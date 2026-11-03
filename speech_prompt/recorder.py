from __future__ import annotations

import tempfile
import wave
import os
from pathlib import Path

SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH = 2


def record_audio(duration: float | None) -> Path:
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError(
            "Faltan dependencias de audio. Instala con: "
            "python -m pip install sounddevice numpy"
        ) from exc

    if duration is not None and duration <= 0:
        raise ValueError("La duracion debe ser mayor que cero")

    frames: list[np.ndarray] = []
    stream = None

    def callback(indata, frame_count, time_info, status):
        if status:
            print(f"Aviso del microfono: {status}")
        frames.append(indata.copy())

    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            callback=callback,
        )
        stream.start()
        print("Grabando desde el microfono.")
        if duration is None:
            print("Pulsa Ctrl+C para detener.")
            try:
                while True:
                    sd.sleep(200)
            except KeyboardInterrupt:
                pass
        else:
            print(f"Grabando durante {duration:g} segundos.")
            sd.sleep(round(duration * 1000))
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        raise RuntimeError(
            "No se pudo acceder al microfono. Revisa el dispositivo "
            "de entrada y los permisos de Windows."
        ) from exc
    finally:
        if stream is not None:
            stream.stop()
            stream.close()

    if not frames:
        raise RuntimeError("No se capturo audio desde el microfono")

    audio = np.concatenate(frames, axis=0)
    descriptor, output_name = tempfile.mkstemp(prefix="speech-prompt-", suffix=".wav")
    os.close(descriptor)
    Path(output_name).unlink(missing_ok=True)
    output = Path(output_name)
    try:
        with wave.open(str(output), "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(audio.tobytes())
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return output
