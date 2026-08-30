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
