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

### Usarla desde otro repositorio

No hace falta instalarla en cada repositorio. Instalála una sola vez en el entorno de Python de cada máquina. En PowerShell, desde cualquier directorio:

```bash
python -m pip install -e "C:\laragon\www\test\speech-recognition"
```

La instalación registra el comando `speech-prompt`. Comprueba que Windows lo encuentra:

```powershell
Get-Command speech-prompt
speech-prompt --help
```

Si `Get-Command` no encuentra el comando, agrega al `PATH` de usuario la carpeta `Scripts` de ese Python. Puedes obtener la ruta exacta así:

```powershell
python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
```

Una vez instalado, cambia al repositorio donde quieras guardar la transcripcion y ejecuta el comando, sin copiar archivos ni reinstalar. En PowerShell:

```bash
Set-Location "C:\ruta\a\mi-otro-repositorio"
speech-prompt --duration 8 --dry-run
```

En Git Bash:

```bash
cd /c/ruta/a/mi-otro-repositorio
speech-prompt --duration 8 --dry-run
```

La prueba graba durante 8 segundos, muestra la transcripcion y no modifica archivos. Si todo esta bien, ejecuta el comando sin `--dry-run`:

```bash
speech-prompt
```

La grabacion continua hasta que pulses `Ctrl+C`. Luego revisa la transcripcion y confirma cuando la CLI lo solicite. Por defecto, se anade al `prompt.md` del directorio actual.

Para escribir en otro archivo dentro del repositorio, pasa una ruta relativa. Si la carpeta no existe, se crea:

```bash
speech-prompt --file "docs\notas.md"
```

Tambien puedes escribir directamente a cualquier ruta, incluso fuera del repositorio:

```bash
speech-prompt --file "C:\Users\HP\Documents\dictado.md"
```

La ruta relativa se interpreta desde el directorio actual de la terminal. La transcripcion se anade al final del archivo destino; el flujo actual no inserta en la posicion del cursor. La clave se busca primero en `.opencode-secrets` del directorio actual, luego en `OPENROUTER_API_KEY` y finalmente junto a la instalacion de la herramienta.

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
