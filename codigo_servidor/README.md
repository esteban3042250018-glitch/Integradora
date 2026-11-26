# Gestión Institucional — Control Documental

Aplicación de escritorio para consultar correo de Microsoft 365, reservar folios,
capturar oficios y generar PDF. La navegación entre interfaces se mantiene dentro
de una sola ventana. La numeración, los borradores, estados y rutas de PDF se
guardan en PostgreSQL; la aplicación ya no usa `documentos.json` para operar.
Los archivos PDF y DOCX permanecen en almacenamiento local/SFTP y PostgreSQL
guarda la ruta remota de los PDF.
Los oficios se pueden redactar en Microsoft Word de escritorio o en **Word
Online**. La opción en línea crea el `.docx` en la carpeta
`GestionInstitucional` del OneDrive de la cuenta autenticada y lo abre en el
navegador; al sincronizar, descarga la versión guardada en OneDrive y respalda
su texto en la aplicación. La cuenta debe tener OneDrive aprovisionado, permiso
`Files.ReadWrite` consentido y acceso a Word para la Web. La sesión del navegador
es independiente de la sesión de la aplicación.
La opción de escritorio conserva el `.docx` en la carpeta local de los PDF e
incluye el membrete activo de `personalizacion.membrete`; Word Online conserva
una copia en el OneDrive del empleado. En ambos casos, guarda los cambios en el
editor elegido y pulsa **Sincronizar cambios** antes de guardar el oficio. Los
PDF se conservan localmente o en SFTP y no se guardan como binarios en PostgreSQL.
Los borradores se respaldan automáticamente en PostgreSQL y puedes retomarlos
con **Retomar borrador**. La campana muestra avisos cuando se genera un PDF;
al abrirla, los avisos se marcan como leídos para esa cuenta. Las rutas y PDF
son locales a este equipo; los avisos y borradores se comparten entre
instalaciones que usan la misma base de datos. El archivo `.docx` no se guarda
en PostgreSQL; el contenido que sí se puede recuperar allí es el último que la
aplicación guardó o sincronizó desde Word.
En **Configuración** puedes cambiar la plantilla del folio (incluidos sus
dígitos, fuente y tamaño), consultar el siguiente consecutivo y registrar un
reinicio sin borrar su historial. También puedes consultar, reemplazar o
desactivar el membrete activo; puedes arrastrar una imagen a la vista previa,
revisarla y confirmarla antes de aplicarla. El archivo de imagen original no
se modifica. Los bloques del formato de folio se separan automáticamente con
un guion; los separadores antiguos se normalizan al cargar el formato. Si
`tkinterdnd2` no está disponible, Configuración sigue abriendo y puedes usar
el botón para seleccionar la imagen; instala los requisitos y recompila el
ejecutable para habilitar arrastrar y soltar.

## Requisitos

- Python 3.10 o posterior.
- Las dependencias listadas en `requirements.txt`.
- Microsoft Word de escritorio instalado si se usará esa opción.
- Una aplicación de Microsoft Entra configurada como cliente público y con los
  permisos de Microsoft Graph que solicita el inicio de sesión.
- Para Word Online, una cuenta con OneDrive disponible y Word para la Web
  habilitado por Microsoft para esa cuenta/organización. La aplicación no
  incluye ni concede una licencia de Microsoft 365.

## Configuración

1. Instala las dependencias:

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. Verifica que `.env` contenga `MICROSOFT_AUTH_API` con el ID de cliente de la
   aplicación de Microsoft Entra. Si `.env` no existe, créalo a partir de
   `.env.example`.
3. Configura `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`,
   `POSTGRES_PASSWORD` y `POSTGRES_DB` en `.env`.
4. Apunta esas variables al host PostgreSQL compartido por los empleados. No
   uses `localhost` en las estaciones cliente. La base debe tener los esquemas
   `correspondencia` y `personalizacion` y las tablas del esquema completo.
   Configura TLS según el servidor; para verificar el certificado, usa
   `POSTGRES_SSLMODE=verify-full` y `POSTGRES_SSLROOTCERT`. Las reservas se
   coordinan en `personalizacion.configuracion_folios`; no configures una base
   independiente por empleado si necesitas folios globalmente únicos.
   La aplicación solo se conecta y consulta/modifica esa base; no ejecuta ni
   instala archivos SQL automáticamente.
