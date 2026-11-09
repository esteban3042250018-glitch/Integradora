CREATE SCHEMA IF NOT EXISTS correspondencia;

CREATE TABLE IF NOT EXISTS correspondencia.oficios_documentos (
    folio TEXT PRIMARY KEY,
    ruta_archivo TEXT NOT NULL,
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
