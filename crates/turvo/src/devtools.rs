// Copyright 2026 Turvo contributors
// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

use std::{
  fmt,
  net::{IpAddr, Ipv4Addr, SocketAddr},
  sync::{Arc, OnceLock, RwLock},
};

type DevtoolsConnectionHandler = Arc<dyn Fn() -> bool + Send + Sync>;
type DevtoolsServerHandler = Arc<dyn Fn(DevtoolsServer) + Send + Sync>;

/// Information emitted when Servo starts a remote DevTools server.
///
/// The authentication token bypasses Servo's connection-approval callback and
/// must be handled like a secret. Its value is deliberately redacted from the
/// [`Debug`] representation.
#[derive(Clone)]
pub struct DevtoolsServer {
  webview_id: String,
  port: u16,
  authentication_token: String,
}

impl DevtoolsServer {
  /// The Turvo webview whose Servo engine owns this server.
  #[must_use]
  pub fn webview_id(&self) -> &str {
    &self.webview_id
  }

  /// The loopback TCP port selected for this server.
  #[must_use]
  pub fn port(&self) -> u16 {
    self.port
  }

  /// Servo's token for clients that support authenticated attachment.
  #[must_use]
  pub fn authentication_token(&self) -> &str {
    &self.authentication_token
  }
}

impl fmt::Debug for DevtoolsServer {
  fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
    formatter
      .debug_struct("DevtoolsServer")
      .field("webview_id", &self.webview_id)
      .field("port", &self.port)
      .field("authentication_token", &"[redacted]")
      .finish()
  }
}

/// Process-wide options applied to Servo instances created by Turvo.
///
/// Tauri owns one application runtime per process, so these options are fixed
/// once the first Servo engine starts. Every Turvo webview receives the same
/// base renderer configuration; the fixed DevTools endpoint is claimed by the
/// first engine so later windows cannot collide with its listener.
#[derive(Clone, Default)]
pub struct TurvoOptions {
  devtools_port: Option<u16>,
  devtools_connection_handler: Option<DevtoolsConnectionHandler>,
  devtools_server_handler: Option<DevtoolsServerHandler>,
}

impl TurvoOptions {
  /// Enables Servo's Firefox-compatible remote devtools server.
  ///
  /// The server always binds to `127.0.0.1`. Port `0` is rejected because
  /// Servo 0.5 does not report the actual operating-system-selected port back
  /// to embedders.
  pub fn try_with_devtools_port(mut self, port: u16) -> Result<Self, InvalidDevtoolsPort> {
    if port == 0 {
      return Err(InvalidDevtoolsPort);
    }
    self.devtools_port = Some(port);
    Ok(self)
  }

  /// Handles tokenless DevTools connection attempts.
  ///
  /// Servo validates its generated authentication token before this handler is
  /// called. Returning `true` therefore approves a client that supplied no
  /// valid token. Applications should return `true` only after an explicit,
  /// application-controlled confirmation.
  #[must_use]
  pub fn with_devtools_connection_handler(
    mut self,
    handler: impl Fn() -> bool + Send + Sync + 'static,
  ) -> Self {
    self.devtools_connection_handler = Some(Arc::new(handler));
    self
  }

  /// Receives the loopback endpoint and generated authentication token.
  ///
  /// Turvo never logs the token. Applications that forward or display it are
  /// responsible for keeping it out of persistent logs and telemetry.
  #[must_use]
  pub fn with_devtools_server_handler(
    mut self,
    handler: impl Fn(DevtoolsServer) + Send + Sync + 'static,
  ) -> Self {
    self.devtools_server_handler = Some(Arc::new(handler));
    self
  }

  pub(crate) fn devtools_listen_address(&self) -> Option<SocketAddr> {
    self
      .devtools_port
      .map(|port| SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), port))
  }

  pub(crate) fn approve_devtools_connection(&self) -> bool {
    self
      .devtools_connection_handler
      .as_ref()
      .is_some_and(|handler| handler())
  }

  pub(crate) fn notify_devtools_server_started(
    &self,
    webview_id: String,
    port: u16,
    authentication_token: String,
  ) {
    if let Some(handler) = &self.devtools_server_handler {
      handler(DevtoolsServer {
        webview_id,
        port,
        authentication_token,
      });
    }
  }
}

impl fmt::Debug for TurvoOptions {
  fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
    formatter
      .debug_struct("TurvoOptions")
      .field("devtools_port", &self.devtools_port)
      .field(
        "has_devtools_connection_handler",
        &self.devtools_connection_handler.is_some(),
      )
      .field(
        "has_devtools_server_handler",
        &self.devtools_server_handler.is_some(),
      )
      .finish()
  }
}