5. Ejecuta una vez `database\correspondencia.sql` para crear o completar la
   tabla `correspondencia.borradores`, necesaria para reservar folios y
   recuperar borradores. La aplicación también necesita las tablas
   `correspondencia.oficios_envio` del esquema institucional.
6. Ejecuta una vez `database\notifications.sql` contra esa base para crear las
   tablas de avisos si aún no existen. `CVDR_MAILBOX_EMAIL` selecciona un buzón
   compartido y requiere el permiso delegado `Mail.ReadWrite.Shared`.
   Microsoft Entra debe permitir `Mail.ReadWrite`, que se usa para marcar un
   mensaje como leído al abrir sus detalles;
   `CVDR_MAX_MESSAGES` limita la consulta (300 por defecto, máximo 1000), y
   `CVDR_FOLIO_REGEX` permite adaptar la detección de folios. El dashboard
   muestra solo los mensajes cuyo asunto contiene un folio reconocido, y sus
   contadores reflejan la cantidad de resultados encontrados, no el límite
   máximo de consulta.
7. Ejecuta `database\personalizacion.sql` contra la base compartida para
   habilitar el historial de configuración de folios, agregar
   `personalizacion.configuracion_formato_folio.anio_folio`, asegurar que solo
   haya un membrete activo y registrar valores predeterminados si aún no
   existen. Ese campo es requerido por la lectura y guardado del año manual;
   si no aplicas la migración, PostgreSQL reportará que `anio_folio` no existe.
   El script modifica solo el esquema `personalizacion`; no altera
   `correspondencia`.
8. La ruta del PDF publicado se guarda en la columna existente
   `correspondencia.oficios_envio.ruta`; no se agrega una columna a
   `correspondencia.borradores`. Si necesitas importar rutas del historial
   local, ejecuta una vez desde la carpeta `codigo_servidor`:

   ```powershell
   python database\migrar_documentos_json.py
   ```

   La importación es idempotente, no borra el JSON y solo actualiza rutas de
   archivos PDF existentes cuyos folios ya estén en `oficios_envio`.
Al pulsar **Guardar documento**, la aplicación genera el PDF final, conserva
una copia local y lo transfiere por SFTP a `SFTP_REMOTE_DIR` en el servidor.
Configura `SFTP_HOST`, `SFTP_PORT`,
`SFTP_USER`, `SFTP_PASSWORD`, `SFTP_REMOTE_DIR` y
`SFTP_HOST_KEY_FINGERPRINT` en `.env`; la huella SHA256 o MD5 se valida antes de
autenticar. PostgreSQL guarda la ruta remota en el campo existente
`correspondencia.oficios_envio.ruta` para el mismo folio, sin cambiar la
estructura de la base ni mezclar el PDF con el registro del borrador. Al crear
un oficio nuevo se registran también sus catálogos predeterminados: prioridad
`Media`, tipo `Oficio` y estatus `Registrado`; si faltan, se insertan dentro de
la transacción. En la sección lateral **Enviada** puedes consultar y abrir los
PDF listados directamente desde la carpeta SFTP; al abrir uno, se descarga
desde el servidor a una caché local. La pantalla del folio también permite
regenerar el PDF.
El **Dashboard** institucional muestra los oficios activos, su área y su
estado vigente. Cada oficio muestra sus archivos disponibles y su historial;
los usuarios asignados a su área pueden cambiar el estado y adjuntar una
aprobación o un acuse. Esos adjuntos se guardan en la carpeta SFTP con el folio
en el nombre y quedan relacionados con el oficio en PostgreSQL. **Enviados**
muestra los oficios de las áreas asignadas al usuario.

