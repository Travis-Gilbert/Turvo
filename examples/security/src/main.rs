// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

//! Native, loopback-only test fixture. Never embed this server in a product:
//! it intentionally shares the ephemeral invoke key with adversarial pages.

use std::{
  collections::BTreeSet,
  io::Read,
  sync::{Arc, Mutex},
  time::{Duration, Instant},
};

use percent_encoding::{utf8_percent_encode, NON_ALPHANUMERIC};
use serde::Deserialize;
use serde_json::{json, Value};
use tauri::{Emitter, Listener, Manager, WebviewUrl, WebviewWindowBuilder};
use tiny_http::{Header, Response, Server};
use url::Url;

const CASES: &[&str] = &[
  "local-suite",
  "remote-frame",
  "local-frame",
  "sandbox-frame",
  "opaque-frame",
  "sandbox-top",
  "remote-top",
  "opaque-top",
  "navigation-race-restored",
];

#[derive(Default)]
struct Observations {
  calls: Vec<String>,
  reports: BTreeSet<String>,
  binary: bool,
  channel: bool,
  js_event: bool,
  blocked_asset_requested: bool,
}

type Shared = Arc<Mutex<Observations>>;

#[tauri::command]
fn protected_action(state: tauri::State<'_, Shared>, case_name: String, value: String) -> Value {
  state.lock().unwrap().calls.push(case_name);
  json!({ "echo": value })
}

#[tauri::command]
fn binary_echo(
  state: tauri::State<'_, Shared>,
  request: tauri::ipc::Request<'_>,
) -> Result<tauri::ipc::Response, String> {
  let tauri::ipc::InvokeBody::Raw(bytes) = request.body() else {
    return Err("expected an actual binary request body".into());
  };
  state.lock().unwrap().binary = bytes == &[0, 255, 10, 0];
  Ok(tauri::ipc::Response::new(bytes.clone()))
}

#[tauri::command]
fn channel_echo(
  state: tauri::State<'_, Shared>,
  channel: tauri::ipc::Channel<String>,
) -> Result<(), String> {
  // Exceeds Tauri's inline threshold, exercising the channel fetch endpoint.
  channel
    .send("s".repeat(65_536))
    .map_err(|e| e.to_string())?;
  state.lock().unwrap().channel = true;
  Ok(())
}

#[tauri::command]
fn emit_from_rust(app: tauri::AppHandle<turvo::Turvo>) -> Result<(), String> {
  app
    .emit("security:rust-event", "rust-value")
    .map_err(|e| e.to_string())
}

#[derive(Deserialize)]
struct Report {
  case: String,
  passed: bool,
  #[serde(default)]
  detail: String,
}

fn finish(app: &tauri::AppHandle<turvo::Turvo>, state: &Shared, failure: Option<&str>) {
  let state = state.lock().unwrap();
  let expected_calls = ["local-json", "local-raw", "restored-local"];
  let passed = failure.is_none()
    && state.calls == expected_calls
    && state.binary
    && state.channel
    && state.js_event
    && !state.blocked_asset_requested
    && CASES.iter().all(|case| state.reports.contains(*case));
  println!(
    "TURVO_NATIVE_SECURITY {}",
    json!({
      "passed": passed,
      "failure": failure,
      "reports": state.reports,
      "calls": state.calls,
      "binary": state.binary,
      "channel": state.channel,
      "js_event": state.js_event,
      "blocked_asset_requested": state.blocked_asset_requested
    })
  );
  app.exit(if passed { 0 } else { 1 });
}

fn navigate(app: &tauri::AppHandle<turvo::Turvo>, url: Url) {
  if let Err(error) = app.get_webview_window("main").unwrap().navigate(url) {
    eprintln!("native probe navigation failed: {error}");
    app.exit(1);
  }
}

