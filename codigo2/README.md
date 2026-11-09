# Gestión Institucional — Control Documental

Aplicación de escritorio para consultar correo de Microsoft 365, reservar folios,
capturar oficios y generar PDF. Las pantallas cambian dentro de una sola ventana.
Los documentos y folios se guardan localmente en
`%LOCALAPPDATA%\GestionInstitucional\documentos.json`. Los PDF se guardan en
`%USERPROFILE%\Documents\GestionInstitucional\Oficios`, se copian al servidor
Ubuntu mediante SFTP y su ruta remota se registra en PostgreSQL.
Los oficios se redactan en Microsoft Word de escritorio; los archivos `.docx`
se guardan en la misma carpeta local de los PDF. Guarda el documento en Word y
usa **Sincronizar cambios** para traer su texto a la aplicación antes de guardar
el oficio.

## Requisitos

- Python 3.10 o posterior.
- Las dependencias listadas en `requirements.txt`.
- Microsoft Word de escritorio instalado.
- Una aplicación de Microsoft Entra configurada como cliente público y con los
  permisos de Microsoft Graph que solicita el inicio de sesión.

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
4. Configura `SFTP_HOST`, `SFTP_PORT`, `SFTP_USER`, `SFTP_PASSWORD`,
   `SFTP_REMOTE_DIR` y `SFTP_HOST_KEY_FINGERPRINT`. Esta versión requiere la
   clave de host Ed25519 del servidor. Verifica su huella directamente en la
   consola de Ubuntu:

   ```bash
   sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256
   ```

   Copia el valor `SHA256:...` a `SFTP_HOST_KEY_FINGERPRINT`. No uses una huella
   obtenida de una conexión no verificada. La aplicación negocia `ssh-ed25519`,
   exige una clave de host Ed25519 y compara su huella SHA-256 antes de
   autenticar. La carpeta remota debe existir y el usuario SFTP debe tener
   permiso de escritura. Si la carpeta pertenece a `root` y tiene permisos
   `755`, puedes habilitar la escritura sin abrir permisos a todos:

   ```bash
   sudo chown vboxuser:www-data /var/www/integradora_proyect/oficios
   sudo chmod 775 /var/www/integradora_proyect/oficios
   ```

   Sustituye `vboxuser` y la carpeta si tu `.env` usa otros valores.
5. Crea la tabla de registro ejecutando el archivo
   `database/crear_tabla_documentos.sql` en la base de datos configurada. Por
   ejemplo, desde PowerShell con PostgreSQL instalado:

   ```powershell
   psql -h localhost -U postgres -d postgres -f .\database\crear_tabla_documentos.sql
   ```

   Ajusta host, usuario y base de datos para que coincidan con tu `.env`.
   En la VM, PostgreSQL también debe escuchar conexiones de red y permitir el
   acceso del equipo Windows en `postgresql.conf`, `pg_hba.conf` y el firewall.

La carpeta de los PDF se crea automáticamente. Para usar otra ubicación,
establece `GESTION_INSTITUCIONAL_DOCUMENTS_DIR` en `.env`.
En la sección lateral **Enviada** puedes consultar los PDF registrados en
PostgreSQL y abrirlos; la aplicación los descarga desde SFTP a una carpeta
temporal local antes de abrirlos.

La primera autenticación crea una caché local de Microsoft en
`token_cache.bin`. No compartas ni agregues esa caché a Git.

## Ejecución

Desde esta carpeta:

```powershell
python main.py
```

## Generar el ejecutable de Windows

Desde PowerShell, en la carpeta `codigo2`, ejecuta:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1
```

El proceso instala las dependencias y genera una versión de carpeta en
`dist\GestionInstitucional\`. Distribuye **toda esa carpeta**, no solo el `.exe`.
Antes del primer inicio, edita el `.env` junto al ejecutable y configura
`MICROSOFT_AUTH_API`, las variables de PostgreSQL y SFTP, incluida la huella
SSH verificada. El `.env` del paquete contiene credenciales: no lo publiques ni
compartas. La caché de Microsoft y los documentos se guardan en
`%LOCALAPPDATA%\GestionInstitucional`.

La compilación debe hacerse en Windows para Windows. La carpeta de salida
incluye el SQL para preparar la tabla de rutas.

El registro del contenido del oficio continúa siendo local; la ruta del PDF se
guarda además en `correspondencia.oficios_documentos`, asociada al folio. Si la
carga SFTP falla, la aplicación conserva el PDF local y muestra el error; si
falla el registro de PostgreSQL, informa que el archivo ya fue subido.
