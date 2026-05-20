-- N-01: Create perfil emisor_token in perfil_entidad
-- Single profile covering MiCA Title III ART issuers and Title IV EMT issuers.

INSERT INTO perfil_entidad (codigo, nombre, descripcion, supervisor, regimen_primario, activo)
VALUES (
  'emisor_token',
  'Emisor de Criptoactivos (ART/EMT)',
  'Persona juridica que emite fichas referenciadas a activos (ART, Title III MiCA) o fichas de dinero electronico (EMT, Title IV MiCA). ART: autorizacion CNMV requerida antes de la emision, salvo regimen simplificado para entidades de credito. EMT: solo entidades de credito o entidades de dinero electronico, con contexto supervisor BdE. MiCA arts. 16-58. Aplicable desde 30 diciembre 2024.',
  'CNMV',
  'MiCA',
  true
)
ON CONFLICT (codigo) DO UPDATE SET
  nombre = EXCLUDED.nombre,
  descripcion = EXCLUDED.descripcion,
  supervisor = EXCLUDED.supervisor,
  regimen_primario = EXCLUDED.regimen_primario,
  activo = EXCLUDED.activo;
