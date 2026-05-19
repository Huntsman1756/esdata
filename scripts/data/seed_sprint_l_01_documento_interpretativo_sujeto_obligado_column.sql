-- Sprint L L-01: schema support for CNMV applicability.
--
-- sujeto_obligado is stored as a queryable text[] column because CNMV
-- applicability is multi-profile and used by endpoint filters.

ALTER TABLE documento_interpretativo
ADD COLUMN IF NOT EXISTS sujeto_obligado text[];