/// Error returned when port `0` is selected for Servo 0.5 DevTools.
#[derive(Debug, thiserror::Error)]
#[error("the pinned Servo release cannot report an OS-selected DevTools port; choose 1..=65535")]
pub struct InvalidDevtoolsPort;

/// Error returned when runtime options are changed after Servo has started.
#[derive(Debug, thiserror::Error)]
#[error("Turvo runtime options must be configured before the first Servo webview starts")]
pub struct OptionsAlreadyLocked;

#[derive(Default)]
struct OptionsState {
  options: TurvoOptions,
  engine_started: bool,
  devtools_server_claimed: bool,
}

impl OptionsState {
  fn configure(&mut self, options: TurvoOptions) -> Result<(), OptionsAlreadyLocked> {
    if self.engine_started {
      return Err(OptionsAlreadyLocked);
    }

    self.options = options;
    Ok(())
  }

  fn start_engine(&mut self) -> TurvoOptions {
    self.engine_started = true;
    let mut options = self.options.clone();
    if options.devtools_port.is_some() {
      if self.devtools_server_claimed {
        options.devtools_port = None;
      } else {
        self.devtools_server_claimed = true;
      }
    }
    options
  }
}

static OPTIONS: OnceLock<RwLock<OptionsState>> = OnceLock::new();

fn options() -> &'static RwLock<OptionsState> {
  OPTIONS.get_or_init(|| RwLock::new(OptionsState::default()))
}

pub(crate) fn configure(value: TurvoOptions) -> Result<(), OptionsAlreadyLocked> {
  options()
    .write()
    .expect("Turvo options lock poisoned")
    .configure(value)
}

pub(crate) fn options_for_engine() -> TurvoOptions {
  options()
    .write()
    .expect("Turvo options lock poisoned")
    .start_engine()
}

#[cfg(test)]
mod tests {
  use super::{DevtoolsServer, OptionsState, TurvoOptions};
  use std::{
    net::{IpAddr, Ipv4Addr, SocketAddr},
    sync::{Arc, Mutex},
  };

  #[test]
  fn devtools_are_disabled_by_default() {
    assert_eq!(TurvoOptions::default().devtools_listen_address(), None);
  }

  #[test]
  fn devtools_only_bind_to_ipv4_loopback() {
    assert_eq!(
      TurvoOptions::default()
        .try_with_devtools_port(7000)
        .unwrap()
        .devtools_listen_address(),
      Some(SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 7000))
    );
  }

  #[test]
  fn options_cannot_change_after_an_engine_starts() {
    let mut state = OptionsState::default();
    let selected = TurvoOptions::default()
      .try_with_devtools_port(7000)
      .unwrap();

    state.configure(selected).unwrap();
    assert_eq!(
      state
        .start_engine()
        .devtools_listen_address()
        .unwrap()
        .port(),
      7000
    );
    assert!(state.configure(TurvoOptions::default()).is_err());
  }

  #[test]
  fn a_fixed_devtools_port_is_claimed_by_only_the_first_engine() {
    let mut state = OptionsState::default();
    state
      .configure(
        TurvoOptions::default()
          .try_with_devtools_port(7000)
          .unwrap(),
      )
      .unwrap();

    assert!(state.start_engine().devtools_listen_address().is_some());
    assert!(state.start_engine().devtools_listen_address().is_none());
  }

  #[test]
  fn zero_is_not_accepted_as_a_devtools_port() {
    assert!(TurvoOptions::default().try_with_devtools_port(0).is_err());
  }

  #[test]
  fn tokenless_devtools_connections_are_denied_by_default() {
    assert!(!TurvoOptions::default().approve_devtools_connection());
    assert!(TurvoOptions::default()
      .with_devtools_connection_handler(|| true)
      .approve_devtools_connection());
  }

  #[test]
  fn server_handler_receives_the_token_without_debug_output_exposing_it() {
    let received = Arc::new(Mutex::new(None));
    let received_ = received.clone();
    let options = TurvoOptions::default().with_devtools_server_handler(move |server| {
      *received_.lock().unwrap() = Some(server);
    });

    options.notify_devtools_server_started("main".into(), 7000, "secret-token".into());

    let server = received.lock().unwrap().take().unwrap();
    assert_eq!(server.webview_id(), "main");
    assert_eq!(server.port(), 7000);
    assert_eq!(server.authentication_token(), "secret-token");
    assert!(!format!("{server:?}").contains("secret-token"));
  }

  #[test]
  fn devtools_server_debug_output_redacts_tokens() {
    let server = DevtoolsServer {
      webview_id: "main".into(),
      port: 7000,
      authentication_token: "secret-token".into(),
    };

    assert!(!format!("{server:?}").contains("secret-token"));
  }
}
