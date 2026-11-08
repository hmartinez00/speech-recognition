from __future__ import annotations

import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from .config import (
    DEFAULT_FILE,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL,
    resolve_api_key,
    resolve_value,
)
from .recorder import SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH
from .transcriber import TranscriptionError, transcribe_audio
from .writer import append_transcription


class RecordingWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    status = Signal(str)

    def __init__(self, duration: float | None = None) -> None:
        super().__init__()
        self.duration = duration
        self.stop_requested = threading.Event()

    def stop(self) -> None:
        self.stop_requested.set()

    def run(self) -> None:
        try:
            import numpy as np
            import sounddevice as sd
            import tempfile
            import wave
            import os

            frames: list[np.ndarray] = []

            def callback(indata, frame_count, time_info, status):
                if status:
                    self.status.emit(f"Aviso del micrófono: {status}")
                frames.append(indata.copy())

            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                callback=callback,
            )
            stream.start()
            self.status.emit("Escuchando… habla ahora")
            elapsed = 0.0
            while not self.stop_requested.is_set() and (
                self.duration is None or elapsed < self.duration
            ):
                sd.sleep(100)
                elapsed += 0.1
            stream.stop()
            stream.close()

            if not frames:
                raise RuntimeError("No se capturó audio desde el micrófono")
            audio = np.concatenate(frames, axis=0)
            descriptor, output_name = tempfile.mkstemp(prefix="speech-prompt-", suffix=".wav")
            os.close(descriptor)
            output = Path(output_name)
            with wave.open(str(output), "wb") as wav_file:
                wav_file.setnchannels(CHANNELS)
                wav_file.setsampwidth(SAMPLE_WIDTH)
                wav_file.setframerate(SAMPLE_RATE)
                wav_file.writeframes(audio.tobytes())
            self.finished.emit(output)
        except Exception as exc:
            self.failed.emit(str(exc))


class SpeechPromptWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Speech Prompt")
        self.setMinimumSize(650, 520)
        self.worker: RecordingWorker | None = None
        self.thread: threading.Thread | None = None
        self.audio_path: Path | None = None

        self.status_label = QLabel("Listo")
        self.status_label.setObjectName("status")
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("La frase reconocida aparecerá aquí…")
        self.text.setMinimumHeight(180)

        self.file_input = QLineEdit(str(Path.cwd() / DEFAULT_FILE))
        self.file_input.setReadOnly(True)
        browse = QPushButton("📁  Elegir archivo")
        browse.clicked.connect(self.choose_file)

        self.listen_button = QPushButton("🎙  Iniciar escucha")
        self.listen_button.setObjectName("primary")
        self.listen_button.clicked.connect(self.toggle_recording)
        copy_button = QPushButton("📋  Copiar texto")
        copy_button.clicked.connect(self.copy_text)
        clear_button = QPushButton("🗑  Limpiar")
        clear_button.clicked.connect(self.clear_text)
        save_button = QPushButton("Guardar en archivo")
        save_button.clicked.connect(self.save_text)

        file_row = QHBoxLayout()
        file_row.addWidget(self.file_input, 1)
        file_row.addWidget(browse)
        actions = QHBoxLayout()
        actions.addWidget(self.listen_button, 1)
        actions.addWidget(copy_button)
        actions.addWidget(clear_button)
        actions.addWidget(save_button)

        panel = QVBoxLayout()
        title = QLabel("Speech Prompt")
        title.setObjectName("title")
        subtitle = QLabel("Dicta, revisa y guarda tus instrucciones rápidamente")
        subtitle.setObjectName("subtitle")
        panel.addWidget(title)
        panel.addWidget(subtitle)
        panel.addSpacing(18)
        panel.addWidget(self.status_label)
        panel.addWidget(self.text, 1)
        panel.addSpacing(12)
        panel.addWidget(QLabel("Archivo de transcripción"))
        panel.addLayout(file_row)
        panel.addSpacing(12)
        panel.addLayout(actions)

        container = QWidget()
        container.setLayout(panel)
        self.setCentralWidget(container)
        self.setStyleSheet(
            """
            QWidget { background: #111827; color: #e5e7eb; }
            QMainWindow { background: #111827; }
            QLabel#title { font-size: 28px; font-weight: 700; color: #f9fafb; }
            QLabel#subtitle { color: #9ca3af; font-size: 13px; }
            QLabel#status { color: #67e8f9; font-weight: 600; padding: 8px 0; }
            QPlainTextEdit, QLineEdit { background: #1f2937; border: 1px solid #374151;
                border-radius: 10px; padding: 12px; color: #f9fafb; }
            QPushButton { background: #273449; border: 1px solid #40506a; border-radius: 9px;
                padding: 11px 15px; color: #e5e7eb; font-weight: 600; }
            QPushButton:hover { background: #34445d; }
            QPushButton#primary { background: #0891b2; border: none; color: white; }
            QPushButton#primary:hover { background: #06b6d4; }
            """
        )

    def choose_file(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Seleccionar archivo de transcripción", self.file_input.text(),
            "Archivos de texto (*.md *.txt);;Todos los archivos (*)",
        )
        if filename:
            self.file_input.setText(filename)

    def toggle_recording(self) -> None:
        if self.worker is not None:
            self.worker.stop()
            self.status_label.setText("Procesando audio…")
            self.listen_button.setEnabled(False)
            return
        self.worker = RecordingWorker()
        self.worker.finished.connect(self.transcribe)
        self.worker.failed.connect(self.recording_failed)
        self.worker.status.connect(self.status_label.setText)
        self.listen_button.setText("⏹  Detener escucha")
        self.thread = threading.Thread(target=self.worker.run, daemon=True)
        self.thread.start()

    def transcribe(self, path: Path) -> None:
        self.audio_path = path
        self.status_label.setText("Transcribiendo…")
        try:
            cwd = Path.cwd()
            key = resolve_api_key(cwd, Path(__file__).resolve().parent.parent)
            if not key:
                raise RuntimeError("No se encontró la clave de OpenRouter")
            model = resolve_value(None, "SPEECH_PROMPT_MODEL", DEFAULT_MODEL)
            language = resolve_value(None, "SPEECH_PROMPT_LANGUAGE", DEFAULT_LANGUAGE)
            text = transcribe_audio(path, key, model, language)
            self.text.setPlainText(text)
            self.status_label.setText("Transcripción lista")
        except (RuntimeError, ValueError, TranscriptionError, OSError) as exc:
            self.recording_failed(str(exc))
        finally:
            path.unlink(missing_ok=True)
            self.reset_recording()

    def recording_failed(self, message: str) -> None:
        self.status_label.setText("Error")
        QMessageBox.critical(self, "Speech Prompt", message)
        self.reset_recording()

    def reset_recording(self) -> None:
        self.worker = None
        self.thread = None
        self.listen_button.setEnabled(True)
        self.listen_button.setText("🎙  Iniciar escucha")

    def copy_text(self) -> None:
        QApplication.clipboard().setText(self.text.toPlainText())
        self.status_label.setText("Texto copiado al portapapeles")

    def clear_text(self) -> None:
        self.text.clear()
        self.status_label.setText("Texto limpiado")

    def save_text(self) -> None:
        value = self.text.toPlainText().strip()
        if not value:
            QMessageBox.information(self, "Speech Prompt", "No hay texto para guardar.")
            return
        destination = Path(self.file_input.text())
        try:
            append_transcription(destination, value)
            self.status_label.setText(f"Guardado en {destination}")
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Speech Prompt", str(exc))


def main() -> int:
    app = QApplication(sys.argv)
    window = SpeechPromptWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
