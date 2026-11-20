# Gestión Institucional — Control Documental

Aplicación de escritorio para consultar correo de Microsoft 365, reservar folios,
capturar oficios y generar PDF. Las pantallas cambian dentro de una sola ventana.
Los documentos, folios y rutas de los PDF se guardan localmente en
`%LOCALAPPDATA%\GestionInstitucional\documentos.json`. Los PDF se guardan en
`%USERPROFILE%\Documents\GestionInstitucional\Oficios`.
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
   `POSTGRES_PASSWORD` y `POSTGRES_DB` en `.env` para que apunten a la misma
   base de datos PostgreSQL compartida por todos los empleados. Carga en esa
   base el esquema completo de la aplicación. Los folios se reservan allí
   usando un bloqueo transaccional y `correspondencia.folios_anuales`; no uses
   una base local independiente por empleado si necesitas folios globalmente
   únicos. La aplicación no crea tablas ni guarda las rutas de los PDF en
   PostgreSQL.

La carpeta de los PDF se crea automáticamente. Para usar otra ubicación,
establece `GESTION_INSTITUCIONAL_DOCUMENTS_DIR` en `.env`.
En la sección lateral **Enviada** puedes consultar y abrir los PDF guardados en
este equipo. El historial local no se comparte entre computadoras.

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
`MICROSOFT_AUTH_API` y, si usas las funciones administrativas conectadas a la
base, las variables de PostgreSQL. El `.env` del paquete contiene credenciales:
no lo publiques ni compartas. La caché de Microsoft y los documentos se guardan en
`%LOCALAPPDATA%\GestionInstitucional`.

La compilación debe hacerse en Windows para Windows. La carpeta de salida
no necesita crear tablas para guardar las rutas de PDF.

El registro del contenido del oficio y el historial de los PDF son locales. La
aplicación usa PostgreSQL únicamente en las funciones administrativas que
consultan `personalizacion.configuracion_folios`, `personalizacion.membrete`,
`correspondencia.oficios_envio` y `correspondencia.oficios_recibido`.
