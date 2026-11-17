let recorder;
let stream;
const status = document.getElementById('status');
const button = document.getElementById('record');

document.addEventListener('keydown', (event) => {
  if (event.code === 'Space' && !event.repeat) {
    event.preventDefault();
    if (recorder) stopRecording();
  }
});

button.addEventListener('click', stopRecording);
window.parent.postMessage({ type: 'speech-prompt-ready' }, '*');
window.addEventListener('message', (event) => {
  if (event.source !== window.parent) return;
  if (event.data?.type === 'start-recording') startRecording();
  if (event.data?.type === 'stop-recording') stopRecording();
});

async function startRecording() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks = [];
    recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
    recorder.onstop = async () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      window.parent.postMessage({ type: 'speech-prompt-audio', blob }, '*');
    };
    recorder.start();
    button.disabled = false;
    button.textContent = '⏹ Detener';
    status.textContent = 'Escuchando… habla ahora';
    window.parent.postMessage({ type: 'speech-prompt-started' }, '*');
  } catch (error) {
    status.textContent = error.name === 'NotAllowedError' ? 'Permiso de micrófono rechazado.' : error.message;
    window.parent.postMessage({ type: 'speech-prompt-error', message: status.textContent }, '*');
  }
}

function stopRecording() {
  if (!recorder) return;
  recorder.stop();
  stream.getTracks().forEach((track) => track.stop());
  button.disabled = true;
  status.textContent = 'Procesando audio…';
}
