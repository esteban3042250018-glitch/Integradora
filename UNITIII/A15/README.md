# A15 · Halcones_dev — Evidencias

Repositorio de evidencias de la actividad A15 del Proyecto Integrador I.

**Informe principal (PDF):** se entrega por separado en la plataforma académica. Este directorio contiene los archivos de respaldo, no una copia del informe.

## Archivos de evidencia

- [Matriz de ejecución de los 30 casos CP-A14](./Evidencias/matriz_ejecucion_CP_A14.csv)
- [Indicadores I1–I6](./Evidencias/indicadores_A15.csv)
- [Bitácora de defectos y brechas](./Evidencias/bitacora_defectos_A15.csv)
- [Pruebas complementarias A15](./Evidencias/test_a15_complementarias.py)
- [Resultado de la suite final: 103 pruebas y 6 subpruebas aprobadas con shims](./Evidencias/pytest_final.log)
- [Resultado de compilación](./Evidencias/compileall_final.log)
- [Barrido heurístico de seguridad](./Evidencias/security_static_scan.txt)
- [Parche de compatibilidad de autenticación](./Evidencias/applogin_A15.patch)

## Alcance y limitaciones

Las pruebas automatizadas utilizan dobles/stubs y no sustituyen pruebas de extremo a extremo con PostgreSQL, Microsoft Entra, SFTP o Windows real. Los indicadores I1, I2 e I4 no son calculables con la evidencia disponible; I3 e I6 son reportes provisionales y SUS corresponde a n=1. Los defectos DEF-A15-02 (almacenamiento de documentos archivados) y DEF-A15-03 (cambio de estado) permanecen abiertos.

Los documentos fuente A13-S1, A13-S2 y A13-S3, las capturas históricas completas y el paquete ZIP de código no se han subido en este commit porque la conexión GitHub disponible aquí solo permite crear/actualizar archivos de texto, no transferir archivos binarios. No se presentan como cargados. Deben agregarse manualmente a esta carpeta si se requiere conservar esos respaldos en GitHub.

