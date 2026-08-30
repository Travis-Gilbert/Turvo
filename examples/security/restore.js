// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

;(async function () {
  const deadline = Date.now() + 10000
  while (!window.__TAURI__ || !window.__TURVO_TEST_BASE__) {
    if (Date.now() > deadline) throw new Error('restored document did not initialize')
    await new Promise(resolve => setTimeout(resolve, 20))
  }
  let passed = false
  let detail = ''
  try {
    const reply = await window.__TAURI__.core.invoke('protected_action', {
      caseName: 'restored-local', value: 'restored-value'
    })
    if (reply.echo !== 'restored-value') throw new Error('restored local invoke failed')
    await new Promise(resolve => setTimeout(resolve, 250))
    passed = true
  } catch (error) {
    detail = String(error)
  }
  await fetch(window.__TURVO_TEST_BASE__ + '/report', {
    method: 'POST', body: JSON.stringify({ case: 'navigation-race-restored', passed, detail })
  })
})()
