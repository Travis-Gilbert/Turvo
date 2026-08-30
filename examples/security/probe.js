// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

;(async function () {
  const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
  const deadline = Date.now() + 15000
  while (!window.__TAURI__ || !window.__TURVO_TEST_BASE__) {
    if (Date.now() > deadline) throw new Error('Tauri initialization did not arrive')
    await pause(20)
  }
  const base = window.__TURVO_TEST_BASE__
  const assert = (condition, message) => { if (!condition) throw new Error(message) }
  const report = (caseName, passed, detail = '') => fetch(base + '/report', {
    method: 'POST', body: JSON.stringify({ case: caseName, passed, detail })
  })
  try {
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
    const imageBlocked = new Promise((resolve, reject) => {
      const image = new Image()
      image.onload = () => reject(new Error('CSP unexpectedly allowed an image'))
      image.onerror = resolve
      image.src = base + '/blocked-image'
      document.body.append(image)
    })
    await imageBlocked
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
    const framesDeadline = Date.now() + 15000
    while (true) {
      const reports = await (await fetch(base + '/status')).json()
      if (cases.every(caseName => reports.includes(caseName))) break
      if (Date.now() > framesDeadline) throw new Error('a frame failed to execute and report')
      await pause(50)
    }
    document.querySelector('#status').textContent = 'Local IPC, channels, events, CSP, and frames passed.'
    await report('local-suite', true)
  } catch (error) {
    await report('local-suite', false, String(error))
  }
})()
