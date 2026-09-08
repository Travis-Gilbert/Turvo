// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

self.onmessage = async ({ data }) => {
  try {
    // Prove the worker executed and can use ordinary same-origin fetch before
    // testing whether it can borrow its containing frame's application origin.
    const asset = await fetch(data.localAsset, { mode: 'same-origin' })
    if (typeof document !== 'undefined' || !asset.ok ||
        !(await asset.text()).includes('turvo-cross-origin-asset-canary')) {
      throw new Error('worker execution or same-origin positive control failed')
    }
    let denied
    try {
      const response = await fetch('ipc://localhost/protected_action', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json', 'Tauri-Callback': '920',
          'Tauri-Error': '921', 'Tauri-Invoke-Key': data.key
        },
        body: JSON.stringify({ caseName: 'local-frame-worker', value: 'must-not-reach-rust' })
      })
      denied = response.headers.get('Tauri-Response') !== 'ok'
    } catch (_) {
      denied = true
    }
    self.postMessage({ executed: true, denied })
  } catch (error) {
    self.postMessage({ executed: false, detail: String(error) })
  }
}
