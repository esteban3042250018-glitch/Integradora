# Gestión Institucional — Control Documental

Aplicación de escritorio para consultar correo de Microsoft 365, reservar folios,
capturar oficios y generar PDF. La navegación entre interfaces se mantiene dentro
de una sola ventana. Los documentos y folios se guardan localmente en
`%LOCALAPPDATA%\GestionInstitucional\documentos.json`; las reservas y copias
recuperables de borradores también se guardan en PostgreSQL. Los PDF se
guardan en `%USERPROFILE%\Documents\GestionInstitucional\Oficios`; la ruta del
PDF local se registra en la base de datos PostgreSQL configurada.
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
editor elegido y pulsa **Sincronizar cambios** antes de guardar el oficio. El
PDF sigue el flujo local/servidor indicado por esta versión y no se guarda en
OneDrive.
Los borradores se respaldan automáticamente en PostgreSQL y puedes retomarlos
con **Retomar borrador**. La campana muestra avisos cuando se registra un PDF;
al abrirla, los avisos se marcan como leídos para esa cuenta. En esta versión de
prueba, los PDFs y avisos solo son visibles desde las instalaciones que usan la
misma base de datos. El archivo `.docx` no se guarda en PostgreSQL; el contenido
que sí se puede recuperar allí es el último que la aplicación guardó o sincronizó
desde Word.

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
4. Apunta esas variables a la base PostgreSQL local de pruebas, que debe tener
   previamente el esquema `correspondencia` requerido por la aplicación. La
   aplicación solo se conecta y consulta/modifica esa base; no ejecuta ni instala
   archivos SQL. Cada tester se conecta al PostgreSQL de su propia computadora
   mediante `127.0.0.1`, por lo que las bases locales no comparten sus datos.
La carpeta de los PDF se crea automáticamente. Para usar otra ubicación,
establece `GESTION_INSTITUCIONAL_DOCUMENTS_DIR` en `.env`.
En la sección lateral **Enviada** puedes consultar los PDF registrados en
PostgreSQL y abrirlos desde la ruta local guardada en la base de datos.

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
Las notificaciones y borradores se comparten entre instalaciones que se conectan
al mismo servidor y base de datos PostgreSQL.

La primera autenticación crea una caché local de Microsoft en
`token_cache.bin`. No compartas ni agregues esa caché a Git.

## Ejecución

Abre la carpeta `codigo3` en Visual Studio Code, selecciona el intérprete de
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
necesites. Desde PowerShell, en la carpeta `codigo3`, ejecuta:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1
```

El proceso instala las dependencias y genera una versión de carpeta en
`dist\GestionInstitucional\`. Distribuye **toda esa carpeta**, no solo el `.exe`.
Antes del primer inicio, edita el `.env` generado junto al ejecutable y configura
`POSTGRES_PASSWORD` con la clave del PostgreSQL local de pruebas. El paquete usa
`127.0.0.1`; `POSTGRES_PORT`, `POSTGRES_USER` y `POSTGRES_DB` deben coincidir con
la instancia local del tester. Configura también `MICROSOFT_AUTH_API` si no está
preparado en el paquete. No compartas contraseñas en el `.env`. La caché de Microsoft y los documentos se guardan en
`%LOCALAPPDATA%\GestionInstitucional`.

La compilación debe hacerse en Windows para Windows. El ejecutable no contiene ni
ejecuta scripts SQL; conéctalo a la base existente configurando el `.env`.

El registro del contenido del oficio continúa siendo local; la ruta del PDF se
guarda además en `correspondencia.oficios_documentos`, asociada al folio. Esta
versión no sube archivos a servidores remotos.
