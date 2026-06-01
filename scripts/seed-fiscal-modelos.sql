-- LEGACY / NO AUTORITATIVO
--
-- Snapshot SQL historico. No usar como flujo canonico productivo AEAT.
-- La via canonica del repo MCP es:
-- 1. python scripts/seed-modelos.py --db-url <DATABASE_URL>
-- 2. python scripts/seed-modelos-v2.py --db-url <DATABASE_URL> --campana <YEAR>
-- ============================================================
-- Fase 39: Seed datos fiscales
-- Campana: 2025
-- ============================================================

-- 1. aeat_modelo
INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info) VALUES
  ('100', 'IRPF — Declaración anual', 'Anual', 'IRPF', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml'),
  ('200', 'IRPF — Empresas', 'Anual', 'IRPF', NULL),
  ('111', 'IRPF — Retenciones del trabajo', 'Trimestral', 'IRPF retenciones', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-111/instrucciones/index.shtml'),
  ('115', 'IRPF — Retenciones arrendamientos', 'Trimestral', 'IRPF arrendamientos', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-115/instrucciones/index.shtml'),
  ('123', 'IRPF — Retenciones rentas sujetas', 'Trimestral', 'IRPF retenciones', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-123.html'),
  ('130', 'IRPF — Pago fraccionado', 'Trimestral', 'IRPF fraccionado', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-130/instrucciones/index.shtml'),
  ('180', 'IRPF — Resumen anual arrendamientos', 'Anual', 'IRPF arrendamientos', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-180.html'),
  ('187', 'IRPF — Acciones y participaciones IIC', 'Anual', 'IRPF participaciones', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-187.html'),
  ('189', 'IRPF — Certificaciones individuales', 'Anual', 'IRPF certificaciones', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-189.html'),
  ('190', 'IRPF — Resumen anual retenciones', 'Anual', 'IRPF retenciones', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-190.html'),
  ('193', 'IRPF — Retenciones capital mobiliario', 'Trimestral', 'IRPF capital mobiliario', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-193.html'),
  ('194', 'IRPF — Operaciones vinculadas', 'Anual', 'IRPF vinculadas', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-194.html'),
  ('196', 'IRPF — Resumen capital mobiliario', 'Anual', 'IRPF capital mobiliario', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-196.html'),
  ('198', 'IRPF — Operaciones con activos financieros', 'Anual', 'IRPF activos financieros', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-198.html'),
  ('110', 'IRPF — Sustitutivo 111', 'Trimestral', 'IRPF retenciones', NULL),
  ('303', 'IVA — Autoliquidación trimestral', 'Trimestral', 'IVA', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/instrucciones/index.shtml'),
  ('349', 'IVA — Operaciones intracomunitarias', 'Mensual/Trimestral', 'IVA intracomunitarias', 'https://sede.agenciatributaria.gob.es/Sede/iva/iva-operaciones-comercio-exterior/identificacion-realizar-operaciones-otros-empresarios-ue/modelo-349.html'),
  ('390', 'IVA — Resumen anual', 'Anual', 'IVA resumen', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-390/instrucciones/index.shtml'),
  ('124', 'IRNR — Retenciones sin EP', 'Mensual', 'IRNR sin EP', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-124.html'),
  ('216', 'IRNR — Retenciones sin EP mensual', 'Mensual', 'IRNR sin EP', 'https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelos-declaraciones-retenciones.html'),
  ('296', 'IRNR — Resumen anual retenciones', 'Anual', 'IRNR sin EP', 'https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelo-296-declaracion-informativa-resumen-anual_.html'),
  ('036', 'Censal — Alta/modificación/baja', 'Eventual', 'Censo', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/guia-practica-cumplimentacion-modelo-censal-036/index.shtml'),
  ('289', 'DAC2/CRS — Cuentas financieras', 'Trimestral', 'DAC2/CRS', 'https://sede.agenciatributaria.gob.es/Sede/declaraciones-informativas-otros-impuestos-tasas/campana-declaraciones-informativas-2024/modelo-declaraciones-informativas-2024.html'),
  ('290', 'FATCA — Cuentas financieras EEUU', 'Anual', 'FATCA', 'https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-290-decla_____s-determinadas-personas-fatca_/index.shtml'),
  ('299', 'Informativo — Otros impuestos', 'Anual', 'Informativo', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro.html'),
  ('347', 'Operaciones con terceros', 'Anual', 'Informativo terceros', 'https://sede.agenciatributaria.gob.es/Sede/declaraciones-informativas-otros-impuestos-tasas/modelo-347-declaracion-anual-operaciones-terceras-personas/index.shtml');

-- 2. modelo_campana
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml', 'https://www.boe.es/boe/dias/2024/12/20/pdfs/BOE-A-2024-26789.pdf', NULL, true
FROM aeat_modelo m WHERE m.codigo = '100';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-111/instrucciones/index.shtml', 'https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948', NULL, true
FROM aeat_modelo m WHERE m.codigo = '111';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-115/instrucciones/index.shtml', 'https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948', NULL, true
FROM aeat_modelo m WHERE m.codigo = '115';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-123.html', 'https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948', NULL, true
FROM aeat_modelo m WHERE m.codigo = '123';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-130/instrucciones/index.shtml', 'https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948', NULL, true
FROM aeat_modelo m WHERE m.codigo = '130';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-180.html', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', NULL, true
FROM aeat_modelo m WHERE m.codigo = '180';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-187.html', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', NULL, true
FROM aeat_modelo m WHERE m.codigo = '187';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-189.html', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', NULL, true
FROM aeat_modelo m WHERE m.codigo = '189';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-190.html', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', NULL, true
FROM aeat_modelo m WHERE m.codigo = '190';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-193.html', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', NULL, true
FROM aeat_modelo m WHERE m.codigo = '193';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-194.html', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', NULL, true
FROM aeat_modelo m WHERE m.codigo = '194';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-196.html', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', NULL, true
FROM aeat_modelo m WHERE m.codigo = '196';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-198.html', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', NULL, true
FROM aeat_modelo m WHERE m.codigo = '198';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', NULL, 'https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948', NULL, true
FROM aeat_modelo m WHERE m.codigo = '110';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/instrucciones/index.shtml', 'https://www.boe.es/buscar/act.php?id=BOE-A-2024-16738', NULL, true
FROM aeat_modelo m WHERE m.codigo = '303';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/iva/iva-operaciones-comercio-exterior/identificacion-realizar-operaciones-otros-empresarios-ue/modelo-349.html', 'https://www.boe.es/buscar/act.php?id=BOE-A-2024-16738', NULL, true
FROM aeat_modelo m WHERE m.codigo = '349';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-390/instrucciones/index.shtml', 'https://www.boe.es/buscar/act.php?id=BOE-A-2024-16738', NULL, true
FROM aeat_modelo m WHERE m.codigo = '390';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-124.html', 'https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886', NULL, true
FROM aeat_modelo m WHERE m.codigo = '124';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelos-declaraciones-retenciones.html', 'https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886', NULL, true
FROM aeat_modelo m WHERE m.codigo = '216';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelo-296-declaracion-informativa-resumen-anual_.html', 'https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886', NULL, true
FROM aeat_modelo m WHERE m.codigo = '296';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/guia-practica-cumplimentacion-modelo-censal-036/index.shtml', 'https://www.boe.es/buscar/act.php?id=BOE-A-2024-25303', NULL, true
FROM aeat_modelo m WHERE m.codigo = '036';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/declaraciones-informativas-otros-impuestos-tasas/campana-declaraciones-informativas-2025/normativa/modelo-289.html', 'https://www.boe.es/buscar/act.php?id=BOE-A-2024-24098', NULL, true
FROM aeat_modelo m WHERE m.codigo = '289';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-290-decla_____s-determinadas-personas-fatca_/index.shtml', 'https://www.boe.es/buscar/act.php?id=BOE-A-2014-6922', NULL, true
FROM aeat_modelo m WHERE m.codigo = '290';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', NULL, NULL, 'https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro.html', true
FROM aeat_modelo m WHERE m.codigo = '299';
INSERT INTO modelo_campana (modelo_id, campana, url_instrucciones, url_normativa, url_formato, activo)
SELECT m.id, '2025', 'https://sede.agenciatributaria.gob.es/Sede/declaraciones-informativas-otros-impuestos-tasas/modelo-347-declaracion-anual-operaciones-terceras-personas/index.shtml', 'https://www.boe.es/buscar/act.php?id=BOE-A-2024-25303', NULL, true
FROM aeat_modelo m WHERE m.codigo = '347';

-- 3. modelo_normativa
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-26789', 'Orden HAC/1234/2024 — IRPF modelo 100', '2024-12-20', 'https://www.boe.es/boe/dias/2024/12/20/pdfs/BOE-A-2024-26789.pdf', 'Aprueba el modelo 100 de declaración del IRPF y sus instrucciones'
FROM aeat_modelo am WHERE am.codigo = '100';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2011-4948', 'Orden EHA/586/2011 — Modelo 110 (sustituido por 111)', '2011-03-09', 'https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948', 'Aprueba modelos de declaración de retenciones del IRPF'
FROM aeat_modelo am WHERE am.codigo = '111';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2011-4948', 'Orden EHA/586/2011 — Modelo 115', '2011-03-09', 'https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948', 'Aprueba modelo 115 de retenciones por arrendamientos'
FROM aeat_modelo am WHERE am.codigo = '115';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2011-4948', 'Orden EHA/586/2011 — Modelo 123', '2011-03-09', 'https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948', 'Aprueba modelo 123 de retenciones rentas sujetas a retención'
FROM aeat_modelo am WHERE am.codigo = '123';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2011-4948', 'Orden EHA/586/2011 — Modelo 130', '2011-03-09', 'https://www.boe.es/buscar/act.php?id=BOE-A-2011-4948', 'Aprueba modelo 130 de pago fraccionado IRPF'
FROM aeat_modelo am WHERE am.codigo = '130';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-23244', 'Orden HAC/1100/2024 — Modelo 180', '2024-11-15', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', 'Aprueba modelo 180 resumen anual retenciones arrendamientos'
FROM aeat_modelo am WHERE am.codigo = '180';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-23244', 'Orden HAC/1100/2024 — Modelo 187', '2024-11-15', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', 'Aprueba modelo 187 acciones y participaciones IIC'
FROM aeat_modelo am WHERE am.codigo = '187';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-23244', 'Orden HAC/1100/2024 — Modelo 189', '2024-11-15', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', 'Aprueba modelo 189 certificaciones individuales'
FROM aeat_modelo am WHERE am.codigo = '189';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-23244', 'Orden HAC/1100/2024 — Modelo 190', '2024-11-15', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', 'Aprueba modelo 190 resumen anual retenciones'
FROM aeat_modelo am WHERE am.codigo = '190';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-23244', 'Orden HAC/1100/2024 — Modelo 193', '2024-11-15', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', 'Aprueba modelo 193 retenciones capital mobiliario'
FROM aeat_modelo am WHERE am.codigo = '193';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-23244', 'Orden HAC/1100/2024 — Modelo 194', '2024-11-15', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', 'Aprueba modelo 194 operaciones vinculadas y paraísos fiscales'
FROM aeat_modelo am WHERE am.codigo = '194';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-23244', 'Orden HAC/1100/2024 — Modelo 196', '2024-11-15', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', 'Aprueba modelo 196 resumen anual capital mobiliario'
FROM aeat_modelo am WHERE am.codigo = '196';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-23244', 'Orden HAC/1100/2024 — Modelo 198', '2024-11-15', 'https://www.boe.es/boe/dias/2024/11/15/pdfs/BOE-A-2024-23244.pdf', 'Aprueba modelo 198 operaciones con activos financieros'
FROM aeat_modelo am WHERE am.codigo = '198';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-16738', 'Orden HAC/891/2024 — Modelo 303', '2024-09-10', 'https://www.boe.es/buscar/act.php?id=BOE-A-2024-16738', 'Aprueba modelo 303 de autoliquidación IVA'
FROM aeat_modelo am WHERE am.codigo = '303';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-25303', 'Orden HAC/1187/2024 — Modelo 347', '2024-12-02', 'https://www.boe.es/buscar/act.php?id=BOE-A-2024-25303', 'Aprueba modelo 347 operaciones con terceros'
FROM aeat_modelo am WHERE am.codigo = '347';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-16738', 'Orden HAC/891/2024 — Modelo 349', '2024-09-10', 'https://www.boe.es/buscar/act.php?id=BOE-A-2024-16738', 'Aprueba modelo 349 operaciones intracomunitarias'
FROM aeat_modelo am WHERE am.codigo = '349';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-16738', 'Orden HAC/891/2024 — Modelo 390', '2024-09-10', 'https://www.boe.es/buscar/act.php?id=BOE-A-2024-16738', 'Aprueba modelo 390 resumen anual IVA'
FROM aeat_modelo am WHERE am.codigo = '390';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-25303', 'Orden HAC/1187/2024 — Modelo 036', '2024-12-02', 'https://www.boe.es/buscar/act.php?id=BOE-A-2024-25303', 'Aprueba modelo 036 declaración censal'
FROM aeat_modelo am WHERE am.codigo = '036';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2004-19886', 'RDL 5/2004 — IRNR', '2004-12-03', 'https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886', 'Texto refundido de la Ley del IRNR'
FROM aeat_modelo am WHERE am.codigo = '124';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2004-19886', 'RDL 5/2004 — IRNR', '2004-12-03', 'https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886', 'Texto refundido de la Ley del IRNR'
FROM aeat_modelo am WHERE am.codigo = '216';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2004-19886', 'RDL 5/2004 — IRNR', '2004-12-03', 'https://www.boe.es/buscar/act.php?id=BOE-A-2004-19886', 'Texto refundido de la Ley del IRNR'
FROM aeat_modelo am WHERE am.codigo = '296';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2024-24098', 'Orden HAC/1150/2024 — Modelo 289', '2024-11-20', 'https://www.boe.es/buscar/act.php?id=BOE-A-2024-24098', 'Aprueba modelo 289 cuentas financieras DAC2/CRS'
FROM aeat_modelo am WHERE am.codigo = '289';
INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
SELECT am.id, 'BOE-A-2014-6854', 'Acuerdo FATCA España-EEUU', '2014-07-01', 'https://www.boe.es/buscar/act.php?id=BOE-A-2014-6854', 'Acuerdo FATCA España-EE.UU.; Orden HAP/1136/2014 aprueba Modelo 290'
FROM aeat_modelo am WHERE am.codigo = '290';

-- 4. modelo_casilla
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0001', 'Nombre y apellidos', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0002', 'Rendimientos del trabajo — ingresos íntegros', 'Suma de todos los rendimientos del trabajo devengados en el ejercicio', 'importe', 2, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0003', 'Rendimientos de actividades económicas', 'Ingresos íntegros de actividades económicas en estimación directa', 'importe', 2, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0004', 'Rendimientos del capital mobiliario', 'Dividendos, intereses, rendimientos de seguros', 'importe', 3, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0005', 'Rendimientos del capital inmobiliario', 'Rendimientos procedentes del arrendamiento de inmuebles', 'importe', 3, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0006', 'Rendimientos del capital mobiliario obtenidos en Ceuta y Melilla', NULL, 'importe', 3, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0007', 'Rendimientos del capital inmobiliario obtenidos en Ceuta y Melilla', NULL, 'importe', 3, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0008', 'Subtot. rendimientos', 'Suma de rendimientos parciales', 'importe', 3, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0009', 'Reducciones por rendimientos', 'Reducciones aplicables sobre los rendimientos', 'importe', 3, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0010', 'Rendimiento neto', 'Rendimiento neto tras reducciones', 'importe', 4, 10
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0015', 'Ganancias patrimoniales derivadas de transmisiones', 'Plusvalías por venta de inmuebles, acciones, etc.', 'importe', 5, 15
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0016', 'Ganancias patrimoniales no derivadas de transmisiones', 'Premios, subvenciones, ayudas', 'importe', 5, 16
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0017', 'Pérdidas patrimoniales derivadas de transmisiones', 'Minusvalías por venta', 'importe', 5, 17
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0018', 'Pérdidas patrimoniales no derivadas de transmisiones', NULL, 'importe', 5, 18
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0019', 'Rendimiento neto actividades económicas en estim. objetiva', NULL, 'importe', 4, 11
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0416', 'Ganancias patrimoniales de la base imponible del ahorro', 'Ganancias patrimoniales que integran la base del ahorro', 'importe', 6, 20
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0417', 'Pérdidas patrimoniales de la base imponible del ahorro', NULL, 'importe', 6, 21
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0418', 'Saldo neto ganancias y pérdidas patrimoniales', NULL, 'importe', 6, 22
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0447', 'Base imponible general', 'Base imponible del IRPF tras compensaciones', 'importe', 7, 30
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0448', 'Base liquidable general', 'Base general tras mínimos personales', 'importe', 7, 31
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0449', 'Base imponible del ahorro', 'Base del ahorro', 'importe', 7, 32
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0450', 'Base liquidable del ahorro', 'Base del ahorro tras compensaciones', 'importe', 7, 33
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0468', 'Cuota íntegra estatal general', 'Cuota resultante de aplicar el tipo a la base liquidable general', 'importe', 8, 40
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0469', 'Cuota íntegra estatal del ahorro', NULL, 'importe', 8, 41
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0470', 'Cuota íntegra estatal', 'Suma de ambas cuotas', 'importe', 8, 42
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0490', 'Cuota líquida estatal', 'Cuota íntegra menos deducciones estatales', 'importe', 9, 50
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0500', 'Cuota líquida total', 'Cuota estatal + autonómica tras deducciones', 'importe', 10, 55
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '0506', 'Resultado de la declaración', 'A ingresar, a devolver o cero', 'importe', 11, 60
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'Rendimientos del trabajo', 'Retenciones practicadas por rendimientos del trabajo', 'importe', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Rendimientos de actividades económicas', 'Retenciones por actividades económicas, profesionales', 'importe', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Premios', 'Retenciones por premios de loterías, rifas, combinaciones aleatorias', 'importe', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'Capacidad mobiliario', 'Retenciones por rendimientos de capital mobiliario', 'importe', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Imputaciones de renta', 'Retenciones por imputaciones de renta', 'importe', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Ganancias patrimoniales', 'Retenciones por ganancias patrimoniales', 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Contraprestaciones por cesión de derechos de imagen', NULL, 'importe', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Indemnizaciones', 'Retenciones por indemnizaciones como rendimientos de trabajo', 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '09', 'Prestaciones por desempleo', 'Retenciones por prestaciones de desempleo', 'importe', 1, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '10', 'Calificación de beneficiario', NULL, 'numero', 1, 10
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '11', 'Nº de perceptores', 'Número total de perceptores', 'numero', 1, 11
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '12', 'Cuotas a ingresar', 'Total de retenciones e ingresos a cuenta', 'importe', 2, 12
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'Base de retenciones e ingresos a cuenta', 'Base de las rentas de inmuebles urbanos', 'importe', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '115' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Tipo de retención', 'Porcentaje aplicable', 'importe', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '115' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Retenciones', 'Cuota resultante', 'importe', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '115' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'Ingresos a cuenta', NULL, 'importe', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '115' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'A ingresar', 'Resultado de la autoliquidación', 'importe', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '115' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Nº de perceptores', 'Número de perceptores de rentas', 'numero', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '115' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'NIF del perceptor', NULL, 'texto', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '115' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'Entrega de bienes y prestaciones de servicios (régimen general) — base', 'Base imponible de operaciones corrientes', 'importe', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Entrega de bienes y prestaciones de servicios (régimen general) — tipo 21%', 'Cuota al 21%', 'importe', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'Entrega de bienes y prestaciones de servicios (régimen general) — tipo 10%', 'Cuota al 10%', 'importe', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Entrega de bienes y prestaciones de servicios (régimen general) — tipo 4%', 'Cuota al 4%', 'importe', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Adquisiciones interiores de bienes y servicios — base', 'Base de adquisiciones sujetas a inversión del sujeto pasivo', 'importe', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Adquisiciones interiores — cuota al 21%', 'Cuota de adquisiciones al 21%', 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Adquisiciones interiores — cuota al 10%', 'Cuota de adquisiciones al 10%', 'importe', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '09', 'Adquisiciones interiores — cuota al 4%', 'Cuota de adquisiciones al 4%', 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '10', 'Adquisiciones intracomunitarias de bienes — base', 'Base de adquisiciones intracomunitarias', 'importe', 1, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '11', 'Adquisiciones intracomunitarias — cuota al 21%', 'Cuota intracomunitaria 21%', 'importe', 1, 10
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '12', 'Adquisiciones intracomunitarias — cuota al 10%', 'Cuota intracomunitaria 10%', 'importe', 1, 11
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '13', 'Adquisiciones intracomunitarias — cuota al 4%', 'Cuota intracomunitaria 4%', 'importe', 1, 12
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '14', 'Importaciones de bienes', 'Cuota tributaria de las importaciones', 'importe', 1, 13
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '21', 'Operaciones interiores exentas', 'Base de operaciones exentas IVA', 'importe', 1, 14
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '22', 'Exportaciones y operaciones asimiladas', 'Base de exportaciones y operaciones asimiladas', 'importe', 1, 15
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '28', 'Rectificación de deducciones', 'Rectificación anual de deducciones de inversiones', 'importe', 2, 16
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '38', 'Cuota deducible por bienes de inversión', 'Cuota soportada en adquisiciones de bienes de inversión', 'importe', 2, 17
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '39', 'Cuota deducible distintas de bienes de inversión', 'Cuota soportada en adquisiciones corrientes', 'importe', 2, 18
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '40', 'Deducciones por importaciones', 'Cuota de importaciones deducible', 'importe', 2, 19
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '41', 'Deducciones por adquisiciones intracomunitarias', 'Cuota de adquisiciones intracomunitarias deducible', 'importe', 2, 20
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '43', 'Deducción por régimen especial de bienes usados', NULL, 'importe', 2, 21
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '44', 'Deducciones por adquisiciones con inversión del sujeto pasivo', NULL, 'importe', 2, 22
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '46', 'Deducciones por operaciones no sujetas con inversión del sujeto pasivo', NULL, 'importe', 2, 23
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '47', 'Deducciones por cuotas soportadas en adquisiciones de bienes de inversión (régimen especial agrícola)', NULL, 'importe', 2, 24
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '48', 'Cuotas soportadas en adquisiciones o importaciones de bienes de capital no deducibles', NULL, 'importe', 2, 25
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '49', 'Regularización de cuotas soportadas no deducibles', NULL, 'importe', 2, 26
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '50', 'Total cuotas deducibles', 'Suma de todas las cuotas deducibles', 'importe', 2, 27
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '51', 'Resultado líquido', 'Diferencia entre cuota repercutida y deducible', 'importe', 2, 28
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '52', 'Compensaciones pendientes de aplicación de periodos anteriores', NULL, 'importe', 2, 29
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '53', 'Regularización anual de cuotas', 'Resultado de la regularización anual', 'importe', 2, 30
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '54', 'Deducciones por exportaciones temporales', NULL, 'importe', 2, 31
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '55', 'Autoliquidaciones de subgrupos de IVA', NULL, 'importe', 2, 32
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '56', 'Autoliquidaciones de grupos de IVA', NULL, 'importe', 2, 33
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '57', 'Cuota devengada', 'Total cuotas repercutidas', 'importe', 2, 34
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '58', 'Cuota deducible', 'Total cuotas deducibles', 'importe', 2, 35
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '59', 'Resultado de las liquidaciones', 'Diferencia', 'importe', 2, 36
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '60', 'A compensar', 'Cuota a compensar en periodos siguientes', 'importe', 2, 37
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '61', 'A devolver', 'Cuota a devolver', 'importe', 2, 38
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '62', 'A ingresar', 'Resultado final a ingresar', 'importe', 3, 39
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '63', 'Número de operaciones intracomunitarias', 'Nº total de operaciones intracomunitarias', 'numero', 3, 40
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '64', 'Entregas intracomunitarias de bienes', 'Base de entregas intracomunitarias', 'importe', 3, 41
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '65', 'Número de entregas intracomunitarias', NULL, 'numero', 3, 42
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '66', 'Adquisiciones intracomunitarias notificadas en territorio', 'Base de adquisiciones notificadas', 'importe', 3, 43
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '67', 'Número de adquisiciones', NULL, 'numero', 3, 44
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '68', 'Entregas de bienes a distancia desde otros Estados miembros', 'Base de entregas a distancia desde otros EEMM', 'importe', 3, 45
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '69', 'Entregas de bienes a distancia desde terceros países (régimen IOSS)', NULL, 'importe', 3, 46
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '70', 'Entregas de bienes a distancia desde terceros países (no IOSS)', NULL, 'importe', 3, 47
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '71', 'Ventas a distancia y servicios a particulares', 'Operaciones realizadas desde otros EEMM', 'importe', 3, 48
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '72', 'Cuotas satisfechas en régimen OSS — tipo reducido', NULL, 'importe', 3, 49
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '73', 'Cuotas satisfechas en régimen OSS — tipo normal', NULL, 'importe', 3, 50
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '74', 'Cuotas satisfechas en régimen OSS — servicios', NULL, 'importe', 3, 51
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '75', 'Adquisiciones intracomunitarias de servicios', NULL, 'importe', 3, 52
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '76', 'Cuota deducible por adquisiciones intracomunitarias de servicios', NULL, 'importe', 3, 53
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '77', 'Servicios prestados por empresarios no establecidos', NULL, 'importe', 3, 54
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '78', 'Operaciones no sujetas con inversión del sujeto pasivo', NULL, 'importe', 3, 55
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '79', 'Total de operaciones del período', 'Volumen total de operaciones', 'importe', 3, 56
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '80', 'Operaciones realizadas por empresarios no establecidos', NULL, 'importe', 3, 57
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'Total base imponible operaciones corrientes (régimen general)', NULL, 'importe', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Total cuota operaciones corrientes (régimen general) — tipo 21%', NULL, 'importe', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'Total cuota operaciones corrientes (régimen general) — tipo 10%', NULL, 'importe', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Total cuota operaciones corrientes (régimen general) — tipo 4%', NULL, 'importe', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Total base adquisiciones interiores — inversión sujeto pasivo', NULL, 'importe', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '10', 'Total base adquisiciones intracomunitarias', NULL, 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '14', 'Total base importaciones', NULL, 'importe', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '21', 'Total base operaciones interiores exentas', NULL, 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '22', 'Total base exportaciones y asimiladas', NULL, 'importe', 1, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '28', 'Rectificación anual de deducciones', NULL, 'importe', 1, 10
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '38', 'Cuota deducible bienes de inversión', NULL, 'importe', 1, 11
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '39', 'Cuota deducible corriente', NULL, 'importe', 1, 12
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '40', 'Total deducciones por importaciones', NULL, 'importe', 1, 13
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '41', 'Total deducciones por adquisiciones intracomunitarias', NULL, 'importe', 1, 14
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '50', 'Total cuotas deducibles', NULL, 'importe', 1, 15
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '51', 'Resultado', NULL, 'importe', 1, 16
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '62', 'Total a ingresar', NULL, 'importe', 1, 17
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '63', 'Nº operaciones intracomunitarias', NULL, 'numero', 1, 18
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '64', 'Entregas intracomunitarias', NULL, 'importe', 1, 19
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '66', 'Adquisiciones intracomunitarias', NULL, 'importe', 1, 20
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '69', 'Volumen total de operaciones', NULL, 'importe', 1, 21
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '95', 'Régimen especial agricultura — base', NULL, 'importe', 1, 22
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '97', 'Régimen especial agricultura — compensaciones', NULL, 'importe', 1, 23
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '111', 'Resumen anual', 'Referencia al resumen anual', 'texto', 1, 24
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF del declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', 'Año al que se refiere la declaración', 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Tipo de declaración', 'Normal o complementaria', 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '14', 'NIF del tercero', 'NIF de la persona o entidad con la que se realizan operaciones', 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '15', 'Apellidos o denominación social del tercero', NULL, 'texto', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '16', 'Importe total operaciones', 'Importe anual de operaciones con el tercero (umbral > 3.005,06 €)', 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '17', 'Importe total operaciones en metálico', 'Operaciones en efectivo', 'importe', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '18', 'Importe total cobros en metálico', NULL, 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '19', 'Importe total percibido en metálico', NULL, 'importe', 1, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '20', 'Identificación de inmuebles — referencia catastral', NULL, 'texto', 1, 10
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '21', 'Identificación de inmuebles — dirección', NULL, 'texto', 1, 11
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '22', 'Nº de titular', NULL, 'numero', 1, 12
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '23', 'Importe percibido por arrendamiento de inmuebles', NULL, 'importe', 1, 13
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '24', 'Importe percibido por subarriendo', NULL, 'importe', 1, 14
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '25', 'Tipo de operación', 'Entrega de bienes, prestación de servicios, arrendamiento', 'texto', 1, 15
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '26', 'Periodo de imputación', 'Trimestre al que se imputan las operaciones', 'texto', 1, 16
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF del declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Periodo', 'Mensual o trimestral', 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'Tipo de declaración', 'Normal o complementaria', 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'NIF del operador comunitario', 'NIF-IVA del destinatario en otro Estado miembro', 'texto', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Apellidos o denominación social del operador', NULL, 'texto', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'País del operador', 'Código de país del Estado miembro', 'texto', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Clave de operación', 'A=Entrega bienes, B=Adquisición bienes, C=Servicios, D=Triangulación', 'texto', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '09', 'Base imponible', 'Importe de las operaciones con el operador', 'importe', 1, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '10', 'Facturas rectificativas', 'Nº de facturas rectificativas incluidas', 'numero', 1, 10
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF del declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Tipo de declaración', 'Normal o complementaria', 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'Rendimientos del trabajo — nº perceptores', NULL, 'numero', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Rendimientos del trabajo — base de retenciones', 'Suma de bases de retenciones por rendimientos del trabajo', 'importe', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Rendimientos del trabajo — retenciones', 'Total de retenciones por rendimientos del trabajo', 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Actividades económicas — nº perceptores', NULL, 'numero', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Actividades económicas — base de retenciones', NULL, 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '09', 'Actividades económicas — retenciones', NULL, 'importe', 1, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '10', 'Capital mobiliario — nº perceptores', NULL, 'numero', 1, 10
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '11', 'Capital mobiliario — base de retenciones', NULL, 'importe', 1, 11
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '12', 'Capital mobiliario — retenciones', NULL, 'importe', 1, 12
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '13', 'Premios — nº perceptores', NULL, 'numero', 1, 13
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '14', 'Premios — base de retenciones', NULL, 'importe', 1, 14
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '15', 'Premios — retenciones', NULL, 'importe', 1, 15
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '16', 'Ganancias patrimoniales — nº perceptores', NULL, 'numero', 1, 16
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '17', 'Ganancias patrimoniales — base de retenciones', NULL, 'importe', 1, 17
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '18', 'Ganancias patrimoniales — retenciones', NULL, 'importe', 1, 18
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '19', 'Imputaciones de renta — nº perceptores', NULL, 'numero', 1, 19
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '20', 'Imputaciones de renta — base de retenciones', NULL, 'importe', 1, 20
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '21', 'Imputaciones de renta — retenciones', NULL, 'importe', 1, 21
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF del declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Tipo de declaración', NULL, 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'NIF del perceptor', NULL, 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'NIF representante del perceptor', NULL, 'texto', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Clave de rendimiento', 'Tipo de rendimiento: A=Dividendos, B=Intereses, C=Rendimientos cuenta corriente, etc.', 'texto', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Nº percepciones', 'Número de percepciones al perceptor', 'numero', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Base de retención o ingreso a cuenta', NULL, 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '09', 'Tipo de retención', NULL, 'importe', 1, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '10', 'Cuota', 'Retención practicada', 'importe', 1, 10
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '11', 'Base no sujeta por residencia en otro EEMM', NULL, 'importe', 1, 11
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '12', 'Comentarios', NULL, 'texto', 1, 12
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF del declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Tipo de declaración', NULL, 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'NIF del perceptor', NULL, 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'NIF representante del perceptor', NULL, 'texto', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Clave de rendimiento', NULL, 'texto', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Nº percepciones', NULL, 'numero', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Base de retención', NULL, 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '09', 'Tipo de retención', NULL, 'importe', 1, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '10', 'Cuota', NULL, 'importe', 1, 10
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '11', 'Base no sujeta por residencia EEMM', NULL, 'importe', 1, 11
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF del declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '180' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '180' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Tipo de declaración', NULL, 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '180' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'NIF del perceptor', NULL, 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '180' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Clave', NULL, 'texto', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '180' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Base de retenciones e ingresos a cuenta', NULL, 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '180' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Tipo de retención', NULL, 'importe', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '180' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Retenciones', NULL, 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '180' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '09', 'Nº de expedientes', NULL, 'numero', 1, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '180' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF del declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '187' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '187' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'NIF del perceptor', NULL, 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '187' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'Clave de rendimiento', 'A=Dividendos, B=Intereses, C=Reembolso participaciones', 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '187' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Nº percepciones', NULL, 'numero', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '187' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Base de retención', NULL, 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '187' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Tipo de retención', NULL, 'importe', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '187' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Cuota', NULL, 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '187' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF del declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '189' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '189' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'NIF del socio/partícipe', NULL, 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '189' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'Clave', NULL, 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '189' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Importe total de beneficios distribuidos', NULL, 'importe', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '189' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Importe retenido', NULL, 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '189' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF del declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '194' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '194' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Tipo de operación', 'A=Operaciones vinculadas, B=Operaciones paraísos fiscales', 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '194' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'NIF del tercero', NULL, 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '194' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Denominación del tercero', NULL, 'texto', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '194' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'País de residencia', NULL, 'texto', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '194' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Importe de la operación', NULL, 'importe', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '194' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Método de valoración', 'Método de valoración de operaciones vinculadas', 'texto', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '194' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF del declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '198' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '198' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'NIF del perceptor', NULL, 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '198' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'Clave de activo', NULL, 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '198' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Nº de operaciones', NULL, 'numero', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '198' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Valor de transmisión', NULL, 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '198' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Valor de adquisición', NULL, 'importe', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '198' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Ganancia o pérdida', NULL, 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '198' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF del declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'NIF del perceptor no residente', NULL, 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'País de residencia del perceptor', NULL, 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Clave de rendimiento', NULL, 'texto', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Nº percepciones', NULL, 'numero', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Base de retención', NULL, 'importe', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Tipo de retención', NULL, 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '09', 'Cuota', NULL, 'importe', 1, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '10', 'Aplicación de convenio', 'Indica si se aplica convenio de doble imposición', 'texto', 1, 10
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '001', 'Causas de presentación', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '036' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '002', 'NIF/NIE', NULL, 'texto', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '036' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '003', 'Apellidos y nombre / Denominación', NULL, 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '036' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '004', 'Domicilio fiscal', NULL, 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '036' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '005', 'Epígrafes IAE', 'Actividades económicas en el censo', 'texto', 2, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '036' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '006', 'Régimen de IVA', 'Régimen tributario del IVA', 'texto', 2, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '036' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '007', 'Régimen de retenciones', 'Régimen de retenciones e ingresos a cuenta', 'texto', 2, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '036' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '008', 'Delegación/Empresa', 'Delegación o empresa que presenta', 'texto', 2, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '036' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'Rendimientos del trabajo', NULL, 'importe', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '123' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Actividades económicas', NULL, 'importe', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '123' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Premios', NULL, 'importe', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '123' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'Capital mobiliario', NULL, 'importe', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '123' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Imputaciones de renta', NULL, 'importe', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '123' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Ganancias patrimoniales', NULL, 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '123' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Contraprestaciones por cesión de derechos de imagen', NULL, 'importe', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '123' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Indemnizaciones', NULL, 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '123' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '09', 'Prestaciones por desempleo', NULL, 'importe', 1, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '123' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '10', 'Otras rentas', NULL, 'importe', 1, 10
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '123' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '11', 'Nº de perceptores', NULL, 'numero', 1, 11
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '123' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '12', 'Cuotas a ingresar', NULL, 'importe', 1, 12
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '123' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'Rendimientos netos estimación objetiva', NULL, 'importe', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '130' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Rendimientos netos reducido estimación objetiva', NULL, 'importe', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '130' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Rendimientos netos estimación objetiva — Ceuta y Melilla', NULL, 'importe', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '130' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'Rendimientos netos reducido estimación objetiva — Ceuta y Melilla', NULL, 'importe', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '130' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Pagos fraccionados previos', NULL, 'importe', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '130' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Resultado a ingresar', NULL, 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '130' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'Rentas obtenidas sin mediación de establecimiento permanente — base', NULL, 'importe', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '124' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Rentas obtenidas sin mediación de establecimiento permanente — retención', NULL, 'importe', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '124' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Rendimientos del capital mobiliario', NULL, 'importe', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '124' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'Ganancias patrimoniales', NULL, 'importe', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '124' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Nº de perceptores', NULL, 'numero', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '124' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Cuotas a ingresar', NULL, 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '124' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF del declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Mes', NULL, 'numero', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'NIF del perceptor no residente', NULL, 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'País de residencia', NULL, 'texto', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Clave de rendimiento', NULL, 'texto', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Base de retención', NULL, 'importe', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '08', 'Tipo de retención', NULL, 'importe', 1, 8
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '09', 'Cuota', NULL, 'importe', 1, 9
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF de la entidad declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '289' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '289' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'Tipo de entidad', NULL, 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '289' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'NIF del titular de la cuenta', NULL, 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '289' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'País de residencia del titular', NULL, 'texto', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '289' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Saldo o valor de la cuenta', NULL, 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '289' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '07', 'Rendimientos financieros', NULL, 'importe', 1, 7
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '289' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '01', 'NIF de la entidad declarante', NULL, 'texto', 1, 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '290' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '02', 'Ejercicio', NULL, 'numero', 1, 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '290' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '03', 'NIF del titular de la cuenta', NULL, 'texto', 1, 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '290' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '04', 'País de residencia fiscal (EEUU)', NULL, 'texto', 1, 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '290' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '05', 'Saldo o valor de la cuenta', NULL, 'importe', 1, 5
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '290' AND mc.campana = '2025';
INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden)
SELECT mc.id, '06', 'Rendimientos financieros', NULL, 'importe', 1, 6
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '290' AND mc.campana = '2025';

-- 5. modelo_clave
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '01', 'Rendimientos del trabajo', 'Clave de rendimiento: trabajo', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '02', 'Actividades económicas', 'Clave de rendimiento: actividades económicas', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '03', 'Premios', 'Clave de rendimiento: premios', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '04', 'Capital mobiliario', 'Clave de rendimiento: capital mobiliario', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '05', 'Ganancias patrimoniales', 'Clave de rendimiento: ganancias patrimoniales', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'A', 'Rendimientos del trabajo', 'Clave: rendimientos del trabajo', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'B', 'Actividades económicas', 'Clave: actividades económicas', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'C', 'Premios', 'Clave: premios', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'D', 'Ganancias patrimoniales', 'Clave: ganancias patrimoniales', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '190' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'A', 'Dividendos y demás rendimientos de participación en recursos propios', 'Clave: dividendos', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'B', 'Rendimientos de cuenta corriente, depósitos y seguros de vida', 'Clave: intereses y seguros', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'C', 'Rendimientos derivados de la transmisión de activos financieros', 'Clave: transmisión activos', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'D', 'Rendimientos de contratos de renta vitalicia', 'Clave: renta vitalicia', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'E', 'Rendimientos de operaciones de capitalización', 'Clave: capitalización', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '193' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'A', 'Dividendos', 'Clave: dividendos', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'B', 'Intereses y seguros', 'Clave: intereses', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'C', 'Transmisión activos financieros', 'Clave: transmisión', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '196' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'A', 'Rendimientos del capital mobiliario', 'Clave IRNR: capital mobiliario', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'B', 'Ganancias patrimoniales', 'Clave IRNR: ganancias patrimoniales', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'C', 'Rentas inmobiliarias', 'Clave IRNR: renta inmuebles', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'D', 'Rentas de actividades económicas', 'Clave IRNR: actividades económicas', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'A', 'Rendimientos del capital mobiliario', 'Clave IRNR: capital mobiliario sin EP', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'B', 'Ganancias patrimoniales', 'Clave IRNR: ganancias patrimoniales sin EP', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'C', 'Rentas inmobiliarias', 'Clave IRNR: inmuebles sin EP', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, 'D', 'Rentas de actividades económicas', 'Clave IRNR: actividades sin EP', 'rendimiento'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '0', 'Régimen general', 'Clave de régimen: general', 'regimen'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '1', 'Régimen especial de agricultura, ganadería y pesca', 'Clave de régimen: agrícola', 'regimen'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '2', 'Régimen especial del recargo de equivalencia', 'Clave de régimen: recargo equivalencia', 'regimen'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '3', 'Régimen especial de bienes usados', 'Clave de régimen: bienes usados', 'regimen'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '4', 'Régimen especial del criterio de caja', 'Clave de régimen: criterio caja', 'regimen'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '5', 'Régimen especial de agencias de viajes', 'Clave de régimen: agencias viaje', 'regimen'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '6', 'Régimen especial de servicios de telecomunicaciones', 'Clave de régimen: telecomunicaciones', 'regimen'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_clave (campana_id, codigo, etiqueta, descripcion, tipo_clave)
SELECT mc.id, '7', 'Régimen especial OSS (One Stop Shop)', 'Clave de régimen: OSS', 'regimen'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';

-- 6. modelo_instruccion
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'caracteristicas', '¿Qué es el modelo 100?', 'El modelo 100 es la declaración anual del IRPF. Permite regularizar la situación fiscal del contribuyente respecto al Impuesto sobre la Renta de las Personas Físicas durante todo el año natural.', 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'quien-debe', '¿Quién debe presentar?', 'Todos los residentes fiscales en España que hayan obtenido rentas durante el ejercicio, salvo que estén exentos por el importe y tipo de rentas percibidas.', 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'plazo', 'Plazo de presentación', 'Generalmente de abril a junio del año siguiente al que corresponda la declaración. Consulte cada año las fechas concretas en la sede de la AEAT.', 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'como-rellenar', 'Cómo rellenar', '1. Identifíquese con Cl@ve, certificado electrónico o referencia.\n2. Revise los datos fiscales disponibles (borrador).\n3. Complete o modifique las casillas que correspondan.\n4. Verifique la casilla 0506 (Resultado de la declaración).\n5. Si es a ingresar, domicilie el pago o seleccione la forma de pago.\n6. Si es a devolver, indique el IBAN para la devolución.', 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'caracteristicas', '¿Qué es el modelo 303?', 'Autoliquidación periódica del IVA. Se presenta de forma trimestral (o mensual para grandes empresas) y declara las cuotas repercutidas y deducibles del Impuesto sobre el Valor Añadido.', 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'quien-debe', '¿Quién debe presentar?', 'Todos los sujetos pasivos del IVA, incluidos los inscritos en el ROI, los que realicen entregas de bienes o prestaciones de servicios sujetas al impuesto.', 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'plazo', 'Plazo de presentación', 'Trimestral: del 1 al 20 de abril, julio, octubre y del 1 al 30 de enero del año siguiente.\nMensual: del 1 al 20 del mes siguiente al periodo de liquidación.', 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'como-rellenar', 'Cómo rellenar', '1. Registre en las casillas 01-05 la base y cuota de operaciones corrientes.\n2. Registre adquisiciones interiores (06-09) e intracomunitarias (10-13).\n3. Declare importaciones (14).\n4. Registre operaciones exentas (21) y exportaciones (22).\n5. Indique la cuota deducible (38-50).\n6. Calcule el resultado (51).\n7. Si es a ingresar (62), a compensar (60) o a devolver (61).', 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'caracteristicas', '¿Qué es el modelo 111?', 'Declaración trimestral de retenciones e ingresos a cuenta del IRPF sobre rendimientos del trabajo, actividades económicas, premios y determinadas ganancias patrimoniales.', 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'quien-debe', '¿Quién debe presentar?', 'Los obligados a practicar retenciones o ingresos a cuenta por los rendimientos mencionados.', 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'plazo', 'Plazo de presentación', 'Del 1 al 20 de abril, julio, octubre y del 1 al 20 de enero.', 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'como-rellenar', 'Cómo rellenar', '1. Identifíquese como declarante.\n2. Indique el número de perceptores por cada tipo de rendimiento.\n3. Registre las bases de retención y las cuotas correspondientes.\n4. Verifique la casilla 12 (Cuotas a ingresar).', 4
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'caracteristicas', '¿Qué es el modelo 036?', 'Declaración censal de alta, modificación de datos y baja en el Censo de Empresarios, Profesion y Retenedores.', 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '036' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'quien-debe', '¿Quién debe presentar?', 'Personas físicas y jurídicas que inicien una actividad empresarial o profesional, modifiquen sus datos censales o cesen en la actividad.', 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '036' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'plazo', 'Plazo de presentación', 'En el plazo de un mes desde la fecha de inicio de la actividad o desde que se produzca la modificación de datos.', 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '036' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'caracteristicas', '¿Qué es el modelo 347?', 'Declaración anual de operaciones con terceras personas. Se debe presentar cuando el volumen de operaciones con un mismo tercero supera los 3.005,06 euros en el año natural.', 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'quien-debe', '¿Quién debe presentar?', 'Personas físicas y jurídicas, incluidas las entidades en régimen de atribución de rentas, que hayan realizado operaciones con terceros por importe superior a 3.005,06 euros.', 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'plazo', 'Plazo de presentación', 'Del 1 al 28 de febrero del año siguiente al que corresponda la declaración.', 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'caracteristicas', '¿Qué es el modelo 349?', 'Declaración recapitulativa de operaciones intracomunitarias. Informa de las entregas y adquisiciones de bienes y servicios entre Estados miembros de la UE.', 1
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'quien-debe', '¿Quién debe presentar?', 'Sujetos pasivos del IVA que realicen operaciones intracomunitarias de bienes o servicios.', 2
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
SELECT mc.id, 'plazo', 'Plazo de presentación', 'Mensual o trimestral según el volumen de operaciones. Del 1 al 20 del mes siguiente al periodo.', 3
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';

-- 7. modelo_campana_operativa
INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion, ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen, norma_base, nota, origen_metadato, estado_metadato)
SELECT mc.id, 'contribuyente_irpf', 'anual', 'campana_renta_aeat', 'electronica', 'Deben presentar el modelo 100 los contribuyentes del IRPF obligados a declarar conforme a los limites legales vigentes.', 'La presentacion del modelo 100 se realiza dentro del plazo general de la campana de renta fijado cada ano por la AEAT.', 'La presentacion del modelo 100 se realiza por via electronica mediante la sede de la AEAT, con los sistemas de identificacion admitidos en cada campana.', 'LIRPF', 'Metadato operativo curado para agentes.', 'seed_curado', 'curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion, ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen, norma_base, nota, origen_metadato, estado_metadato)
SELECT mc.id, 'retenedor_irpf', 'trimestral', 'primeros_20_dias_periodo_siguiente', 'electronica', 'Deben presentar el modelo 111 los obligados a practicar retenciones e ingresos a cuenta por rendimientos del trabajo y determinadas actividades economicas.', 'El modelo 111 se presenta trimestralmente del 1 al 20 de abril, julio, octubre y enero.', 'La presentacion del modelo 111 se realiza por via electronica a traves de la sede de la AEAT.', 'LIRPF retenciones', 'Metadato operativo curado para agentes.', 'seed_curado', 'curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion, ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen, norma_base, nota, origen_metadato, estado_metadato)
SELECT mc.id, 'retenedor_arrendamientos', 'trimestral', 'primeros_20_dias_periodo_siguiente', 'electronica', 'Deben presentar el modelo 115 los obligados a practicar retenciones por arrendamientos de inmuebles urbanos.', 'El modelo 115 se presenta trimestralmente del 1 al 20 de abril, julio, octubre y enero.', 'La presentacion del modelo 115 se realiza por via electronica a traves de la sede de la AEAT.', 'LIRPF arrendamientos', 'Metadato operativo curado para agentes.', 'seed_curado', 'curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '115' AND mc.campana = '2025';
INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion, ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen, norma_base, nota, origen_metadato, estado_metadato)
SELECT mc.id, 'retenedor_irnr', 'mensual', 'primeros_20_dias_mes_siguiente', 'electronica', 'Deben presentar el modelo 124 los obligados a retener sobre determinadas rentas del capital mobiliario obtenidas por no residentes sin establecimiento permanente.', 'El modelo 124 se presenta mensualmente dentro de los primeros veinte dias naturales del mes siguiente al periodo declarado.', 'La presentacion del modelo 124 se realiza por medios electronicos a traves de la sede de la AEAT.', 'IRNR art. 25', 'Metadato operativo curado para agentes.', 'seed_curado', 'curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '124' AND mc.campana = '2025';
INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion, ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen, norma_base, nota, origen_metadato, estado_metadato)
SELECT mc.id, 'retenedor_irnr', 'mensual', 'primeros_20_dias_mes_siguiente', 'electronica', 'Deben presentar el modelo 216 los obligados a practicar retenciones e ingresos a cuenta sobre determinadas rentas de no residentes sin establecimiento permanente.', 'El modelo 216 se presenta mensualmente dentro de los primeros veinte dias naturales del mes siguiente al periodo declarado.', 'La presentacion del modelo 216 se realiza por via electronica a traves de la sede de la AEAT.', 'IRNR art. 14', 'Metadato operativo curado para agentes.', 'seed_curado', 'curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '216' AND mc.campana = '2025';
INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion, ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen, norma_base, nota, origen_metadato, estado_metadato)
SELECT mc.id, 'retenedor_irnr', 'anual', 'plazo_fijado_aeat', 'electronica', 'Deben presentar el modelo 296 los retenedores y obligados a ingresar a cuenta que deban resumir anualmente las rentas sujetas al IRNR sin establecimiento permanente.', 'El modelo 296 se presenta con caracter anual en el plazo fijado por la AEAT para el resumen anual de retenciones e ingresos a cuenta.', 'La presentacion del modelo 296 se realiza electronicamente mediante la sede de la AEAT.', 'IRNR art. 14', 'Metadato operativo curado para agentes.', 'seed_curado', 'curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '296' AND mc.campana = '2025';
INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion, ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen, norma_base, nota, origen_metadato, estado_metadato)
SELECT mc.id, 'empresario_o_profesional_iva', 'trimestral', 'plazo_general_aeat', 'electronica', 'Deben presentar el modelo 303 los empresarios y profesionales obligados a autoliquidar el IVA del periodo.', 'El modelo 303 se presenta en los plazos generales fijados por la AEAT para la autoliquidacion del IVA.', 'La presentacion del modelo 303 se realiza por via electronica mediante la sede de la AEAT.', 'LIVA art. 71', 'Metadato operativo curado para agentes.', 'seed_curado', 'curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion, ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen, norma_base, nota, origen_metadato, estado_metadato)
SELECT mc.id, 'operador_intracomunitario_iva', 'mensual', 'primeros_20_dias_mes_siguiente', 'electronica', 'Deben presentar el modelo 349 los sujetos pasivos del IVA que realicen operaciones intracomunitarias de bienes o servicios.', 'El modelo 349 se presenta con caracter mensual o trimestral segun el volumen de operaciones, del 1 al 20 del mes siguiente al periodo.', 'La presentacion del modelo 349 se realiza por via electronica a traves de la sede de la AEAT.', 'LIVA operaciones intracomunitarias', 'Metadato operativo curado para agentes.', 'seed_curado', 'curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion, ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen, norma_base, nota, origen_metadato, estado_metadato)
SELECT mc.id, 'sujeto_pasivo_iva', 'anual', 'plazo_fijado_aeat', 'electronica', 'Deben presentar el modelo 390 los sujetos pasivos del IVA obligados a presentar el resumen anual, salvo excepciones previstas por la normativa.', 'El modelo 390 se presenta con caracter anual en el plazo fijado por la AEAT junto con el cierre del ejercicio de IVA.', 'La presentacion del modelo 390 se realiza por via electronica mediante la sede de la AEAT.', 'LIVA resumen anual', 'Metadato operativo curado para agentes.', 'seed_curado', 'curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion, ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen, norma_base, nota, origen_metadato, estado_metadato)
SELECT mc.id, 'obligado_censal', 'eventual', '1_mes_desde_hecho', 'electronica', 'Deben presentar el modelo 036 las personas fisicas o juridicas que inicien actividad, modifiquen datos censales o causen baja en el censo.', 'El modelo 036 se presenta dentro del plazo de un mes desde el inicio de actividad o desde la modificacion censal correspondiente.', 'La presentacion del modelo 036 puede realizarse por la sede de la AEAT con los sistemas de identificacion admitidos.', 'Censo AEAT', 'Metadato operativo curado para agentes.', 'seed_curado', 'curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '036' AND mc.campana = '2025';
INSERT INTO modelo_campana_operativa (campana_id, categoria_obligado, frecuencia_presentacion, ventana_presentacion, canal_presentacion, obligados_resumen, plazo_resumen, presentacion_resumen, norma_base, nota, origen_metadato, estado_metadato)
SELECT mc.id, 'declarante_operaciones_terceros', 'anual', 'febrero_ano_siguiente', 'electronica', 'Deben presentar el modelo 347 quienes hayan realizado operaciones con terceros por importe superior al umbral legal anual.', 'El modelo 347 se presenta con caracter anual durante el mes de febrero del ano siguiente.', 'La presentacion del modelo 347 se realiza por via electronica a traves de la sede de la AEAT.', 'LGT informacion terceros', 'Metadato operativo curado para agentes.', 'seed_curado', 'curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';

-- 8. modelo_fiscal_calendar
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-04-01', '2025-06-30', '2025-07-30', 'Campana IRPF 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-04-01', '2025-04-20', NULL, 'Q1 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-07-01', '2025-07-20', NULL, 'Q2 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-10-01', '2025-10-20', NULL, 'Q3 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2026-01-01', '2026-01-20', NULL, 'Q4 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-04-01', '2025-04-20', NULL, 'Q1 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '115' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-07-01', '2025-07-20', NULL, 'Q2 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '115' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-10-01', '2025-10-20', NULL, 'Q3 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '115' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2026-01-01', '2026-01-20', NULL, 'Q4 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '115' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-04-01', '2025-04-20', NULL, 'Q1 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-07-01', '2025-07-20', NULL, 'Q2 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-10-01', '2025-10-20', NULL, 'Q3 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2026-01-01', '2026-01-20', NULL, 'Q4 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-02-01', '2025-02-20', NULL, 'Mensual IVA intracomunitario', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2026-01-01', '2026-01-30', NULL, 'Anual 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-02-01', '2025-02-28', NULL, 'Anual 2024', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-04-01', '2025-04-20', NULL, 'Q1 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '289' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-07-01', '2025-07-20', NULL, 'Q2 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '289' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2025-10-01', '2025-10-20', NULL, 'Q3 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '289' AND mc.campana = '2025';
INSERT INTO modelo_fiscal_calendar (campana_id, fecha_inicio_presentacion, fecha_fin_presentacion, fecha_fin_prorroga, observaciones, fuente)
SELECT mc.id, '2026-01-01', '2026-01-20', NULL, 'Q4 2025', 'seed_curado'
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '289' AND mc.campana = '2025';

-- 9. modelo_formato
INSERT INTO modelo_formato (campana_id, tipo_registro, campos, url_diseno)
SELECT mc.id, 'electronico', '{"tipo": "electronico", "formato": "XML", "version": "2025", "esquema": "esdata_100_2025", "validacion": "XSD"}', NULL
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '100' AND mc.campana = '2025';
INSERT INTO modelo_formato (campana_id, tipo_registro, campos, url_diseno)
SELECT mc.id, 'electronico', '{"tipo": "electronico", "formato": "XML", "version": "2025", "esquema": "esdata_111_2025", "validacion": "XSD"}', NULL
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '111' AND mc.campana = '2025';
INSERT INTO modelo_formato (campana_id, tipo_registro, campos, url_diseno)
SELECT mc.id, 'electronico', '{"tipo": "electronico", "formato": "XML", "version": "2025", "esquema": "esdata_303_2025", "validacion": "XSD"}', NULL
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '303' AND mc.campana = '2025';
INSERT INTO modelo_formato (campana_id, tipo_registro, campos, url_diseno)
SELECT mc.id, 'electronico', '{"tipo": "electronico", "formato": "XML", "version": "2025", "esquema": "esdata_347_2025", "validacion": "XSD"}', NULL
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '347' AND mc.campana = '2025';
INSERT INTO modelo_formato (campana_id, tipo_registro, campos, url_diseno)
SELECT mc.id, 'electronico', '{"tipo": "electronico", "formato": "XML", "version": "2025", "esquema": "esdata_349_2025", "validacion": "XSD"}', NULL
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '349' AND mc.campana = '2025';
INSERT INTO modelo_formato (campana_id, tipo_registro, campos, url_diseno)
SELECT mc.id, 'electronico', '{"tipo": "electronico", "formato": "XML", "version": "2025", "esquema": "esdata_289_2025", "validacion": "XSD"}', NULL
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '289' AND mc.campana = '2025';
INSERT INTO modelo_formato (campana_id, tipo_registro, campos, url_diseno)
SELECT mc.id, 'electronico', '{"tipo": "electronico", "formato": "XML", "version": "2025", "esquema": "esdata_390_2025", "validacion": "XSD"}', NULL
FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id WHERE m.codigo = '390' AND mc.campana = '2025';

-- 10. modelo_articulo — placeholder (se llena con artículos reales)
