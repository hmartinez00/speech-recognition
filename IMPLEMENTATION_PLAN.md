# Speech Prompt CLI: Linea Base de Implementacion

## 1. Objetivo

Crear una herramienta CLI portable para Git Bash en Windows que capture voz desde el microfono, la transcriba mediante un modelo de speech-to-text de OpenRouter y anada el resultado al archivo `prompt.md` del repositorio actual.

La herramienta debe poder instalarse una sola vez y utilizarse desde multiples repositorios sin agregar codigo de aplicacion a esos repositorios. El cambio normal en un repositorio consumidor sera unicamente la actualizacion explicita de su `prompt.md`.

## 2. Alcance de la primera version

La primera version debe incluir:

- Captura de audio desde el microfono local.
- Grabacion interactiva detenida con `Ctrl+C`.
- Duracion opcional mediante parametro CLI.
- Generacion de audio temporal en formato WAV PCM mono a 16 kHz.
- Transcripcion remota mediante el endpoint STT de OpenRouter.
- Modelo configurable, con `nvidia/nemotron-3.5-transcribe` como valor inicial.
- Idioma configurable, con `es` como valor inicial.
- Escritura append-only en `prompt.md`.
- Confirmacion antes de modificar el archivo.
- Opcion no interactiva para aceptar automaticamente.
- Seleccion de archivo destino mediante `--file`.
- Lectura segura de la clave desde variables de entorno o `.opencode-secrets`.
- Eliminacion del audio temporal despues de la transcripcion.
- Mensajes de error accionables para problemas de microfono, red, autenticacion y API.
- Documentacion de instalacion y uso desde Git Bash.

Fuera del alcance inicial:

- Identificacion biometrica del hablante.
- Diarizacion de multiples hablantes.
- Interfaz grafica o servidor web.
- Procesamiento local con Whisper.
- Edicion semantica o reescritura de la transcripcion por un modelo de texto.
- Sincronizacion automatica con Git.
- Modificacion de archivos distintos al destino indicado.

## 3. Arquitectura

La arquitectura sera modular y pequena:

```text
Microfono
   |
   v
Grabador local
   |
   v
WAV temporal
   |
   v
Cliente OpenRouter STT
   |
   v
Texto transcrito
   |
   v
Confirmacion
   |
   v
prompt.md
```

Estructura objetivo:

```text
speech-recognition/
├── speech_prompt/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── recorder.py
│   ├── transcriber.py
│   └── writer.py
├── pyproject.toml
├── README.md
├── IMPLEMENTATION_PLAN.md
├── .gitignore
└── prompt.md
```

Responsabilidades:

- `cli.py`: argumentos, flujo principal, mensajes y codigo de salida.
- `config.py`: modelo, idioma, archivo destino y descubrimiento de credenciales.
- `recorder.py`: inicializacion del dispositivo, captura y escritura del WAV temporal.
- `transcriber.py`: codificacion del audio, peticion HTTP y validacion de la respuesta.
- `writer.py`: formateo de la entrada y escritura segura en el archivo destino.
- `__main__.py`: punto de entrada para `python -m speech_prompt`.
- `__init__.py`: version del paquete y exportaciones minimas.

## 4. Integracion con OpenRouter

### 4.1 Endpoint

La integracion utilizara:

```text
POST https://openrouter.ai/api/v1/audio/transcriptions
```

La autenticacion sera mediante:

```text
Authorization: Bearer <OPENROUTER_API_KEY>
```

La implementacion inicial debe usar la biblioteca estandar de Python (`urllib`) para minimizar dependencias. Si el manejo de multipart o los requisitos del proveedor lo justifican, se podra usar el cliente oficial compatible con OpenAI en una fase posterior.

### 4.2 Peticion JSON

La ruta principal enviara el audio como Base64 sin prefijo de data URI:

```json
{
  "model": "nvidia/nemotron-3.5-transcribe",
  "input_audio": {
    "data": "<base64 del WAV>",
    "format": "wav"
  },
  "language": "es",
  "temperature": 0
}
```

La respuesta minima esperada es:

```json
{
  "text": "Texto reconocido desde el microfono.",
  "usage": {
    "seconds": 8.4,
    "cost": 0.000277
  }
}
```

La implementacion debe requerir que `text` exista y sea una cadena. Los campos de `usage` se trataran como opcionales y solo se mostraran si la respuesta los contiene.

