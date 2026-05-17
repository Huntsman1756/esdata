-- Seed supervised entity profiles for the applicability engine.
-- Preconditions:
--   - Alembic revision 20260517_0079_profile_applicability_tables applied.
--   - LIVMC and LEY10_2010 loaded in norma.
-- Safe to rerun: all writes are idempotent UPSERTs.

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = 'LIVMC') THEN
        RAISE EXCEPTION 'Required norma LIVMC is not loaded';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = 'LEY10_2010') THEN
        RAISE EXCEPTION 'Required norma LEY10_2010 is not loaded';
    END IF;
END
$$;

INSERT INTO perfil_entidad (
    codigo,
    nombre,
    descripcion,
    supervisor,
    regimen_primario,
    activo,
    notas
) VALUES
(
    'sociedad_valores',
    'Sociedad de Valores',
    'Empresa de servicios de inversion habilitada para prestar servicios de inversion con el alcance previsto en la LIVMC.',
    'CNMV',
    'LIVMC',
    true,
    'Fuente de perfil: LIVMC arts. 143-149; sujeto obligado PBC/FT: LEY10_2010 art. 2.'
),
(
    'agencia_valores',
    'Agencia de Valores',
    'Empresa de servicios de inversion con limitaciones operativas frente a sociedad de valores, segun regimen LIVMC.',
    'CNMV',
    'LIVMC',
    true,
    'Fuente de perfil: LIVMC arts. 143-149; sujeto obligado PBC/FT: LEY10_2010 art. 2.'
),
(
    'sgiic',
    'Sociedad Gestora IIC',
    'Sociedad gestora de instituciones de inversion colectiva sometida a normativa IIC y supervision CNMV.',
    'CNMV',
    'RD_1082_2012',
    true,
    'Fuente de perfil: RD_1082_2012 y normativa IIC; sujeto obligado PBC/FT: LEY10_2010 art. 2.'
),
(
    'eaf',
    'Empresa Asesoramiento Financiero',
    'Empresa de asesoramiento financiero integrada en el perimetro de empresas de servicios de inversion.',
    'CNMV',
    'LIVMC',
    true,
    'Fuente de perfil: LIVMC arts. 143-149; sujeto obligado PBC/FT: LEY10_2010 art. 2.'
),
(
    'entidad_credito',
    'Entidad de Credito',
    'Entidad de credito supervisada principalmente por Banco de Espana con obligaciones transversales fiscales y PBC/FT.',
    'BDE',
    'multiple',
    true,
    'Fuente de perfil: normativa bancaria aplicable y sujeto obligado PBC/FT segun LEY10_2010 art. 2.'
),
(
    'empresa_servicios_pago',
    'Empresa Servicios Pago',
    'Entidad de servicios de pago con regimen propio y obligaciones transversales fiscales y PBC/FT.',
    'BDE',
    'multiple',
    true,
    'Fuente de perfil: normativa de servicios de pago y sujeto obligado PBC/FT segun LEY10_2010 art. 2.'
)
ON CONFLICT (codigo) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    supervisor = EXCLUDED.supervisor,
    regimen_primario = EXCLUDED.regimen_primario,
    activo = EXCLUDED.activo,
    notas = EXCLUDED.notas;

COMMIT;
