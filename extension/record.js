let recorder;
let stream;
const status = document.getElementById('status');
const button = document.getElementById('record');

document.addEventListener('keydown', (event) => {
  if (event.code === 'Space' && !event.repeat) {
    event.preventDefault();
    if (recorder) stopRecording();
  }
  if (event.key === 'Escape') window.close();
});

button.addEventListener('click', stopRecording);

startRecording();

async function startRecording() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks = [];
    recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
    recorder.onstop = async () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      window.opener?.postMessage({ type: 'speech-prompt-audio', blob }, '*');
      window.close();
    };
    recorder.start();
    button.disabled = false;
    button.textContent = '⏹ Detener';
    status.textContent = 'Escuchando… habla ahora';
  } catch (error) {
    status.textContent = error.name === 'NotAllowedError' ? 'Permiso de micrófono rechazado.' : error.message;
    window.opener?.postMessage({ type: 'speech-prompt-error', message: status.textContent }, '*');
  }
}

function stopRecording() {
  if (!recorder) return;
  recorder.stop();
  stream.getTracks().forEach((track) => track.stop());
  button.disabled = true;
  status.textContent = 'Procesando audio…';
}
