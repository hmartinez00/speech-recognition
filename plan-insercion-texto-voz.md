# Plan de implementación: inserción de texto por voz en campos web

## Objetivo

Agregar a la extensión del navegador la posibilidad de insertar directamente el texto reconocido por voz en el campo editable que tenga el foco, sin modificar la funcionalidad existente de reconocimiento, visualización o copia del texto.

## Flujo propuesto

```text
Reconocimiento de voz
        ↓
Popup o background
        ↓
Content script de la pestaña activa
        ↓
Elemento editable con foco
        ↓
Inserción en la posición del cursor
```

## Alcance funcional

La extensión deberá detectar y admitir los siguientes elementos editables:

- `<input type="text">`
- `<input type="search">`
- `<input type="email">`
- `<input type="url">`
- Otros tipos de input que permitan escritura libre, según la compatibilidad requerida.
- `<textarea>`
- Elementos con `contenteditable="true"`.

No se deberán modificar elementos que estén deshabilitados, sean de solo lectura o no sean editables.

## Plan de implementación

### 1. Detectar el elemento activo

Implementar la detección mediante `document.activeElement` dentro del `content script`.

El elemento deberá validarse para confirmar que es un campo de texto editable y que pertenece a la página activa.

También se deberá contemplar el último campo editable enfocado, ya que el foco puede desplazarse temporalmente hacia la interfaz de la extensión durante el dictado.

### 2. Validar la editabilidad

Ignorar elementos que cumplan cualquiera de estas condiciones:

- `disabled`.
- `readonly`.
- No sean visibles o no estén disponibles para interacción.
- No permitan ingreso de texto libre.

### 3. Insertar texto en la posición del cursor

Para elementos `<input>` y `<textarea>`:

- Obtener `selectionStart` y `selectionEnd`.
- Reemplazar el texto seleccionado, si existe.
- Insertar el texto reconocido en la posición actual del cursor.
- Restaurar la posición del cursor después de la inserción.

Para elementos `contenteditable`:

- Obtener la selección activa mediante la API `Selection`.
- Utilizar `Range` para insertar o reemplazar el contenido.
- Restaurar la selección cuando sea necesario.

### 4. Mantener sincronizado el estado de los formularios

Después de actualizar un campo, disparar los eventos correspondientes, como:

- `input`.
- `change`, cuando corresponda.

Esto permitirá que la inserción funcione correctamente en formularios tradicionales y en aplicaciones construidas con React, Vue, Angular u otros frameworks.

### 5. Conectar el reconocimiento de voz con el content script

Cuando se obtenga un resultado de reconocimiento de voz:

1. El popup o el background enviará un mensaje al `content script`.
2. El `content script` localizará el elemento editable activo o el último elemento editable enfocado.
3. El texto será insertado en la posición del cursor.
4. La funcionalidad actual de reconocimiento y presentación del texto continuará disponible.

### 6. Gestionar el foco durante el dictado

Guardar una referencia lógica al último elemento editable activo, evitando depender exclusivamente de `document.activeElement` después de abrir el popup o iniciar el reconocimiento.

La referencia deberá invalidarse si el elemento deja de existir, deja de ser editable o pertenece a un contexto no accesible.

### 7. Revisar permisos y limitaciones del navegador

Verificar la configuración de `manifest.json`, incluyendo:

- `content_scripts`.
- Permisos necesarios para acceder a las páginas autorizadas.
- Compatibilidad con la pestaña activa.

Documentar las páginas donde los content scripts no pueden ejecutarse, por ejemplo:

- `chrome://` y otras páginas internas del navegador.
- Tiendas de extensiones.
- Algunas páginas protegidas o documentos PDF, según el navegador.

### 8. Preservar la funcionalidad existente

La nueva lógica deberá ser adicional y no reemplazar el comportamiento actual. El texto reconocido deberá continuar pudiendo:

- Mostrarse en la interfaz existente.
- Copiarse al portapapeles, si esa funcionalidad ya existe.
- Utilizarse mediante el flujo anterior de la extensión.

La inserción directa será una capacidad complementaria.

## Pruebas previstas

Probar como mínimo los siguientes escenarios:

- Input de texto vacío.
- Input con texto existente y cursor en el medio.
- Input con una selección activa que deba reemplazarse.
- Textarea.
- Campos de email, búsqueda y URL.
- Elemento `contenteditable`.
- Campo `readonly` o `disabled`.
- Página sin ningún campo editable enfocado.
- Formularios administrados por React, Vue o Angular.
- Cambio de foco mientras el reconocimiento está activo.
- Pestañas o páginas donde el content script no tenga acceso.
- Confirmación de que el comportamiento anterior continúa funcionando.

## Resultado esperado

Al dictar texto con un campo editable enfocado en la pestaña activa, el texto reconocido deberá aparecer automáticamente en dicho campo, exactamente en la posición del cursor o reemplazando la selección actual, sin romper las capacidades existentes de la extensión.