**Áreas y usuarios** consulta y administra el catálogo activo de
`correspondencia.areas`; no mantiene nombres de áreas en el código. Los
usuarios asignados a un área con `puede_administrar = TRUE` pueden administrar
el catálogo y las asignaciones. El campo Área emisora, Dashboard y Enviados
usan las áreas activas de PostgreSQL, y los cambios de estado requieren que el
usuario esté asignado al área del oficio. La base
compartida debe incluir las tablas institucionales `areas`, `empleado`,
`area_empleado`, `oficios_area_emision`, `oficios_estatus`, `estatus_oficios`,
`aprobados` y `acuses`, además de la columna `areas.puede_administrar`
(`BOOLEAN NOT NULL DEFAULT FALSE`) y las tablas indicadas en Configuración.
Para habilitar administradores, activa ese permiso en las áreas
correspondientes y asigna usuarios activos a ellas.

Para probar la recuperación, inicia sesión, crea un documento y empieza a
capturar sus datos. La aplicación los respalda después de una pausa breve y
sincroniza el contenido de Word al pulsar **Sincronizar cambios**. Si se cierra
inesperadamente, vuelve a iniciar sesión con la misma cuenta en esta
computadora y pulsa **Retomar borrador**. Los cambios de Word que no se guardaron
con Ctrl+S y no se sincronizaron con la aplicación no pueden garantizarse.
Para probar Word Online, inicia sesión con una cuenta cuyo OneDrive y Word para
la Web estén habilitados, pulsa **Word Online**, inicia sesión en el navegador
si te lo solicita, guarda desde Word Online y luego pulsa **Sincronizar cambios**
en la aplicación.

## Formato de documentos de Word

Al sincronizar un archivo `.docx`, la aplicación conserva la estructura
semántica del contenido: párrafos y títulos, tablas, listas numeradas y con
viñetas, formato de texto, hipervínculos e imágenes rasterizadas. Al generar el
PDF, las tablas y listas se renderizan como elementos del documento, no como
texto plano. SmartArt, gráficos, cuadros de texto y otros objetos específicos
de Word pueden simplificarse; la posición de las imágenes en el PDF puede
diferir de la original.

Las notificaciones y borradores se comparten entre instalaciones que se conectan
al mismo servidor y base de datos PostgreSQL.

La primera autenticación crea una caché local de Microsoft en
`token_cache.bin`. No compartas ni agregues esa caché a Git.

## Ejecución

Abre la carpeta `codigo_servidor` en Visual Studio Code, selecciona el intérprete de
Python del proyecto e instala sus dependencias:

```powershell
python -m pip install -r requirements.txt
```

Después abre `main.py` y pulsa **F5** con la configuración
**Gestión Institucional (Python)**. También puedes ejecutarlo desde la terminal
integrada con `python main.py`. Esta carpeta contiene el código fuente y no
incluye el ejecutable compilado.

## Generar el ejecutable de Windows

La configuración para empaquetar la aplicación se conserva para cuando la
necesites. Desde PowerShell, en la carpeta `codigo_servidor`, ejecuta:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1
```

El proceso instala las dependencias y genera una versión de carpeta en
`dist\GestionInstitucional\`. Distribuye **toda esa carpeta**, no solo el `.exe`.
Antes del primer inicio, edita el `.env` generado junto al ejecutable y apunta
`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` y `POSTGRES_USER` al servidor.
Configura `POSTGRES_PASSWORD` y las opciones TLS de acuerdo con la política de
la organización. Configura también `MICROSOFT_AUTH_API`. No compartas el `.env`
ni contraseñas. La caché de Microsoft y los documentos se guardan en
`%LOCALAPPDATA%\GestionInstitucional`.

La compilación debe hacerse en Windows para Windows. El ejecutable no contiene ni
ejecuta scripts SQL; conéctalo a la base existente configurando el `.env`.

El contenido del oficio, estado y metadatos de PDF se guardan en PostgreSQL;
los archivos PDF/DOCX permanecen en almacenamiento local/SFTP. La aplicación
usa las tablas `correspondencia.borradores`,
`personalizacion.configuracion_folios`,
`personalizacion.configuracion_formato_folio`,
`correspondencia.notificaciones`,
`correspondencia.notificaciones_leidas` y los catálogos de membrete y folios
definidos en el esquema PostgreSQL completo. No requiere tablas `asuntos` ni
`oficios_documentos`.
