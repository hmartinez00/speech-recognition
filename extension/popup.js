const DEFAULT_MODEL = 'nvidia/nemotron-3.5-transcribe';
const ENDPOINT = 'https://openrouter.ai/api/v1/audio/transcriptions';
const $ = (id) => document.getElementById(id);
let recorder;
let chunks = [];
let stream;

document.addEventListener('DOMContentLoaded', async () => {
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
  const recordUrl = chrome.runtime.getURL('record.html');
  const recordWindow = window.open(recordUrl, 'speechPromptRecorder', 'popup,width=420,height=180');
  if (!recordWindow) {
    setStatus('Chrome bloqueó la ventana de grabación. Permite ventanas emergentes para la extensión.', true);
    return;
  }
  setStatus('Abriendo grabador…');
  window.addEventListener('message', handleRecorderMessage, { once: false });
  return;
  /* Fallback kept below for browsers that allow microphone access in the popup. */
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    chunks = [];
    recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
    recorder.onstop = transcribe;
    recorder.start();
    $('record').textContent = '⏹ Detener';
    setStatus('Escuchando… habla ahora');
  } catch (error) {
    const message = error.name === 'NotAllowedError'
      ? 'Permiso de micrófono rechazado. Permítelo en los ajustes del sitio para esta extensión y vuelve a cargarla.'
      : 'No se pudo acceder al micrófono: ' + error.message;
    setStatus(message, true);
  }
}

function handleRecorderMessage(event) {
  if (event.data?.type === 'speech-prompt-error') setStatus(event.data.message, true);
  if (event.data?.type === 'speech-prompt-audio') transcribeBlob(event.data.blob);
}

function stopRecording() {
  recorder.stop();
  stream.getTracks().forEach((track) => track.stop());
  recorder = null;
  $('record').disabled = true;
  $('record').textContent = '🎙 Procesando…';
  setStatus('Procesando audio…');
}

async function transcribe() {
  await transcribeBlob(new Blob(chunks, { type: 'audio/webm' }));
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
    setStatus('Transcripción lista');
  } catch (error) { setStatus(error.message, true); }
  finally { $('record').disabled = false; $('record').textContent = '🎙 Escuchar'; }
}

function setStatus(message, error = false) { $('status').textContent = message; $('status').style.color = error ? '#fca5a5' : '#67e8f9'; }
