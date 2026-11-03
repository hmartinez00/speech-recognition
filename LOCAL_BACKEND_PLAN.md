# Speech Prompt CLI: Plan de Backend Local

## 1. Objetivo

Definir una alternativa de transcripcion completamente local para la CLI `speech-prompt`. El audio se capturara desde el microfono, se procesara con un modelo Whisper instalado en el equipo y el texto resultante se anadira a `prompt.md`, sin enviar grabaciones a OpenRouter ni a otro servicio remoto.

Este plan debe poder implementarse como un proveedor adicional dentro de la misma CLI, reutilizando la captura de audio, el manejo de configuracion y la escritura Markdown definidos en `IMPLEMENTATION_PLAN.md`.

## 2. Alcance

La primera version del backend local debe incluir:

- Captura de audio desde el microfono.
- Grabacion interactiva mediante `Ctrl+C`.
- Duracion fija opcional.
- Audio temporal WAV PCM mono a 16 kHz.
- Transcripcion local mediante `faster-whisper`.
- Seleccion configurable del modelo Whisper.
- Idioma configurable, con `es` como valor por defecto.
- Escritura append-only en `prompt.md`.
- Confirmacion antes de persistir el texto.
- Modo `--dry-run`.
- Eliminacion del audio temporal al finalizar.
- Funcionamiento sin API key y sin conexion despues de instalar el modelo.

Fuera del alcance inicial:

- Identificacion biometrica del hablante.
- Diarizacion.
- Entrenamiento o ajuste fino del modelo.
- Interfaz grafica.
- Conversion automatica entre formatos de audio.
- Uso de GPU como requisito obligatorio.
- Distribucion de los pesos del modelo dentro del repositorio.

## 3. Arquitectura

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
faster-whisper / CTranslate2
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

La implementacion debe compartir con el backend OpenRouter los siguientes componentes:

- `cli.py`: argumentos y flujo de usuario.
- `config.py`: configuracion comun.
- `recorder.py`: captura de audio.
- `writer.py`: persistencia en Markdown.

El backend local debe quedar aislado en un modulo propio:

```text
speech_prompt/
├── transcriber.py
└── providers/
    ├── __init__.py
    └── local_whisper.py
```

La CLI seleccionara el proveedor mediante una opcion:

```bash
speech-prompt --provider local
```

La interfaz comun prevista es equivalente a:

```python
class Transcriber(Protocol):
    def transcribe(self, audio_path: Path, language: str) -> str:
        ...
```

El flujo principal no debe conocer detalles de Whisper, CTranslate2 ni del proveedor remoto.

## 4. Motor de transcripcion

Se recomienda `faster-whisper` como primera implementacion local.

Motivos:

- Usa CTranslate2 en lugar de ejecutar Whisper mediante PyTorch completo.
- Tiene menor consumo en muchas configuraciones de CPU.
- Permite cuantizacion mediante `compute_type`.
- Soporta modelos Whisper conocidos.
- Proporciona segmentos y metadatos de idioma.
- Tiene una API Python sencilla.

Ejemplo conceptual:

```python
from faster_whisper import WhisperModel

model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe(
    str(audio_path),
    language="es",
    beam_size=5,
)
text = " ".join(segment.text.strip() for segment in segments).strip()
```

La instancia del modelo debe cargarse una sola vez por proceso. No debe recrearse para cada segmento o peticion.

## 5. Modelos disponibles

El modelo debe ser configurable mediante CLI o variable de entorno.

Valores orientativos:

| Modelo | Calidad | Velocidad CPU | Memoria | Uso recomendado |
| --- | --- | --- | --- | --- |
| `tiny` | Baja | Muy alta | Muy baja | Pruebas rapidas |
| `base` | Basica | Alta | Baja | Equipos limitados |
| `small` | Buena | Media | Media | Valor por defecto recomendado |
| `medium` | Muy buena | Baja | Alta | Mejor calidad en CPU potente |
| `large-v3` | Excelente | Muy baja en CPU | Muy alta | GPU o equipos potentes |

La primera configuracion recomendada es:

```text
SPEECH_PROMPT_PROVIDER=local
SPEECH_PROMPT_LOCAL_MODEL=small
SPEECH_PROMPT_LANGUAGE=es
```

Uso equivalente:

