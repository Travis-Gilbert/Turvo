// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'

const script = readFileSync(
  new URL('../src/invoke-system-initialization-script.js', import.meta.url), 'utf8'
).replace('__INVOKE_KEY__', JSON.stringify('test-only-invoke-key'))

async function invoke(payload, response, command = 'echo') {
  const requests = []
  let complete
  const callback = new Promise(resolve => { complete = resolve })
  const internals = { runCallback: (id, value) => complete({ id, value }) }
  const context = vm.createContext({
    window: { __TAURI_INTERNALS__: internals },
    ArrayBuffer, Uint8Array, Map, Headers, Error,
    fetch: async (url, options) => {
      requests.push({ url, ...options })
      if (response instanceof Error) throw response
      return response
    }
  })
  vm.runInContext(script, context)
  internals.postMessage({
    cmd: command, callback: 7, error: 8, payload,
    options: { headers: { 'X-Test': 'preserved' } }
  })
  return { result: await callback, requests, window: context.window }
}

function response(body, contentType, kind = 'ok', status = 200) {
  return new Response(body, {
    status, headers: { 'Content-Type': contentType, 'Tauri-Response': kind }
  })
}

test('JSON, custom serializers, maps, and authentication headers survive transport', async () => {
  const { result, requests } = await invoke({
    map: new Map([['value', 42]]),
    bytes: new Uint8Array([0, 255]),
    channel: { __TAURI_TO_IPC_KEY__: () => '__CHANNEL__:12' }
  }, response('{"answer":42}', 'application/json; charset=utf-8'))
  assert.deepEqual(result, { id: 7, value: { answer: 42 } })
  assert.equal(requests.length, 1)
  const request = requests[0]
  assert.equal(request.url, 'ipc://localhost/echo')
  assert.equal(request.method, 'POST')
  assert.deepEqual(JSON.parse(request.body), {
    map: { value: 42 }, bytes: [0, 255], channel: '__CHANNEL__:12'
  })
  assert.equal(request.headers.get('Content-Type'), 'application/json')
  assert.equal(request.headers.get('Tauri-Invoke-Key'), 'test-only-invoke-key')
  assert.equal(request.headers.get('Tauri-Callback'), '7')
  assert.equal(request.headers.get('Tauri-Error'), '8')
  assert.equal(request.headers.get('X-Test'), 'preserved')
})

test('binary arrays and typed-array slices preserve exact bytes', async () => {
  for (const payload of [[0, 255, 10], new Uint8Array([9, 0, 255, 10, 9]).subarray(1, 4)]) {
    const { result, requests } = await invoke(
      payload, response(new Uint8Array([0, 255, 10]), 'application/octet-stream')
    )
    assert.equal(requests[0].headers.get('Content-Type'), 'application/octet-stream')
    assert.deepEqual(Array.from(requests[0].body), [0, 255, 10])
    assert.equal(result.id, 7)
    assert.deepEqual(Array.from(new Uint8Array(result.value)), [0, 255, 10])
  }
})

test('channel fetches use the same authenticated protocol', async () => {
  const { result, requests } = await invoke(
    null, response('channel payload', 'text/plain; charset=utf-8'), 'plugin:__TAURI_CHANNEL__|fetch'
  )
  assert.equal(requests[0].url, 'ipc://localhost/plugin%3A__TAURI_CHANNEL__%7Cfetch')
  assert.deepEqual(result, { id: 7, value: 'channel payload' })
})

test('command errors use the error callback', async () => {
  const { result } = await invoke({}, response('"denied"', 'application/json', 'error'))
  assert.deepEqual(result, { id: 8, value: 'denied' })
})

test('network and HTTP failures do not fall back to an unauthenticated transport', async () => {
  for (const reply of [new Error('network denied'), response('', 'text/plain', 'error', 403)]) {
    const { result, requests } = await invoke({}, reply)
    assert.equal(requests.length, 1)
    assert.equal(result.id, 8)
    assert.match(result.value, /network denied|request was rejected: 403/)
  }
})

test('initialization exposes an immutable Turvo runtime marker', async () => {
  const { window } = await invoke({}, response('{}', 'application/json'))
  assert.deepEqual({ ...window.__TURVO__ }, { runtime: 'servo' })
  assert.equal(Object.isFrozen(window.__TURVO__), true)
  assert.equal(Object.getOwnPropertyDescriptor(window, '__TURVO__').enumerable, false)
})
