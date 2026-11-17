const DEFAULT_MODEL = 'nvidia/nemotron-3.5-transcribe';
const ENDPOINT = 'https://openrouter.ai/api/v1/audio/transcriptions';
const $ = (id) => document.getElementById(id);
let recorder;
let chunks = [];
let stream;
let sourceTabId;
let recorderFrameReady = false;

document.addEventListener('DOMContentLoaded', async () => {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  sourceTabId = tab?.id;
  const settings = await chrome.storage.local.get({ apiKey: '', language: 'es', model: DEFAULT_MODEL });
  $('apiKey').value = settings.apiKey;
  $('language').value = settings.language;
  $('model').value = settings.model;
});

$('save').addEventListener('click', async () => {
  await chrome.storage.local.set({ apiKey: $('apiKey').value.trim(), language: $('language').value.trim() || 'es', model: $('model').value.trim() || DEFAULT_MODEL });
  setStatus('Configuración guardada');
});

$('record').addEventListener('click', () => recorder ? stopRecording() : startRecording());
$('copy').addEventListener('click', async () => { await navigator.clipboard.writeText($('text').value); setStatus('Texto copiado al portapapeles'); });
$('clear').addEventListener('click', () => { $('text').value = ''; setStatus('Texto limpiado'); });

async function startRecording() {
  const frame = $('recorder');
  $('record').classList.remove('is-ready', 'is-processing', 'is-error');
  $('record').classList.add('is-preparing');
  $('record').textContent = '⌛ Preparando…';
  $('record').disabled = true;
  frame.hidden = false;
  setStatus('Solicitando micrófono…');
  if (recorderFrameReady) frame.contentWindow.postMessage({ type: 'start-recording' }, '*');
}

function handleRecorderMessage(event) {
  if (event.source !== $('recorder').contentWindow) return;
  if (event.data?.type === 'speech-prompt-ready') recorderFrameReady = true;
  if (event.data?.type === 'speech-prompt-started') {
    $('record').hidden = true;
    $('recorder').hidden = false;
    $('recorder').classList.add('is-recording');
    $('recorder').contentDocument?.documentElement.classList.add('is-recording');
    setStatus('Escuchando… habla ahora');
  }
  if (event.data?.type === 'speech-prompt-error') {
    $('recorder').hidden = true;
    $('record').hidden = false;
    $('record').disabled = false;
    $('record').classList.remove('is-preparing', 'is-processing');
    $('record').classList.add('is-error');
    $('record').textContent = '🎙 Reintentar';
    setStatus(event.data.message, true);
  }
  if (event.data?.type === 'speech-prompt-audio') {
    $('recorder').hidden = true;
    $('record').hidden = false;
    $('record').disabled = true;
    $('record').classList.remove('is-preparing', 'is-error');
    $('record').classList.add('is-processing');
    $('record').textContent = '🎙 Procesando…';
    setStatus('Procesando audio…');
    transcribeBlob(event.data.blob);
  }
}

function stopRecording() {
  $('recorder').contentWindow.postMessage({ type: 'stop-recording' }, '*');
}

async function transcribeBlob(blob) {
  try {
    const settings = await chrome.storage.local.get({ apiKey: '', language: 'es', model: DEFAULT_MODEL });
    if (!settings.apiKey) throw new Error('Guarda primero tu clave de OpenRouter en Configuración.');
    const data = await blob.arrayBuffer();
    let binary = '';
    new Uint8Array(data).forEach((byte) => { binary += String.fromCharCode(byte); });
    const response = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${settings.apiKey}`, 'Content-Type': 'application/json', 'HTTP-Referer': 'chrome-extension://speech-prompt', 'X-OpenRouter-Title': 'Speech Prompt Chrome Extension' },
      body: JSON.stringify({ model: settings.model, input_audio: { data: btoa(binary), format: 'webm' }, language: settings.language, temperature: 0 })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error?.message || `OpenRouter rechazó la solicitud (${response.status})`);
    if (!result.text?.trim()) throw new Error('OpenRouter no devolvió una transcripción útil.');
    $('text').value = result.text.trim();
    await insertIntoActiveField(result.text.trim());
    setStatus('Transcripción lista');
  } catch (error) { setStatus(error.message, true); }
  finally {
    $('record').disabled = false;
    $('record').textContent = '🎙 Escuchar';
    $('record').classList.remove('is-preparing', 'is-processing', 'is-error');
    $('record').classList.add('is-ready');
    $('record').hidden = false;
    $('recorder').hidden = true;
    $('recorder').classList.remove('is-recording');
    $('recorder').contentDocument?.documentElement.classList.remove('is-recording');
  }
}

async function insertIntoActiveField(text) {
  if (!sourceTabId) return;
  try {
    const response = await chrome.tabs.sendMessage(sourceTabId, { type: 'speech-prompt-insert', text });
    if (response?.ok) setStatus('Transcripción insertada en el campo activo');
  } catch (_) {
    setStatus('Transcripción lista; esta página no permite insertar texto directamente.');
  }
}

function setStatus(message, error = false) { $('status').textContent = message; $('status').style.color = error ? '#fca5a5' : '#67e8f9'; }

window.addEventListener('message', handleRecorderMessage);
$('recorder').addEventListener('load', () => {
  recorderFrameReady = true;
  $('recorder').contentDocument?.documentElement.classList.remove('is-recording');
  if (!$('recorder').hidden) $('recorder').contentWindow.postMessage({ type: 'start-recording' }, '*');
});