```bash
speech-prompt --provider local --local-model small
```

El modelo no debe descargarse silenciosamente sin informar al usuario. En la primera ejecucion la CLI debe indicar que los pesos seran descargados y aproximadamente que implica el proceso.

## 6. Dispositivo y cuantizacion

La implementacion inicial debe priorizar CPU para maximizar portabilidad:

```text
device=cpu
compute_type=int8
```

En una fase posterior se puede permitir:

```bash
speech-prompt --provider local --device cuda --compute-type float16
```

Valores previstos:

- CPU: `int8`, o `int8_float16` cuando el entorno lo soporte.
- CUDA: `float16`.
- GPU con poca memoria: cuantizacion compatible con el hardware.

La CLI debe validar la combinacion solicitada y producir un error accionable si el dispositivo no esta disponible.

No se debe asumir la existencia de CUDA, cuDNN ni una GPU NVIDIA.

## 7. Descarga y almacenamiento del modelo

La primera ejecucion puede descargar los pesos desde el origen configurado por `faster-whisper`/Hugging Face. Despues de la descarga, la transcripcion debe poder ejecutarse offline.

Requisitos:

- Mostrar un mensaje claro durante la descarga inicial.
- No almacenar los pesos dentro del repositorio consumidor.
- Respetar la cache normal del usuario.
- Permitir un directorio alternativo mediante configuracion futura.
- Informar si el modelo requerido no esta disponible localmente y no hay conexion.

El tamanio exacto depende del modelo y de su cuantizacion. La documentacion debe evitar prometer un numero fijo y recomendar verificar espacio libre antes de descargar modelos grandes.

## 8. Contrato de CLI

El backend local debe conservar la misma CLI general:

```bash
speech-prompt --provider local
```

Opciones especificas o comunes:

```text
--file PATH             Archivo destino. Por defecto: prompt.md
--provider PROVIDER     local u openrouter
--local-model MODEL     tiny, base, small, medium o large-v3
--device DEVICE         cpu o cuda
--compute-type TYPE     int8, float16 u otro tipo compatible
--language CODE         Idioma. Por defecto: es
--duration SEC          Duracion fija de grabacion
--yes                   No pedir confirmacion
--dry-run               No modificar archivos
```

Ejemplos:

```bash
speech-prompt --provider local
speech-prompt --provider local --local-model base
speech-prompt --provider local --local-model small --duration 30
speech-prompt --provider local --dry-run
```

En la primera ejecucion, la salida debe distinguir entre:

```text
Cargando modelo local: small
Descargando el modelo si no esta disponible en la cache...
```

y el procesamiento normal:

```text
Transcribiendo localmente...
```

## 9. Dependencias

Dependencias de ejecucion previstas:

```text
sounddevice
numpy
faster-whisper
```

`faster-whisper` puede instalar dependencias binarias adicionales. La instalacion debe probarse especificamente con Python 3.13 en Windows antes de declarar la combinacion como soportada.

Si una dependencia no dispone de wheel compatible con el entorno del usuario, la CLI debe documentar el error y ofrecer como alternativa el backend OpenRouter, en lugar de ocultar o ignorar el problema.

No se debe incluir PyTorch como dependencia si `faster-whisper` no lo necesita para la configuracion elegida.

## 10. Privacidad

Ventajas de privacidad:

- El audio no sale del equipo durante la transcripcion.
- No se necesita API key.
- La transcripcion puede funcionar sin internet despues de la descarga del modelo.
- Los archivos temporales pueden eliminarse localmente.

Limitaciones:

- La descarga inicial del modelo requiere red.
- El origen del modelo y sus terminos deben revisarse antes de distribuir la herramienta.
- El proceso puede dejar cache del modelo en el perfil del usuario.
- La transcripcion queda escrita en `prompt.md`, que puede estar bajo seguimiento de Git.

La documentacion debe dejar claro que backend local significa que el audio no se envia al servicio STT, pero no implica que ningun dato abandone el equipo durante la descarga inicial.

## 11. Rendimiento esperado

El rendimiento dependera de:

- Procesador.
- Memoria disponible.
- Modelo elegido.
- Cuantizacion.
- Duracion del audio.
- Ruido y complejidad del habla.
- Uso simultaneo de otros procesos.

