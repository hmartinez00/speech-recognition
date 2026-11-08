from __future__ import annotations

import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
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
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.resize(430, 285)
        self.setMinimumSize(360, 240)
        self._drag_position: QPoint | None = None
        self._path_visible = False
        self.worker: RecordingWorker | None = None
        self.thread: threading.Thread | None = None
        self.audio_path: Path | None = None
        self.full_text_window: QMainWindow | None = None

        self.status_label = QLabel("Listo")
        self.status_label.setObjectName("status")
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("La frase reconocida aparecerá aquí…")
        self.text.setMaximumHeight(92)
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

        self.file_input = QLineEdit(str(Path.cwd() / DEFAULT_FILE))
        self.file_input.setReadOnly(True)

        self.listen_button = QPushButton("🎙")
        self.listen_button.setToolTip("Iniciar escucha")
        self.listen_button.setFixedWidth(48)
        self.listen_button.setObjectName("primary")
        self.listen_button.clicked.connect(self.toggle_recording)
        copy_button = QPushButton("📋")
        copy_button.setToolTip("Copiar texto al portapapeles")
        copy_button.setFixedWidth(42)
        copy_button.clicked.connect(self.copy_text)
        clear_button = QPushButton("🗑")
        clear_button.setToolTip("Limpiar el texto visible")
        clear_button.setFixedWidth(42)
        clear_button.clicked.connect(self.clear_text)
        save_button = QPushButton("💾")
        save_button.setToolTip("Guardar transcripción en el archivo")
        save_button.setFixedWidth(42)
        save_button.clicked.connect(self.save_text)
        review_button = QPushButton("🔍")
        review_button.setToolTip("Abrir ventana con el texto completo")
        review_button.setFixedWidth(42)
        review_button.clicked.connect(self.show_full_text)
        menu_button = QPushButton("☰")
        menu_button.setToolTip("Más opciones")
        menu_button.setFixedWidth(42)
        menu_button.clicked.connect(self.show_options_menu)

        self.minimize_button = QPushButton("—")
        self.minimize_button.setToolTip("Minimizar")
        self.minimize_button.clicked.connect(self.showMinimized)
        self.maximize_button = QPushButton("□")
        self.maximize_button.setToolTip("Maximizar/restaurar")
        self.maximize_button.clicked.connect(self.toggle_maximize)
        close_button = QPushButton("✕")
        close_button.setObjectName("close")
        close_button.setToolTip("Cerrar")
        close_button.clicked.connect(self.close)
        for button in (self.minimize_button, self.maximize_button, close_button):
            button.setFixedWidth(34)

        browse = QPushButton("📁")
        browse.setToolTip("Elegir archivo de transcripción")
        browse.setFixedWidth(42)
        browse.clicked.connect(self.choose_file)

        actions = QHBoxLayout()
        actions.addWidget(self.listen_button, 1)
        actions.addWidget(copy_button)
        actions.addWidget(clear_button)
        actions.addWidget(save_button)
        actions.addWidget(review_button)
        actions.addWidget(browse)

        panel = QVBoxLayout()
        panel.setContentsMargins(14, 12, 14, 12)
        title = QLabel("Speech Prompt")
        title.setObjectName("title")
        subtitle = QLabel("Dicta, revisa y guarda tus instrucciones rápidamente")
        subtitle.setObjectName("subtitle")
        heading = QHBoxLayout()
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(menu_button)
        heading.addWidget(self.minimize_button)
        heading.addWidget(self.maximize_button)
        heading.addWidget(close_button)
        panel.addLayout(heading)
        panel.addWidget(subtitle)
        panel.addSpacing(6)
        panel.addWidget(self.status_label)
        panel.addWidget(self.text, 1)
        panel.addSpacing(5)
        panel.addLayout(actions)

        self.path_row = QHBoxLayout()
        self.path_row.addWidget(self.file_input)
        self.path_row.setContentsMargins(0, 0, 0, 0)
        panel.insertLayout(panel.count() - 1, self.path_row)
        self.file_input.hide()

        container = QWidget()
        container.setObjectName("surface")
        container.setMouseTracking(True)
        container.setLayout(panel)
        self.setCentralWidget(container)
        self.setStyleSheet(
            """
            QWidget#surface { background: #111827; color: #e5e7eb;
                border: 1px solid #334155; border-radius: 16px; }
            QLabel#title { font-size: 20px; font-weight: 700; color: #f9fafb; }
            QLabel#subtitle { color: #9ca3af; font-size: 11px; }
            QLabel#status { color: #67e8f9; font-weight: 600; padding: 2px 0; }
            QPlainTextEdit, QLineEdit { background: #1f2937; border: 1px solid #374151;
                border-radius: 9px; padding: 7px; color: #f9fafb; }
            QPushButton { background: #273449; border: 1px solid #40506a; border-radius: 8px;
                padding: 7px 9px; color: #e5e7eb; font-weight: 600; font-size: 16px; }
            QPushButton:hover { background: #34445d; }
            QPushButton#primary { background: #0891b2; border: none; color: white; }
            QPushButton#primary:hover { background: #06b6d4; }
            QPushButton#close:hover { background: #dc2626; }
            QMenu { background: #1f2937; color: #f9fafb; border: 1px solid #40506a;
                border-radius: 9px; }
            QMenu::item { padding: 7px 24px; }
            QMenu::item:selected { background: #0891b2; }
            QWidget#surface:hover { border-color: #475569; }
            """
        )

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

    def nativeEvent(self, event_type, message):
        """Delegate border hit-testing to Windows for native resizing."""
        if sys.platform == "win32" and event_type == b"windows_generic_MSG":
            import ctypes

            class Point(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            class Msg(ctypes.Structure):
                _fields_ = [
                    ("hwnd", ctypes.c_void_p),
                    ("message", ctypes.c_uint),
                    ("wParam", ctypes.c_size_t),
                    ("lParam", ctypes.c_ssize_t),
                    ("time", ctypes.c_uint),
                    ("pt", Point),
                ]

            msg = Msg.from_address(int(message))
            if msg.message == 0x0084 and not self.isMaximized():  # WM_NCHITTEST
                x = ctypes.c_short(msg.lParam & 0xFFFF).value
                y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                frame = self.frameGeometry()
                margin = 10
                left = x <= frame.left() + margin
                right = x >= frame.right() - margin
                top = y <= frame.top() + margin
                bottom = y >= frame.bottom() - margin
                result = None
                if top and left:
                    result = 13  # HTTOPLEFT
                elif top and right:
                    result = 14  # HTTOPRIGHT
                elif bottom and left:
                    result = 16  # HTBOTTOMLEFT
                elif bottom and right:
                    result = 17  # HTBOTTOMRIGHT
                elif left:
                    result = 10  # HTLEFT
                elif right:
                    result = 11  # HTRIGHT
                elif top:
                    result = 12  # HTTOP
                elif bottom:
                    result = 15  # HTBOTTOM
                if result is not None:
                    return True, result
        return super().nativeEvent(event_type, message)

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        position = event.position().toPoint()
        if (
            position.y() < 48
            and not self.childAt(position) in
            (self.minimize_button, self.maximize_button)
        ):
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_position = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.position().y() < 48:
            self.toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setText("□")
        else:
            self.showMaximized()
            self.maximize_button.setText("❐")

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
        self.listen_button.setText("⏹")
        self.listen_button.setToolTip("Detener escucha")
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
        self.listen_button.setText("🎙")
        self.listen_button.setToolTip("Iniciar escucha")

    def copy_text(self) -> None:
        QApplication.clipboard().setText(self.text.toPlainText())
        self.status_label.setText("Texto copiado al portapapeles")

    def clear_text(self) -> None:
        self.text.clear()
        self.status_label.setText("Texto limpiado")

    def show_full_text(self) -> None:
        dialog = QMainWindow(self)
        dialog.setWindowTitle("Texto completo — Speech Prompt")
        dialog.setMinimumSize(620, 420)
        editor = QPlainTextEdit(dialog)
        editor.setPlainText(self.text.toPlainText())
        editor.setReadOnly(False)
        dialog.setCentralWidget(editor)
        dialog.show()
        self.full_text_window = dialog

    def show_options_menu(self) -> None:
        menu = QMenu(self)
        choose_action = QAction("Elegir archivo de transcripción", self)
        choose_action.triggered.connect(self.choose_file)
        menu.addAction(choose_action)
        path_action = QAction("Mostrar ruta del archivo", self)
        path_action.setCheckable(True)
        path_action.setChecked(self._path_visible)
        path_action.triggered.connect(self.toggle_path_visibility)
        menu.addAction(path_action)
        full_text_action = QAction("Abrir auditoría del texto", self)
        full_text_action.triggered.connect(self.show_full_text)
        menu.addAction(full_text_action)
        menu.addSeparator()
        about_action = QAction("Acerca de Speech Prompt", self)
        about_action.triggered.connect(
            lambda: QMessageBox.information(
                self, "Speech Prompt", "Dictado y transcripción rápida para tu flujo de trabajo."
            )
        )
        menu.addAction(about_action)
        menu.exec(self.mapToGlobal(self.rect().topRight()))

    def toggle_path_visibility(self, visible: bool) -> None:
        self._path_visible = visible
        self.file_input.setVisible(visible)

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
