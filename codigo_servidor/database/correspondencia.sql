BEGIN;

CREATE SCHEMA IF NOT EXISTS correspondencia;

CREATE TABLE IF NOT EXISTS correspondencia.borradores (
    folio text PRIMARY KEY,
    usuario_id text NOT NULL,
    usuario_nombre text NOT NULL,
    asunto text NOT NULL DEFAULT '',
    area_emisora text NOT NULL DEFAULT '',
    recepcion text NOT NULL DEFAULT '',
    cuerpo text NOT NULL DEFAULT '',
    estado text NOT NULL DEFAULT 'Creado',
    actualizado_en timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE correspondencia.borradores
    ADD COLUMN IF NOT EXISTS folio text,
    ADD COLUMN IF NOT EXISTS usuario_id text,
    ADD COLUMN IF NOT EXISTS usuario_nombre text,
    ADD COLUMN IF NOT EXISTS asunto text NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS area_emisora text NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS recepcion text NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS cuerpo text NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS estado text NOT NULL DEFAULT 'Creado',
    ADD COLUMN IF NOT EXISTS actualizado_en timestamp with time zone
        NOT NULL DEFAULT CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS borradores_usuario_actualizado_idx
    ON correspondencia.borradores (usuario_id, actualizado_en DESC);

COMMIT;
