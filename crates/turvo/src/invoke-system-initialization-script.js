// Copyright 2019-2024 Tauri Programme within The Commons Conservancy
// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

// Invoke system for the Servo runtime, derived from tauri's ipc-protocol.js.
//
// The lower-level Servo protocol handler supplies the real body stream and
// authenticated initiating document. Use ipc:// on every OS so Windows does
// not fall back to the metadata-only HTTP resource interception interface.

;(function () {
  Object.defineProperty(window, '__TURVO__', {
    value: Object.freeze({ runtime: 'servo' }),
    configurable: false,
    enumerable: false,
    writable: false
  })

  /**
   * A runtime generated key to ensure an IPC call comes from an initialized frame.
   *
   * This is declared outside the `window.__TAURI_INVOKE__` definition to prevent
   * the key from being leaked by `window.__TAURI_INVOKE__.toString()`.
   */
  const __TAURI_INVOKE_KEY__ = __INVOKE_KEY__

  const processIpcMessage = function (message) {
    if (
      message instanceof ArrayBuffer
      || ArrayBuffer.isView(message)
      || Array.isArray(message)
    ) {
      return {
        contentType: 'application/octet-stream',
        data: Array.isArray(message) ? new Uint8Array(message) : message
      }
    } else {
      const data = JSON.stringify(message, (_k, val) => {
        // if this value changes, make sure to update it in:
        // 1. ipc.js
        // 2. core.ts
        const SERIALIZE_TO_IPC_FN = '__TAURI_TO_IPC_KEY__'

        if (val instanceof Map) {
          return Object.fromEntries(val.entries())
        } else if (val instanceof Uint8Array) {
          return Array.from(val)
        } else if (val instanceof ArrayBuffer) {
          return Array.from(new Uint8Array(val))
        } else if (
          typeof val === 'object'
          && val !== null
          && SERIALIZE_TO_IPC_FN in val
        ) {
          return val[SERIALIZE_TO_IPC_FN]()
        } else {
          return val
        }
      })

      return {
        contentType: 'application/json',
        data
      }
    }
  }

  function sendIpcMessage(message) {
    const { cmd, callback, error, payload, options } = message
    const { contentType, data } = processIpcMessage(payload)
    const headers = new Headers((options && options.headers) || {})
    headers.set('Content-Type', contentType)
    headers.set('Tauri-Callback', callback)
    headers.set('Tauri-Error', error)
    headers.set('Tauri-Invoke-Key', __TAURI_INVOKE_KEY__)

    fetch('ipc://localhost/' + encodeURIComponent(cmd), {
      method: 'POST',
      body: data,
      headers
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error('Turvo IPC request was rejected: ' + response.status)
        }
        const callbackId =
          response.headers.get('Tauri-Response') === 'ok' ? callback : error
        const contentType = (response.headers.get('content-type') || '')
          .split(';')[0].trim().toLowerCase()
        switch (contentType) {
          case 'application/json':
            return response.json().then((r) => [callbackId, r])
          case 'text/plain':
            return response.text().then((r) => [callbackId, r])
          default:
            return response.arrayBuffer().then((r) => [callbackId, r])
        }
      })
      .then(
        ([callbackId, data]) => {
          window.__TAURI_INTERNALS__.runCallback(callbackId, data)
        },
        (e) => {
          window.__TAURI_INTERNALS__.runCallback(error, e instanceof Error ? e.message : String(e))
        }
      )
  }

  Object.defineProperty(window.__TAURI_INTERNALS__, 'postMessage', {
    value: sendIpcMessage
  })
})()
