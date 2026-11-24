# Integración del proyecto Gestión Institucional

## Base y diseño
- Se conserva esta carpeta como proyecto funcional base: arquitectura `controller/`, `model/` y `views/`.
- Se incorporan los recursos visuales del proyecto de referencia (`cvdr.jpg`, `icon_app.ico`, `icon_app.png`) sin sustituir los módulos que contienen la integración con PostgreSQL, Microsoft Graph y la generación de documentos.
- Se mantiene el diseño de las pantallas funcionales y sus controles conectados a los datos reales.

## Fuentes
- El selector de fuentes obtiene las familias instaladas en Windows y las fuentes disponibles en los directorios de fuentes de Microsoft Office.
- La generación DOCX aplica la fuente y el tamaño configurados al estilo normal y al texto insertado.
- La generación PDF registra e incrusta el archivo de fuente TrueType/OpenType compatible cuando está disponible y aplica la configuración al cuerpo y al folio.
- Si una fuente no tiene un archivo compatible para incrustar en PDF, se utiliza una fuente PDF estándar como respaldo.

## Almacenamiento
Los archivos se guardan en `Documentos/GestionInstitucional/` (o en la ruta definida por `GESTION_INSTITUCIONAL_DOCUMENTS_DIR`):

- `creado/`: estado Creado.
- `revisado/`: estados Enviado y Aprobado.
- `acusado/`: estado Acusado.

Al cambiar el estado, los archivos asociados al folio se trasladan a la carpeta correspondiente y se actualizan las rutas registradas en PostgreSQL y en el historial local. En el primer acceso a la bandeja se intenta migrar la estructura anterior `Oficios/<folio>/` a las nuevas carpetas.

## Nota
Las credenciales y la conexión de PostgreSQL continúan dependiendo de la configuración local del archivo `.env`. No compartas ese archivo públicamente.