### 4.3 Modelos

Valor por defecto:

```text
nvidia/nemotron-3.5-transcribe
```

Alternativa configurable:

```text
openai/whisper-large-v3
```

El modelo nunca debe quedar hardcodeado unicamente en el codigo. Debe poder definirse por parametro y, opcionalmente, por variable de entorno.

Ejemplos:

```bash
speech-prompt --model nvidia/nemotron-3.5-transcribe
speech-prompt --model openai/whisper-large-v3
```

La herramienta no debe asumir que todos los modelos de OpenRouter aceptan los mismos parametros adicionales. `model`, `input_audio`, `format`, `language` y `temperature` son la base; las opciones avanzadas solo se agregaran cuando esten documentadas y probadas para el modelo seleccionado.

## 5. Configuracion y credenciales

### 5.1 Orden de descubrimiento

La clave de OpenRouter se resolvera en este orden:

1. `.opencode-secrets` en el directorio de trabajo actual.
2. Variable de entorno `OPENROUTER_API_KEY`.
3. `.opencode-secrets` junto a la raiz de la herramienta instalada.

El archivo de secretos se interpretara como una sola linea. Se permitira espacio en blanco alrededor, pero nunca se imprimira ni se incluira en errores.

El archivo existente en este repositorio esta excluido por `.gitignore` y debe permanecer fuera del seguimiento de Git.

### 5.2 Configuracion funcional

Valores iniciales previstos:

```text
SPEECH_PROMPT_MODEL=nvidia/nemotron-3.5-transcribe
SPEECH_PROMPT_LANGUAGE=es
SPEECH_PROMPT_FILE=prompt.md
```

Los parametros CLI tendran prioridad sobre las variables de entorno.

La clave nunca debe:

- Escribirse en el codigo fuente.
- Incluirse en `pyproject.toml` o `README.md`.
- Aparecer en logs o mensajes de error.
- Guardarse en el archivo de transcripcion.
- Incluirse en commits.
- Imprimirse durante pruebas.

## 6. Contrato de CLI

El nombre previsto del comando sera:

```bash
speech-prompt
```

El modulo tambien debe ejecutarse con:

```bash
python -m speech_prompt
```

Opciones iniciales:

```text
--file PATH       Archivo destino. Por defecto: prompt.md
--model MODEL     Modelo de OpenRouter
--language CODE   Idioma del audio. Por defecto: es
--duration SEC    Duracion fija. Si se omite, se graba hasta Ctrl+C
--yes             No pedir confirmacion antes de escribir
--dry-run         Transcribir y mostrar, sin modificar archivos
--version         Mostrar la version
--help            Mostrar ayuda
```

Ejemplos:

```bash
speech-prompt
speech-prompt --file docs/prompt.md
speech-prompt --duration 30
speech-prompt --language es --model openai/whisper-large-v3
speech-prompt --dry-run
speech-prompt --yes
```

Flujo interactivo esperado:

```text
Grabando desde el microfono.
Pulsa Ctrl+C para detener.

Deteniendo grabacion...
Transcribiendo con nvidia/nemotron-3.5-transcribe...

Texto reconocido:
<transcripcion>

Anadir esta transcripcion a prompt.md? [Y/n]
Texto anadido a prompt.md.
```

Los mensajes visibles pueden usar caracteres ASCII para funcionar correctamente en diferentes configuraciones de Git Bash.

Codigos de salida previstos:

- `0`: operacion completada o simulacion completada.
- `1`: error de uso, configuracion, grabacion, red, API o escritura.
- `2`: operacion cancelada por el usuario.

## 7. Captura de audio

La primera implementacion usara `sounddevice` y `numpy`:

- Un canal mono.
- Frecuencia de muestreo de 16.000 Hz.
- Muestras PCM de 16 bits.
- Contenedor WAV.
- Archivo temporal creado con la biblioteca estandar.
- Eliminacion garantizada mediante `try/finally`.

`Ctrl+C` debe detener la grabacion limpiamente, cerrar el stream y conservar la posibilidad de mostrar la transcripcion si el audio se capturo correctamente.

La duracion fija debe validar que sea un numero positivo. La grabacion interactiva debe manejar la ausencia de dispositivo de entrada con un mensaje que indique revisar el microfono predeterminado de Windows y los permisos del sistema.

