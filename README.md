# Speech Prompt CLI

CLI portable para grabar voz desde el microfono, transcribirla con OpenRouter y anadir el resultado a `prompt.md`.

## Requisitos

- Python 3.10 o posterior.
- Windows con un microfono accesible.
- Conexion a internet.
- Creditos y una clave de OpenRouter.

La herramienta no descarga modelos locales ni requiere GPU. El audio se envia al endpoint de speech-to-text de OpenRouter y se elimina el archivo temporal al finalizar.

## Instalacion

Desde Git Bash:

```bash
python -m pip install -e C:/laragon/www/test/speech-recognition
```

Si se prefiere un entorno aislado:

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -e C:/laragon/www/test/speech-recognition
```

## Credenciales

La CLI busca la clave en este orden:

1. `.opencode-secrets` en el directorio actual.
2. `OPENROUTER_API_KEY`.
3. `.opencode-secrets` junto a la instalacion de la herramienta.

`.opencode-secrets` debe contener la clave en su primera linea no vacia. Nunca se debe agregar al repositorio.

## Uso

Desde el repositorio cuyo `prompt.md` se desea actualizar:

```bash
speech-prompt
```

Habla y pulsa `Ctrl+C` para detener la grabacion. La CLI muestra la transcripcion y solicita confirmacion antes de escribirla.

Opciones:

```bash
speech-prompt --file docs/prompt.md
speech-prompt --duration 30
speech-prompt --language es
speech-prompt --model openai/whisper-large-v3
speech-prompt --dry-run
speech-prompt --yes
```

Tambien puede ejecutarse sin instalar el comando:

```bash
python -m speech_prompt
```

## Configuracion opcional

```bash
export OPENROUTER_API_KEY="..."
export SPEECH_PROMPT_MODEL="nvidia/nemotron-3.5-transcribe"
export SPEECH_PROMPT_LANGUAGE="es"
export SPEECH_PROMPT_FILE="prompt.md"
```

Los argumentos de la CLI tienen prioridad sobre las variables de entorno.

## Seguridad

- El audio se envia a OpenRouter para transcripcion.
- El audio se guarda solo temporalmente.
- La clave nunca se imprime ni se guarda en `prompt.md`.
- `--dry-run` permite revisar el texto sin modificar archivos.
- No se agregan archivos de audio al repositorio.

## Desarrollo

Instala las dependencias de prueba y ejecuta:

```bash
python -m pip install -e ".[test]"
python -m pytest
```
