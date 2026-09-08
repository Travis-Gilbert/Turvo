// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
  env,
  error::Error,
  io,
  net::{TcpStream, ToSocketAddrs},
  path::PathBuf,
  sync::Mutex,
  thread,
  time::{Duration, Instant},
};

use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_shell::{
  process::{CommandChild, CommandEvent},
  ShellExt,
};
use turvo::url::Url;

const DEFAULT_CODE_SERVER_URL: &str = "http://127.0.0.1:8080";
const SIDECAR_NAME: &str = "code-server";
const DEVTOOLS_PORT_ENV: &str = "TURVO_DEVTOOLS_PORT";

#[derive(Default)]
struct CodeServerSidecar(Mutex<Option<CommandChild>>);

impl CodeServerSidecar {
  fn stop(&self) {
    if let Some(child) = self
      .0
      .lock()
      .expect("code-server sidecar lock poisoned")
      .take()
    {
      let _ = child.kill();
    }
  }
}

fn configured_url() -> Result<(Url, bool), Box<dyn Error>> {
  match env::var("TURVO_CODE_SERVER_URL") {
    Ok(value) if !value.trim().is_empty() => Ok((Url::parse(value.trim())?, false)),
    _ => Ok((Url::parse(DEFAULT_CODE_SERVER_URL)?, true)),
  }
}

fn configured_workspace() -> io::Result<PathBuf> {
  match env::var_os("TURVO_CODE_SERVER_WORKSPACE") {
    Some(path) if !path.is_empty() => PathBuf::from(path).canonicalize(),
    _ => env::current_dir()?.canonicalize(),
  }
}

fn configured_options(code_server_url: Url) -> Result<turvo::EngineOptions, Box<dyn Error>> {
  let mut options = turvo::EngineOptions::default().try_with_code_server_url(code_server_url)?;
  if let Some(value) = env::var_os(DEVTOOLS_PORT_ENV) {
    let value = value.to_str().ok_or_else(|| {
      io::Error::new(
        io::ErrorKind::InvalidInput,
        format!("{DEVTOOLS_PORT_ENV} must be valid UTF-8"),
      )
    })?;
    let port = value.parse::<u16>().map_err(|_| {
      io::Error::new(
        io::ErrorKind::InvalidInput,
        format!("{DEVTOOLS_PORT_ENV} must be an integer from 1 through 65535"),
      )
    })?;
    options = options
      .try_with_devtools_port(port)?
      .with_devtools_connection_handler(|| true)
      .with_devtools_server_handler(|server| {
        eprintln!(
          "Turvo DevTools for {} listening on 127.0.0.1:{}",
          server.webview_id(),
          server.port()
        );
      });
  }
  Ok(options)
}

fn wait_until_listening(url: &Url) -> io::Result<()> {
  let host = url
    .host_str()
    .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "code-server URL has no host"))?;
  let port = url.port_or_known_default().ok_or_else(|| {
    io::Error::new(
      io::ErrorKind::InvalidInput,
      "code-server URL has no explicit or scheme-default port",
    )
  })?;
  let addresses = (host, port).to_socket_addrs()?.collect::<Vec<_>>();
  if addresses.is_empty() {
    return Err(io::Error::new(
      io::ErrorKind::AddrNotAvailable,
      "code-server URL did not resolve to a socket address",
    ));
  }

  let deadline = Instant::now() + Duration::from_secs(30);
  loop {
    if addresses
      .iter()
      .any(|address| TcpStream::connect_timeout(address, Duration::from_millis(100)).is_ok())
    {
      return Ok(());
    }
    if Instant::now() >= deadline {
      return Err(io::Error::new(
        io::ErrorKind::TimedOut,
        format!("bundled code-server did not listen at {url}"),
      ));
    }
    thread::sleep(Duration::from_millis(50));
  }
}

fn launch_sidecar(
  app: &tauri::App<turvo::Turvo>,
  url: &Url,
) -> Result<CommandChild, Box<dyn Error>> {
  let workspace = configured_workspace()?;
  let bind_address = format!(
    "{}:{}",
    url
      .host_str()
      .ok_or("default code-server URL has no host")?,
    url
      .port_or_known_default()
      .ok_or("default code-server URL has no port")?
  );
  let command = app.shell().sidecar(SIDECAR_NAME)?.args([
    "--auth".into(),
    "none".into(),
    "--bind-addr".into(),
    bind_address,
    "--disable-telemetry".into(),
    "--disable-update-check".into(),
    workspace.to_string_lossy().into_owned(),
  ]);
  let (mut events, child) = command.spawn()?;

  tauri::async_runtime::spawn(async move {
    while let Some(event) = events.recv().await {
      match event {
        CommandEvent::Stdout(bytes) => {
          eprintln!("code-server: {}", String::from_utf8_lossy(&bytes).trim());
        }
        CommandEvent::Stderr(bytes) => {
          eprintln!("code-server: {}", String::from_utf8_lossy(&bytes).trim());
        }
        CommandEvent::Error(error) => eprintln!("code-server sidecar error: {error}"),
        CommandEvent::Terminated(payload) => {
          eprintln!("code-server sidecar terminated: {payload:?}");
          break;
        }
        _ => {}
      }
    }
  });

  wait_until_listening(url)?;
  Ok(child)
}

fn main() {
  let (code_server_url, launch_bundled) =
    configured_url().expect("TURVO_CODE_SERVER_URL must be an absolute URL");

  let options = configured_options(code_server_url.clone())
    .expect("code-server and DevTools settings must be valid");
  let app = turvo::builder_with_options(options)
    .expect("Turvo engine options must be configured before a webview starts")
    .plugin(tauri_plugin_shell::init())
    .setup(move |app| {
      let child = if launch_bundled {
        Some(launch_sidecar(app, &code_server_url)?)
      } else {
        None
      };
      app.manage(CodeServerSidecar(Mutex::new(child)));

      WebviewWindowBuilder::new(app, "main", WebviewUrl::External(code_server_url.clone()))
        .title("code-server")
        .inner_size(1280.0, 800.0)
        .on_document_title_changed(|window, title| {
          if !title.trim().is_empty() {
            let _ = window.set_title(&title);
          }
        })
        .build()?;
      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("failed to build the Turvo code-server example");

  app.run(|handle, event| {
    if matches!(event, RunEvent::Exit) {
      handle.state::<CodeServerSidecar>().stop();
    }
  });
}
