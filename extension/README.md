# Extensión Chrome

1. Abre `chrome://extensions`.
2. Activa **Modo de desarrollador**.
3. Pulsa **Cargar descomprimida** y selecciona esta carpeta `extension`.
4. Abre el popup desde el icono de la extensión.
5. En **Configuración**, pega tu clave de OpenRouter y guárdala.
6. Pulsa **Escuchar**, habla y pulsa **Detener**. El texto aparecerá en el textarea.

La extensión usa el mismo endpoint, modelo e idioma por defecto que la aplicación actual. Chrome entrega el audio en WebM; se envía directamente a OpenRouter sin descargar ningún modelo local.

## Atajo de teclado

El atajo predeterminado es `Ctrl+Shift+Y`. Puedes cambiarlo desde `chrome://extensions/shortcuts`.
