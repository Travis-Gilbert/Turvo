// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

;(async function () {
  const scriptUrl = new URL(document.currentScript.src)
  const params = new URLSearchParams(location.search)
  const caseName = params.get('case') || scriptUrl.searchParams.get('case')
  const base = params.get('base') || scriptUrl.origin
  const report = (passed, detail = '', reportedCase = caseName) => fetch(base + '/report', {
    method: 'POST', body: JSON.stringify({ case: reportedCase, passed, detail })
  })
  try {
    if (window !== window.top && (window.__TAURI__ || window.__TURVO_TEST_BASE__)) {
      throw new Error('main-frame initialization leaked into a child frame')
    }
    const config = await (await fetch(base + '/config')).json()
    if (!config.key) throw new Error('missing positive-control invoke key')
    const attempt = async suffix => {
      try {
        const response = await fetch('ipc://localhost/protected_action', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json', 'Tauri-Callback': '910',
            'Tauri-Error': '911', 'Tauri-Invoke-Key': config.key
          },
          body: JSON.stringify({ caseName: caseName + suffix, value: 'must-not-reach-rust' })
        })
        return response.headers.get('Tauri-Response') !== 'ok'
      } catch (_) {
        return true
      }
    }
    if (!await attempt('')) throw new Error('untrusted command reached Rust')
    if (caseName === 'local-frame') {
      const result = await new Promise((resolve, reject) => {
        const worker = new Worker(new URL('worker-probe.js', config.localRoot))
        const timer = setTimeout(() => {
          worker.terminate()
          reject(new Error('local-frame worker did not execute and report'))
        }, 10000)
        worker.onmessage = ({ data }) => {
          clearTimeout(timer)
          worker.terminate()
          resolve(data)
        }
        worker.onerror = () => {
          clearTimeout(timer)
          worker.terminate()
          reject(new Error('local-frame worker failed to start'))
        }
        worker.postMessage({ key: config.key, localAsset: config.localAsset })
      })
      if (result.executed !== true) throw new Error(result.detail || 'worker positive control missing')
      await report(result.denied === true, 'local-frame worker reached Rust', 'local-frame-worker')
      if (result.denied !== true) return
    }
    if (caseName === 'remote-frame' || caseName === 'remote-top') {
      let exposed = false
      try {
        exposed = (await (await fetch(config.localAsset)).text()).includes('turvo-cross-origin-asset-canary')
      } catch (_) {}
      if (exposed) throw new Error('remote document read a cross-origin bundled asset')
      const opaque = await fetch(config.localAsset, { mode: 'no-cors' })
      if (opaque.type !== 'opaque' || opaque.status !== 0 || (await opaque.text()) !== '') {
        throw new Error('no-cors bundled response exposed its status or body')
      }
    }
    if (caseName === 'opaque-top') {
      // Queue calls from this opaque document immediately before Rust restores
      // a trusted local document. None may borrow the replacement's identity.
      for (let index = 0; index < 16; index++) void attempt('-queued-' + index)
    }
    await report(true)
  } catch (error) {
    await report(false, String(error))
  }
})()
