// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

;(async function () {
  const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
  const deadline = Date.now() + 15000
  while (!window.__TURVO_TEST_BASE__) {
    if (Date.now() > deadline) throw new Error('Tauri initialization did not arrive')
    await pause(20)
  }
  const base = window.__TURVO_TEST_BASE__
  await fetch(base + '/stage/script-start')
  const assert = (condition, message) => { if (!condition) throw new Error(message) }
  const report = (caseName, passed, detail = '') => fetch(base + '/report', {
    method: 'POST', body: JSON.stringify({ case: caseName, passed, detail })
  })
  try {
    while (!window.__TAURI__) {
      if (Date.now() > deadline) throw new Error('Tauri initialization did not arrive')
      await pause(20)
    }
    await fetch(base + '/stage/globals-ready')
    assert(location.origin === 'http://tauri.localhost', 'bundled document lacks its HTTP tuple origin')
    const asset = await fetch('private.txt', { mode: 'same-origin' })
    assert(asset.ok && (await asset.text()).includes('turvo-cross-origin-asset-canary'), 'same-origin bundled fetch failed')
    const head = await fetch('private.txt', { method: 'HEAD' })
    assert(head.ok && (await head.text()) === '', 'HEAD did not preserve an empty successful response')
    let uploadRejected = false
    try {
      const upload = await fetch('private.txt', { method: 'POST', body: 'must-not-reach-asset-handler' })
      uploadRejected = !upload.ok
    } catch (_) { uploadRejected = true }
    assert(uploadRejected, 'asset interceptor accepted an upload without a body transport')
    while (!window.__TURVO_STATIC_MODULE__) {
      if (Date.now() > deadline) throw new Error('static module or its dependency failed under CSP self')
      await pause(20)
    }
    assert(window.__TURVO_STATIC_MODULE__ === 'static-module-dependency-loaded', 'static module result changed')
    const dynamicModule = await import('./dynamic-module.js')
    assert(dynamicModule.value === 'dynamic-module-loaded', 'dynamic module failed under CSP self')
    assert(window.__TAURI__.core.convertFileSrc('/probe.txt').startsWith('http://asset.localhost/'), 'convertFileSrc ignored the runtime URL contract')
    await report('local-assets-modules', true)
    const { invoke, Channel } = window.__TAURI__.core
    const { listen, emit } = window.__TAURI__.event
    const originalFetch = window.fetch.bind(window)
    let invokeKey
    window.fetch = (url, options) => {
      if (String(url).startsWith('ipc://')) {
        invokeKey = new Headers(options.headers).get('Tauri-Invoke-Key')
      }
      return originalFetch(url, options)
    }
    const reply = await invoke('protected_action', { caseName: 'local-json', value: 'native-value' })
    window.fetch = originalFetch
    assert(reply.echo === 'native-value', 'JSON invoke payload was not preserved')
    assert(typeof invokeKey === 'string' && invokeKey.length > 0, 'test invoke key was not captured')
    const localRoot = new URL('/', location.href).href
    await fetch(base + '/configure', {
      method: 'POST', body: JSON.stringify({
        key: invokeKey, localRoot, localAsset: new URL('private.txt', location.href).href
      })
    })
    const rawReply = await fetch('ipc://localhost/protected_action', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json', 'Tauri-Callback': '900',
        'Tauri-Error': '901', 'Tauri-Invoke-Key': invokeKey
      },
      body: JSON.stringify({ caseName: 'local-raw', value: 'raw-value' })
    })
    assert(rawReply.headers.get('Tauri-Response') === 'ok', 'raw positive control failed')
    assert((await rawReply.json()).echo === 'raw-value', 'raw positive control body changed')
    const binary = await invoke('binary_echo', new Uint8Array([0, 255, 10, 0]))
    assert(Array.from(new Uint8Array(binary)).join(',') === '0,255,10,0', 'binary round trip changed bytes')

    let receiveChannel
    const channelValue = new Promise(resolve => { receiveChannel = resolve })
    const channel = new Channel()
    channel.onmessage = receiveChannel
    await invoke('channel_echo', { channel })
    assert(await channelValue === 's'.repeat(65536), 'channel fetch lost its payload')
    let receiveRust
    const rustEvent = new Promise(resolve => { receiveRust = resolve })
    const unlistenRust = await listen('security:rust-event', event => receiveRust(event.payload))
    await invoke('emit_from_rust')
    assert(await rustEvent === 'rust-value', 'Rust event payload was lost')
    unlistenRust()
    let receiveAck
    const ack = new Promise(resolve => { receiveAck = resolve })
    const unlistenAck = await listen('security:ack', event => receiveAck(event.payload))
    await emit('security:js-event', 'js-value')
    assert(await ack === 'ack-value', 'JS event did not reach Rust')
    unlistenAck()

    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
    assert(document.querySelector('h1').getBoundingClientRect().width > 0, 'bundled document has no layout')
    for (const imageUrl of [base + '/blocked-image', new URL('csp-canary.svg', location.href).href]) {
      await new Promise((resolve, reject) => {
        const image = new Image()
        image.onload = () => reject(new Error('CSP unexpectedly allowed an image'))
        image.onerror = resolve
        image.src = imageUrl
        document.body.append(image)
      })
    }
    const cases = ['remote-frame', 'local-frame', 'sandbox-frame', 'opaque-frame']
    for (const caseName of cases) {
      const frame = document.createElement('iframe')
      if (caseName === 'sandbox-frame') frame.sandbox = 'allow-scripts'
      if (caseName === 'opaque-frame') {
        frame.src = 'data:text/html,' + encodeURIComponent(
          '<!doctype html><script src="' + base + '/attacker.js?case=opaque-frame"></script>'
        )
      } else {
        const url = new URL('attacker.html', caseName === 'local-frame' ? localRoot : base + '/')
        url.searchParams.set('case', caseName)
        url.searchParams.set('base', base)
        frame.src = url.href
      }
      document.body.append(frame)
    }
    const requiredFrameReports = [...cases, 'local-frame-worker']
    const framesDeadline = Date.now() + 15000
    while (true) {
      const reports = await (await fetch(base + '/status')).json()
      if (requiredFrameReports.every(caseName => reports.includes(caseName))) break
      if (Date.now() > framesDeadline) throw new Error('a frame failed to execute and report')
    }
    document.querySelector('#status').textContent = 'Local IPC, channels, events, CSP, and frames passed.'
    await report('local-suite', true)
  } catch (error) {
    await report('local-suite', false, String(error))
  }
})()
