const { invoke } = window.__TAURI__.core
const { emit, listen } = window.__TAURI__.event
const status = document.querySelector('#status')

function report(value) {
  status.textContent = String(value)
}

listen('turvo:rust-event', (event) => report(event.payload)).catch(report)

document.querySelector('#greet').addEventListener('click', async () => {
  try {
    report(await invoke('greet', { name: document.querySelector('#name').value }))
  } catch (error) {
    report(error)
  }
})

document.querySelector('#js-event').addEventListener('click', async () => {
  try {
    await emit('turvo:js-event', 'an event from JavaScript')
    report('JavaScript event emitted; waiting for Rust.')
  } catch (error) {
    report(error)
  }
})

document.querySelector('#rust-event').addEventListener('click', async () => {
  try {
    await invoke('emit_from_rust', { message: 'an event emitted by a Rust command' })
  } catch (error) {
    report(error)
  }
})

document.querySelectorAll('[data-command]').forEach((button) => {
  button.addEventListener('click', async () => {
    const command = button.dataset.command
    const args = command === 'retitle_secondary_window'
      ? { title: `Turvo API - ${new Date().toLocaleTimeString()}` }
      : {}

    try {
      const result = await invoke(command, args)
      report(result ?? `${command} completed`)
    } catch (error) {
      report(error)
    }
  })
})

const databaseName = 'turvo-api-storage-hook'
const storeName = 'probe'
const probeKey = 'round-trip'

function requestResult(request) {
  return new Promise((resolve, reject) => {
    request.addEventListener('success', () => resolve(request.result), { once: true })
    request.addEventListener('error', () => reject(request.error), { once: true })
  })
}

function transactionComplete(transaction) {
  return new Promise((resolve, reject) => {
    transaction.addEventListener('complete', resolve, { once: true })
    transaction.addEventListener('abort', () => reject(transaction.error), { once: true })
    transaction.addEventListener('error', () => reject(transaction.error), { once: true })
  })
}

async function openProbeDatabase() {
  const request = indexedDB.open(databaseName, 1)
  request.addEventListener('upgradeneeded', () => {
    if (!request.result.objectStoreNames.contains(storeName)) {
      request.result.createObjectStore(storeName)
    }
  })
  return requestResult(request)
}

async function readProbeValue() {
  const database = await openProbeDatabase()
  try {
    const transaction = database.transaction(storeName, 'readonly')
    const completed = transactionComplete(transaction)
    const result = await requestResult(transaction.objectStore(storeName).get(probeKey))
    await completed
    return result
  } finally {
    database.close()
  }
}

document.querySelector('#idb-round-trip').addEventListener('click', async () => {
  try {
    const database = await openProbeDatabase()
    const value = { source: 'turvo-api', committed: true }
    const transaction = database.transaction(storeName, 'readwrite')
    const completed = transactionComplete(transaction)
    transaction.objectStore(storeName).put(value, probeKey)
    await completed
    database.close()

    const reopened = await readProbeValue()
    if (JSON.stringify(reopened) !== JSON.stringify(value)) {
      throw new Error(`IndexedDB reopened with an unexpected value: ${JSON.stringify(reopened)}`)
    }
    report('IndexedDB write committed and survived reopen.')
  } catch (error) {
    report(error)
  }
})

document.querySelector('#idb-clear').addEventListener('click', async () => {
  try {
    await invoke('clear_browsing_data')
    await new Promise((resolve) => setTimeout(resolve, 100))
    const reopened = await readProbeValue()
    if (reopened !== undefined) {
      throw new Error('IndexedDB value remained after clear_all_browsing_data.')
    }
    report('IndexedDB was cleared and reopened empty.')
  } catch (error) {
    report(error)
  }
})
