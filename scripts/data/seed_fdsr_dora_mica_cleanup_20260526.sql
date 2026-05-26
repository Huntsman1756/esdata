-- FDSR-DORA-MICA-CLEANUP-01
-- Remove weak duplicate EU norm rows after canonical CELEX rows exist.
--
-- Preconditions enforced:
-- - canonical norma.codigo values exist: 32022R2554 and 32023R1114
-- - weak duplicate rows have no dependent references in obligation/profile
--   tables checked by the MCP validation suite.
--
-- This script is intentionally narrow: it deletes only unreferenced weak
-- duplicate norma rows. It does not rewrite obligations, articles, or source
-- evidence.

DO $$
DECLARE
    v_references integer;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = '32022R2554') THEN
        RAISE EXCEPTION 'Canonical DORA norma 32022R2554 not found';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = '32023R1114') THEN
        RAISE EXCEPTION 'Canonical MiCA norma 32023R1114 not found';
    END IF;

    SELECT
        (
            SELECT COUNT(*)
            FROM obligacion_perfil
            WHERE norma_codigo IN ('DORA_2022_2535', 'MICA_2023_1114')
        )
        + (
            SELECT COUNT(*)
            FROM obligacion_fuente
            WHERE codigo_referencia IN ('DORA_2022_2535', 'MICA_2023_1114')
        )
        + (
            SELECT COUNT(*)
            FROM criterio_relacion
            WHERE norma_codigo IN ('DORA_2022_2535', 'MICA_2023_1114')
        )
    INTO v_references;

    IF v_references <> 0 THEN
        RAISE EXCEPTION 'Weak DORA/MiCA duplicates still have % dependent references', v_references;
    END IF;

    DELETE FROM norma
    WHERE codigo IN ('DORA_2022_2535', 'MICA_2023_1114');
END $$;