La CLI no debe prometer transcripcion en tiempo real. La primera version grabara una toma completa y despues procesara el archivo.

Para mantener una experiencia razonable:

- Recomendar `small` como equilibrio inicial.
- Permitir `base` en equipos lentos.
- Evitar cargar `large-v3` automaticamente.
- Mostrar una indicacion de progreso cuando el motor lo permita.
- Mantener el modelo cargado mientras dure el proceso.

## 12. Audio y limites

La captura compartida con el backend OpenRouter sera:

- WAV PCM.
- Mono.
- 16 kHz.
- 16 bits por muestra.

El backend local no tiene el limite de carga de una API remota, pero grabaciones muy largas aumentan el consumo de memoria, el tiempo de procesamiento y la posibilidad de errores. La CLI debe recomendar tomas cortas y permitir `--duration`.

Una futura version puede dividir grabaciones largas en segmentos, pero no es requisito de la primera version.

## 13. Persistencia en `prompt.md`

La persistencia sera identica a la del backend OpenRouter:

```md
## 2026-11-02 16:10

Texto transcrito localmente.
```

Reglas:

- Append-only.
- UTF-8.
- No sobrescribir entradas anteriores.
- No escribir texto vacio.
- Confirmar antes de modificar salvo `--yes`.
- No modificar archivos en `--dry-run`.
- Eliminar el WAV temporal incluso si la escritura falla.

## 14. Manejo de errores

Casos minimos:

- `faster-whisper` no instalado: mostrar comando de instalacion.
- Modelo no descargado y sin internet: indicar que se requiere descargarlo una vez.
- Modelo invalido: mostrar modelos aceptados.
- Falta de memoria: recomendar un modelo mas pequeno.
- Dispositivo CUDA no disponible: recomendar `--device cpu`.
- Microfono ausente: revisar dispositivo y permisos de Windows.
- Audio vacio: solicitar otra grabacion.
- Transcripcion vacia: informar y no tocar `prompt.md`.
- Archivo destino no escribible: mostrar la ruta y revisar permisos.
- Cancelacion con `Ctrl+C`: limpiar el archivo temporal y salir sin escribir texto parcial.

No se deben mostrar trazas completas por defecto. Un modo de depuracion futuro debe limitarse a informacion tecnica que no contenga credenciales ni el contenido completo del audio.

## 15. Pruebas previstas

### Pruebas unitarias

- Seleccion del proveedor local.
- Resolucion de modelo por defecto.
- Validacion de `device` y `compute_type`.
- Formateo de segmentos en texto.
- Manejo de segmentos vacios.
- Rechazo de transcripcion vacia.
- Escritura append-only compartida con el backend remoto.
- `--dry-run` sin cambios.
- Limpieza del audio temporal.

### Pruebas de integracion

- Carga de un modelo pequeno en CPU.
- Transcripcion de un WAV corto de prueba.
- Ejecucion sin conexion despues de descargar el modelo.
- Error controlado cuando el modelo no esta en cache y no hay red.
- Ejecucion desde un repositorio distinto al de la herramienta.

### Prueba manual inicial

1. Crear un entorno virtual.
2. Instalar las dependencias locales.
3. Ejecutar `speech-prompt --provider local --local-model tiny`.
4. Confirmar que la descarga inicial se informa claramente.
5. Grabar entre 5 y 10 segundos en espanol.
6. Revisar la transcripcion.
7. Ejecutar de nuevo sin conexion y confirmar que usa la cache.
8. Confirmar que `prompt.md` conserva entradas anteriores.
9. Verificar que no queda audio temporal.
10. Comprobar que no se necesita ni se solicita `OPENROUTER_API_KEY`.

## 16. Instalacion aislada recomendada