fn serve(server: Server, base: String, app: tauri::AppHandle<turvo::Turvo>, state: Shared) {
  let deadline = Instant::now() + Duration::from_secs(120);
  let mut config = json!({ "base": base });
  while Instant::now() < deadline {
    let mut request = match server.recv_timeout(Duration::from_millis(100)) {
      Ok(Some(request)) => request,
      Ok(None) => continue,
      Err(_) => break,
    };
    let path = request.url().split('?').next().unwrap_or("/").to_owned();
    let mut report = None;
    let (body, content_type, status) = match path.as_str() {
      "/attacker.html" => (
        include_str!("../attacker.html").to_owned(),
        "text/html",
        200,
      ),
      "/attacker.js" => (
        include_str!("../attacker.js").to_owned(),
        "text/javascript",
        200,
      ),
      "/config" => (config.to_string(), "application/json", 200),
      "/status" => (
        json!(state.lock().unwrap().reports).to_string(),
        "application/json",
        200,
      ),
      "/configure" | "/report" => {
        let mut body = String::new();
        if request
          .as_reader()
          .take(8193)
          .read_to_string(&mut body)
          .is_err()
          || body.len() > 8192
        {
          finish(&app, &state, Some("invalid fixture report body"));
          return;
        }
        if path == "/configure" {
          let Ok(value) = serde_json::from_str::<Value>(&body) else {
            finish(&app, &state, Some("invalid fixture configuration"));
            return;
          };
          // Kept only in process memory; never included in diagnostic output.
          config["key"] = value["key"].clone();
          config["localAsset"] = value["localAsset"].clone();
          config["localRoot"] = value["localRoot"].clone();
        } else {
          report = serde_json::from_str::<Report>(&body).ok();
          if report.is_none() {
            finish(&app, &state, Some("invalid native report"));
            return;
          }
        }
        ("ok".into(), "text/plain", 200)
      }
      "/blocked-image" => {
        state.lock().unwrap().blocked_asset_requested = true;
        ("CSP should prevent this request".into(), "text/plain", 200)
      }
      _ => ("not found".into(), "text/plain", 404),
    };
    let response = Response::from_string(body)
      .with_status_code(status)
      .with_header(Header::from_bytes("Content-Type", content_type).unwrap())
      .with_header(Header::from_bytes("Access-Control-Allow-Origin", "*").unwrap())
      .with_header(Header::from_bytes("Cache-Control", "no-store").unwrap());
    let _ = request.respond(response);
    let Some(report) = report else { continue };
    if !report.passed || !CASES.contains(&report.case.as_str()) {
      let message = format!("{}: {}", report.case, report.detail);
      finish(&app, &state, Some(&message));
      return;
    }
    if !state.lock().unwrap().reports.insert(report.case.clone()) {
      finish(&app, &state, Some("duplicate native report"));
      return;
    }
    println!("native case passed: {}", report.case);
    match report.case.as_str() {
      "local-suite" => {
        let mut url = Url::parse(config["localRoot"].as_str().unwrap()).unwrap();
        url.set_path("/sandbox.html");
        url
          .query_pairs_mut()
          .append_pair("case", "sandbox-top")
          .append_pair("base", &base);
        navigate(&app, url);
      }
      "sandbox-top" => navigate(
        &app,
        Url::parse(&format!("{base}/attacker.html?case=remote-top")).unwrap(),
      ),
      "remote-top" => {
        let html =
          format!("<!doctype html><script src=\"{base}/attacker.js?case=opaque-top\"></script>");
        let url = format!(
          "data:text/html,{}",
          utf8_percent_encode(&html, NON_ALPHANUMERIC)
        );
        navigate(&app, Url::parse(&url).unwrap());
      }
      "opaque-top" => {
        let mut url = Url::parse(config["localRoot"].as_str().unwrap()).unwrap();
        url.set_path("/restore.html");
        navigate(&app, url);
      }
      "navigation-race-restored" => {
        finish(&app, &state, None);
        return;
      }
      _ => {}
    }
  }
  finish(
    &app,
    &state,
    Some("native probe timed out before all cases reported"),
  );
}

fn main() {
  let server = Server::http("127.0.0.1:0").expect("bind the loopback fixture");
  let base = format!("http://{}", server.server_addr());
  let state = Shared::default();
  let setup_state = state.clone();
  let app = turvo::builder()
    .manage(state)
    .invoke_handler(tauri::generate_handler![
      protected_action,
      binary_echo,
      channel_echo,
      emit_from_rust
    ])
    .setup(move |app| {
      let handle = app.handle().clone();
      let events_state = setup_state.clone();
      app.listen("security:js-event", move |event| {
        events_state.lock().unwrap().js_event = event.payload() == "\"js-value\"";
        let _ = handle.emit("security:ack", "ack-value");
      });
      WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
        .title("Turvo native security probe")
        .inner_size(800.0, 600.0)
        .initialization_script(format!(
          "window.__TURVO_TEST_BASE__ = {};",
          serde_json::to_string(&base)?
        ))
        .on_web_resource_request(|request, response| {
          if request.uri().path() == "/sandbox.html" {
            response.headers_mut().append(
              tauri::http::header::CONTENT_SECURITY_POLICY,
              tauri::http::HeaderValue::from_static("sandbox allow-scripts"),
            );
          }
        })
        .build()?;
      let handle = app.handle().clone();
      std::thread::spawn(move || serve(server, base, handle, setup_state));
      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("build the native security probe");
  std::process::exit(app.run_return(|_, _| {}));
}
