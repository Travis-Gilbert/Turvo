// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Emitter, Listener, Manager, PhysicalSize, WebviewUrl, WebviewWindowBuilder};

const SECONDARY_WINDOW: &str = "secondary";

#[tauri::command]
fn greet(name: &str) -> String {
  format!("Hello {name} from a Tauri command running over Turvo.")
}

#[tauri::command]
fn emit_from_rust(app: tauri::AppHandle<turvo::Turvo>, message: String) -> Result<(), String> {
  app
    .emit("turvo:rust-event", message)
    .map_err(|error| error.to_string())
}

#[tauri::command]
async fn create_secondary_window(app: tauri::AppHandle<turvo::Turvo>) -> Result<String, String> {
  if let Some(window) = app.get_webview_window(SECONDARY_WINDOW) {
    window.set_focus().map_err(|error| error.to_string())?;
    return Ok(SECONDARY_WINDOW.into());
  }

  WebviewWindowBuilder::new(&app, SECONDARY_WINDOW, WebviewUrl::App("index.html".into()))
    .title("Turvo API - secondary")
    .inner_size(560.0, 440.0)
    .build()
    .map_err(|error| error.to_string())?;

  Ok(SECONDARY_WINDOW.into())
}

#[tauri::command]
fn retitle_secondary_window(
  app: tauri::AppHandle<turvo::Turvo>,
  title: String,
) -> Result<(), String> {
  let window = app
    .get_webview_window(SECONDARY_WINDOW)
    .ok_or_else(|| "the secondary window is not open".to_owned())?;
  window.set_title(&title).map_err(|error| error.to_string())
}

#[tauri::command]
fn resize_secondary_window(app: tauri::AppHandle<turvo::Turvo>) -> Result<(), String> {
  let window = app
    .get_webview_window(SECONDARY_WINDOW)
    .ok_or_else(|| "the secondary window is not open".to_owned())?;
  window
    .set_size(PhysicalSize::new(720, 520))
    .map_err(|error| error.to_string())
}

#[tauri::command]
fn close_secondary_window(app: tauri::AppHandle<turvo::Turvo>) -> Result<(), String> {
  let window = app
    .get_webview_window(SECONDARY_WINDOW)
    .ok_or_else(|| "the secondary window is not open".to_owned())?;
  window.close().map_err(|error| error.to_string())
}

#[tauri::command]
fn clear_browsing_data(app: tauri::AppHandle<turvo::Turvo>) -> Result<(), String> {
  let window = app
    .get_webview_window("main")
    .ok_or_else(|| "the main window is not open".to_owned())?;
  window
    .clear_all_browsing_data()
    .map_err(|error| error.to_string())
}

fn main() {
  turvo::builder()
    .setup(|app| {
      let handle = app.handle().clone();
      app.listen("turvo:js-event", move |event| {
        let reply = format!("Rust received: {}", event.payload());
        if let Err(error) = handle.emit("turvo:rust-event", reply) {
          eprintln!("failed to emit Rust event: {error}");
        }
      });
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![
      greet,
      emit_from_rust,
      create_secondary_window,
      retitle_secondary_window,
      resize_secondary_window,
      close_secondary_window,
      clear_browsing_data,
    ])
    .run(tauri::generate_context!())
    .expect("failed to run the Turvo API example");
}