Para no contaminar el Python global:

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install sounddevice numpy faster-whisper
python -m pip install -e .
```

En Git Bash de Windows, la activacion puede requerir:

```bash
source .venv/Scripts/activate
```

La documentacion final debe incluir una alternativa para ejecutar el modulo sin activar el entorno si el usuario prefiere invocar directamente el Python del entorno virtual.

## 17. Comparacion con OpenRouter

| Criterio | Backend local | OpenRouter |
| --- | --- | --- |
| Requiere internet durante el uso | No | Si |
| Requiere API key | No | Si |
| Audio fuera del equipo | No | Si |
| Instalacion inicial | Pesada | Ligera |
| Descarga de modelos | Si | No |
| Coste por transcripcion | No | Si |
| Dependencia del hardware | Alta | Baja |
| Velocidad predecible | No | Depende de red y proveedor |
| Facilidad de puesta en marcha | Media o baja | Alta |
| Uso en equipos restringidos | Puede ser dificil | Requiere acceso de red |
| Calidad | Depende del modelo local | Depende del modelo remoto |
| Portabilidad inmediata | Menor | Mayor |

## 18. Criterios para elegir esta alternativa

Elegir el backend local si:

- La privacidad del audio es prioritaria.
- Se necesita trabajar sin conexion.
- La herramienta se usara con frecuencia suficiente para justificar la instalacion.
- El equipo tiene memoria, CPU o GPU adecuadas.
- Se acepta descargar y mantener modelos locales.
- Se quiere evitar el coste variable de una API.

Elegir OpenRouter si:

- Se busca la instalacion mas rapida.
- La calidad remota y la latencia de red son aceptables.
- El equipo es limitado.
- Se necesita minimizar dependencias binarias locales.
- Ya existe una clave configurada.

## 19. Estrategia recomendada

No crear una CLI separada para el backend local. Mantener una sola herramienta con proveedores intercambiables:

```bash
speech-prompt --provider openrouter
speech-prompt --provider local
```

Orden recomendado de implementacion:

1. Implementar captura y persistencia comunes.
2. Implementar OpenRouter para validar el flujo completo con menor riesgo de instalacion.
3. Agregar `local_whisper.py` como proveedor opcional.
4. Probar `tiny` y `small` en CPU con Python 3.13 y Windows.
5. Documentar una recomendacion segun hardware y privacidad.

No debe existir fallback automatico hacia OpenRouter si el usuario selecciono explicitamente `--provider local`; eso violaria la expectativa de privacidad. Un fallback futuro debera ser opt-in y visible.

## 20. Criterios de aceptacion

El backend local se considerara listo cuando:

- `speech-prompt --provider local --help` o la ayuda general documente sus opciones.
- Pueda cargar un modelo soportado en CPU.
- Pueda transcribir un WAV corto en espanol.
- Funcione sin API key.
- Funcione sin internet despues de descargar el modelo.
- No envie audio a ningun endpoint remoto durante la transcripcion.
- Escriba correctamente en `prompt.md` usando el formato comun.
- `--dry-run` no modifique archivos.
- El audio temporal se elimine al terminar o fallar.
- Los errores de instalacion, memoria y modelo sean accionables.
- La documentacion indique el tamanio y las implicaciones de la descarga sin prometer cifras fijas.

## 21. Riesgos

### Compatibilidad de Python y Windows

Las dependencias binarias pueden no disponer de wheels para todas las combinaciones de Python, arquitectura y sistema operativo. Esto debe verificarse antes de fijar Python 3.13 como requisito definitivo.

### Rendimiento insuficiente

`small`, `medium` o `large-v3` pueden resultar demasiado lentos en CPU. La CLI debe ofrecer `tiny` o `base` como opciones de diagnostico.

### Memoria insuficiente

Los modelos mayores pueden provocar errores o degradacion del sistema. No se debe seleccionar automaticamente un modelo grande.

### Calidad variable

Los errores en nombres propios y terminologia de programacion pueden persistir. Una fase posterior podria usar un diccionario local o una correccion opcional, pero nunca debe alterar silenciosamente el texto transcrito en la primera version.

### Licencias y distribucion

Antes de distribuir binarios o incluir modelos, se deben revisar las licencias de `faster-whisper`, CTranslate2, Whisper y los pesos descargados. La herramienta debe descargar modelos segun las condiciones de sus fuentes y no empaquetarlos sin una revision legal.

## 22. Decision base

El backend local se implementara como proveedor opcional de la CLI comun. La configuracion inicial sera CPU con `faster-whisper`, modelo `small`, idioma `es`, audio WAV temporal y escritura append-only en `prompt.md`.

La decision entre este plan y `IMPLEMENTATION_PLAN.md` debe basarse principalmente en privacidad, disponibilidad de internet, capacidad del equipo y tolerancia a una instalacion mas pesada.