No se usara FFmpeg en la primera version. El WAV generado directamente por `sounddevice` evita una dependencia externa adicional.

## 8. Escritura en el archivo destino

La escritura sera append-only y no sobrescribira el contenido existente.

Formato previsto:

```md
## 2026-11-02 16:10

Necesito implementar autenticacion con JWT y agregar pruebas para el endpoint de usuarios.
```

Reglas:

- Crear el archivo si no existe.
- Mantener el contenido anterior intacto.
- Asegurar una separacion clara entre entradas.
- Usar UTF-8.
- Crear el directorio padre si es necesario solo cuando el usuario lo haya indicado explicitamente.
- No modificar ningun archivo en `--dry-run`.
- No escribir una transcripcion vacia.
- Evitar duplicar saltos de linea innecesarios.

La escritura debe ser tan atomica como sea razonable: construir la entrada completa, abrir el archivo en modo append y escribirla en una sola operacion logica. Si el archivo no es escribible, el error debe identificar el destino sin revelar informacion sensible.

## 9. Seguridad y privacidad

El audio se enviara a OpenRouter para su transcripcion. La CLI debe comunicar esta propiedad en la documentacion y en la ayuda, pero no necesita imprimir advertencias repetitivas en cada ejecucion.

Medidas obligatorias:

- No registrar el audio.
- No conservar el WAV temporal despues de la ejecucion.
- No registrar la API key ni cabeceras de autenticacion.
- No incluir secretos en excepciones.
- No realizar peticiones a endpoints distintos de los configurados.
- Validar el esquema basico de la respuesta antes de escribir.
- Permitir `--dry-run` para revisar el texto sin modificar el repositorio.
- Mantener `.opencode-secrets` en `.gitignore`.

La herramienta reconoce voz a texto. No implementa verificacion de identidad ni reconocimiento biometrico del hablante.

## 10. Manejo de errores

Los errores deben ser breves, concretos y accionables.

Casos minimos:

- Falta la API key: indicar `OPENROUTER_API_KEY` o `.opencode-secrets`.
- API key invalida: indicar revisar la clave sin mostrarla.
- Credito insuficiente o limite alcanzado: mostrar el estado HTTP y una accion general.
- Modelo no disponible: indicar el modelo y sugerir `--model openai/whisper-large-v3`.
- Peticion rechazada: mostrar el mensaje seguro devuelto por la API.
- Timeout o fallo de red: indicar revisar la conexion y reintentar.
- No existe microfono: indicar revisar dispositivo y permisos.
- Dependencia de audio ausente: indicar el comando de instalacion.
- Archivo destino no escribible: mostrar la ruta y revisar permisos.
- Respuesta sin `text`: tratarla como error de proveedor.
- Cancelacion con `Ctrl+C`: limpiar recursos y salir con codigo `2` cuando corresponda.

No se deben mostrar trazas completas por defecto. Se podra anadir una opcion `--debug` en una fase posterior, siempre excluyendo secretos.

## 11. Dependencias

Dependencia de ejecucion prevista:

```text
sounddevice
numpy
```

La red, Base64, JSON, WAV, archivos temporales, argumentos y fechas deben resolverse con la biblioteca estandar de Python cuando sea practico.

Dependencias de desarrollo opcionales:

```text
pytest
ruff
```

La configuracion de empaquetado se realizara con `pyproject.toml` y un punto de entrada:

```toml
[project.scripts]
speech-prompt = "speech_prompt.cli:main"
```

## 12. Portabilidad entre repositorios

Durante el desarrollo local:

```bash
python -m pip install -e C:/laragon/www/test/speech-recognition
```

Despues, desde cualquier repositorio:

```bash
speech-prompt
```

Tambien debe ser posible ejecutar la herramienta sin instalacion global:

```bash
python C:/laragon/www/test/speech-recognition -f prompt.md
```

El directorio de trabajo actual determinara el archivo destino por defecto. Esto permite utilizar la misma instalacion en multiples repositorios sin copiar codigo.

## 13. Pruebas previstas

### Pruebas unitarias

