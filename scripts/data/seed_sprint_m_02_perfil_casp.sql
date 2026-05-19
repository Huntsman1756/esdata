-- M-02: Create perfil casp in perfil_entidad
-- CASP under MiCA arts. 3.1.16 and 59

INSERT INTO perfil_entidad (codigo, nombre, descripcion, supervisor, regimen_primario, activo)
VALUES (
  'casp',
  'Proveedor de Servicios de Criptoactivos (CASP)',
  'Entidad autorizada por la CNMV para prestar uno o m\u00e1s servicios de criptoactivos en Espa\u00f1a conforme al Reglamento MiCA (UE) 2023/1114 arts. 3.1.16 y 59. Incluye custodia, operaci\u00f3n de plataformas de intercambio, intercambio de criptoactivos a cambio de divisas o criptoactivos, ejecuci\u00f3n de \u00f3rdenes, colocaci\u00f3n, recepci\u00f3n y transmisi\u00f3n de \u00f3rdenes, asesoramiento y gesti\u00f3n de portafolios. MiCA es plenamente aplicable desde 30 diciembre 2024. El periodo transitorio para PSAV existentes en Espa\u00f1a finaliza 30 diciembre 2025.',
  'CNMV',
  'MiCA',
  true
)
ON CONFLICT (codigo) DO UPDATE SET
  nombre = EXCLUDED.nombre,
  descripcion = EXCLUDED.descripcion,
  supervisor = EXCLUDED.supervisor,
  regimen_primario = EXCLUDED.regimen_primario;