- Resolucion de la API key desde variable de entorno.
- Resolucion desde `.opencode-secrets` cuando no existe variable de entorno.
- Rechazo de un archivo de secretos vacio.
- Prioridad de argumentos CLI sobre variables de entorno.
- Construccion de la peticion OpenRouter sin exponer la clave.
- Validacion de respuestas con y sin `text`.
- Formateo de entradas Markdown.
- Creacion de un archivo destino inexistente.
- Append sin alterar contenido anterior.
- `--dry-run` sin escritura.
- Validacion de duraciones invalidas.

### Pruebas de integracion

- Cliente contra un endpoint HTTP simulado.
- Respuesta valida de OpenRouter.
- Error HTTP de autenticacion.
- Error HTTP de modelo no encontrado.
- Grabacion con dispositivo disponible, si el entorno de pruebas lo permite.

### Prueba manual inicial

1. Instalar las dependencias.
2. Ejecutar una grabacion de 5 a 10 segundos.
3. Confirmar que el texto aparece correctamente.
4. Confirmar que `prompt.md` conserva su contenido anterior.
5. Confirmar que el audio temporal desaparece.
6. Ejecutar desde otro directorio con `--file prompt.md`.
7. Ejecutar `--dry-run` y verificar que no hay cambios.
8. Ejecutar `git status --short` y comprobar que no aparece ningun secreto ni audio.

## 14. Fases de implementacion

### Fase 1: esqueleto y configuracion

- Crear el paquete Python.
- Crear `pyproject.toml`.
- Implementar version y punto de entrada.
- Implementar descubrimiento de configuracion y credenciales.
- Actualizar `.gitignore` para temporales y entornos virtuales si es necesario.

### Fase 2: grabacion

- Implementar captura interactiva.
- Implementar duracion fija.
- Generar WAV temporal.
- Manejar `Ctrl+C` y errores de dispositivo.

### Fase 3: transcripcion OpenRouter

- Implementar codificacion Base64.
- Implementar peticion al endpoint STT.
- Implementar seleccion de modelo e idioma.
- Validar respuesta y errores HTTP.
- Mostrar uso y coste solo si estan disponibles.

### Fase 4: persistencia

- Implementar formato Markdown con timestamp.
- Implementar confirmacion.
- Implementar `--yes` y `--dry-run`.
- Implementar escritura segura en el archivo destino.

### Fase 5: calidad y portabilidad

- Escribir README.
- Agregar pruebas unitarias.
- Probar desde Git Bash.
- Verificar ejecucion desde otro repositorio.
- Verificar ausencia de secretos y temporales rastreables.

## 15. Criterios de aceptacion

La primera version se considerara lista cuando:

- `python -m speech_prompt --help` funcione.
- `speech-prompt --help` funcione despues de una instalacion editable.
- La herramienta capture audio del microfono en Windows.
- Una grabacion corta se transcriba con OpenRouter.
- La clave pueda leerse desde `.opencode-secrets` sin imprimirse.
- `prompt.md` se cree o actualice en el repositorio actual.
- Las entradas anteriores permanezcan intactas.
- `--file` permita elegir otro destino.
- `--dry-run` no modifique archivos.
- `--yes` evite la confirmacion interactiva.
- El audio temporal se elimine incluso cuando la transcripcion falle.
- Los errores principales tengan mensajes accionables.
- No haya secretos, audio ni temporales incluidos en Git.
- El README documente instalacion, configuracion y uso.

## 16. Decisiones abiertas para fases posteriores

Estas decisiones no bloquean la primera implementacion:

- Soporte de proveedores alternativos ademas de OpenRouter.
- Backend local con Whisper.
- Seleccion automatica entre varios modelos.
- Compresion a MP3 u Opus para grabaciones largas.
- Reintentos con backoff para errores transitorios.
- Correccion opcional de puntuacion mediante un modelo de texto.
- Modo continuo que agregue varias transcripciones en una sesion.
- Instalador o binario independiente para Windows.
- Soporte de dispositivos de entrada seleccionables.

## 17. Decision base

La implementacion comenzara como una CLI Python pequena, instalable y modular, usando captura local con `sounddevice`, audio WAV temporal, el endpoint STT de OpenRouter y escritura append-only en `prompt.md`.

El modelo inicial sera `nvidia/nemotron-3.5-transcribe`, con `openai/whisper-large-v3` como alternativa seleccionable. La herramienta no dependera de un repositorio consumidor concreto y no modificara archivos distintos del destino que el usuario indique.
