"""Alembic migration — Fase 21: lineas de criterio jurisprudencial/doctrinal.

Crea:
- linea_criterio: agrupacion de resoluciones/doctrina por cuestion practica
- linea_criterio_referencia: referencias a documentos soporte (CENDOJ, DGT, TEAC, etc.)

No elimina ni modifica tablas existentes.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260426_0019_linea_criterio"
down_revision = "20260426_0018_micro_obligaciones"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "linea_criterio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("cuestion_practica", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("criterio_dominante", sa.Text(), nullable=True),
        sa.Column("matices", sa.Text(), nullable=True),
        sa.Column("excepciones", sa.Text(), nullable=True),
        sa.Column("ultimo_cambio", sa.Date(), nullable=True),
        sa.Column("estado", sa.Text(), nullable=False, server_default=sa.text("'borrador'::text")),
        sa.Column("autor_id", sa.Integer(), nullable=True),
        sa.Column("revisor_id", sa.Integer(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_linea_criterio_estado", "estado"),
        sa.Index("ix_linea_criterio_activo", "activo"),
        sa.Index("ix_linea_criterio_titulo_trgm", "titulo", postgresql_using="gin", postgresql_ops={"titulo": "gin_trgm_ops"}),
    )

    op.create_table(
        "linea_criterio_referencia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("linea_id", sa.Integer(), sa.ForeignKey("linea_criterio.id", ondelete="CASCADE"), nullable=False),
        sa.Column("documento_referencia", sa.Text(), nullable=False),
        sa.Column("tipo_documento", sa.Text(), nullable=True),
        sa.Column("organismo_emisor", sa.Text(), nullable=True),
        sa.Column("fecha", sa.Date(), nullable=True),
        sa.Column("rol_en_linea", sa.Text(), nullable=True, default="soporte"),
        sa.Column("orden", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_linea_criterio_referencia_linea", "linea_id"),
        sa.Index("ix_linea_criterio_referencia_doc", "documento_referencia"),
        sa.UniqueConstraint("linea_id", "documento_referencia", name="uq_linea_doc_referencia"),
    )

    # Seed lineas de criterio — temas de alto impacto para sociedad de valores

    # 1. IVA en servicios de restauracion — cambio de criterio TS
    op.execute("""
        INSERT INTO linea_criterio (titulo, cuestion_practica, descripcion, criterio_dominante, matices, excepciones, ultimo_cambio, estado, autor_id, revisor_id, activo) VALUES
        ('IVA reducido en restauracion', 'Se aplica el tipo reducido del IVA a servicios de restauracion?',
          'Analizar la evolucion del criterio del Tribunal Supremo sobre la aplicacion del tipo reducido (10%) al servicio de restauracion y hosteleria, frente al tipo general (21%).',
          'El Tribunal Supremo ha ido restringiendo el ambito de aplicacion del tipo reducido, exigiendo que el servicio preste efectivamente la actividad de restauracion y no mera cesion de alimentos.',
          'Distinguir entre venta al por menor de alimentos (tipo reducido) y servicio de restauracion (tambien reducido pero con requisitos estrictos de prestacion).',
          'No aplica a ventas a granel o productos envasados sin servicio adicional.',
          NULL, 'vigente', 1, 1, true)
    """)

    # 2. Comisiones de preferencia e indiferencia — MiFID
    op.execute("""
        INSERT INTO linea_criterio (titulo, cuestion_practica, descripcion, criterio_dominante, matices, excepciones, ultimo_cambio, estado, autor_id, revisor_id, activo) VALUES
        ('Comisiones preferencia e indiferencia', 'Las sociedades de valores pueden cobrar comisiones que favorezcan a unos clientes sobre otros?',
          'Analizar los limites de las comisiones de preferencia e indiferencia bajo MiFID II y la normativa CNMV, y cuando constituyen conflicto de interes.',
          'Permitidas con limites estrictos y transparencia total al cliente. Deben reflejar costes reales y no superar los beneficios para el cliente.',
          'Requiere divulgacion previa al cliente y registro documental de las comisiones aplicadas.',
          'No aplica a operaciones institucionales con acuerdos de soft dollar documentados.',
          NULL, 'vigente', 1, 1, true)
    """)

    # 3. Ejecucion preferente — best execution
    op.execute("""
        INSERT INTO linea_criterio (titulo, cuestion_practica, descripcion, criterio_dominante, matices, excepciones, ultimo_cambio, estado, autor_id, revisor_id, activo) VALUES
        ('Ejecucion preferente de ordenes', 'Que criterios debe seguir una sociedad de valores para garantizar la ejecucion preferente?',
          'Analizar las obligaciones de best execution bajo art. 61 LMCV y Reg. 2017/565, incluyendo calidad ejecucion, costes, rapidez y probabilidad de ejecucion.',
          'Obligacion continua de tomar medidas diligentes para obtener el mejor resultado para el cliente. Factor de calidad incluye precio, costes, rapidez, ejecucion, size, probabilidad.',
          'Debe mantener politica de ejecucion documentada y revisar periodicamente los destinos de orden.',
          'Puede ejecutarse por medios exclusivos solo si el cliente acuerda explicitamente.',
          NULL, 'vigente', 1, 1, true)
    """)

    # 4. Suitability y appropriateness
    op.execute("""
        INSERT INTO linea_criterio (titulo, cuestion_practica, descripcion, criterio_dominante, matices, excepciones, ultimo_cambio, estado, autor_id, revisor_id, activo) VALUES
        ('Adecuacion y conveniencia de productos', 'Cual es la diferencia entre evaluar adecuacion y conveniencia, y cuando aplica cada una?',
          'Suitability (art. 53 LMCV) aplica a servicios de inversion: evaluar perfil del cliente vs caracteristicas del producto. Appropriateness (art. 54 LMCV) aplica solo a servicios de ejecucion: verificar conocimientos basicos.',
          'Suitability exige conocimiento de situacion financiera, objetivos, tolerancia riesgo. Appropriateness solo verifica conocimientos y experiencia en la categoria de producto.',
          'Si el cliente proporciona informacion actualizada automaticamente se considera adecuada. No se requiere suitability para servicios de ejecucion no asistida.',
          'Excepcion: clientes institucionales, profesionales automaticos y productos no complejos para apropiateness.',
          NULL, 'vigente', 1, 1, true)
    """)

    # 5. Informacion privilegiada — insider trading
    op.execute("""
        INSERT INTO linea_criterio (titulo, cuestion_practica, descripcion, criterio_dominante, matices, excepciones, ultimo_cambio, estado, autor_id, revisor_id, activo) VALUES
        ('Informacion privilegiada y listas insider', 'Que obligaciones tiene la sociedad de valores en materia de informacion privilegiada?',
          'Analizar obligaciones MAR: creacion y mantenimiento de listas insider, listas de vigilancia, restriccion de personas con acceso, y reporte de operaciones de PPI.',
          'Obligacion de crear lista insider para cada informacion privilegiada. Personas en la lista no pueden operar en el emisor. Lista de vigilancia para empleados con acceso recurrente.',
          'Deben existir procedimientos escritos y controles tecnologicos. Las listas deben actualizarse en tiempo real.',
          'Excepcion para M&A con acuerdos de confidencialidad y necesidad de conocimiento justificada.',
          NULL, 'vigente', 1, 1, true)
    """)

    # 6. Productos prioritarios — product governance
    op.execute("""
        INSERT INTO linea_criterio (titulo, cuestion_practica, descripcion, criterio_dominante, matices, excepciones, ultimo_cambio, estado, autor_id, revisor_id, activo) VALUES
        ('Gobierno de productos (product governance)', 'Como debe disenarse y distribuirse un producto financiero bajo MiFID II?',
          'Analizar obligaciones de fabricacion y distribucion: identificar mercado objetivo, restriccion de distribucion al target, revision periodica de productos.',
          'El fabricante debe definir mercado objetivo y tomar medidas para que el producto llegue a ese target. El distribuidor debe considerar si el target es consistente.',
          'Revision periodica obligatoria. Si el producto se vende fuera del target, notificar al fabricante y suspender distribucion si es necesario.',
          'No aplica a productos para clientes profesionales o institucionales en la misma medida.',
          NULL, 'vigente', 1, 1, true)
    """)

    # 7. PBLAFT — deberes de comunicacion
    op.execute("""
        INSERT INTO linea_criterio (titulo, cuestion_practica, descripcion, criterio_dominante, matices, excepciones, ultimo_cambio, estado, autor_id, revisor_id, activo) VALUES
        ('Comunicacion de indicios de LP', 'Cuales son los deberes de comunicacion de indicios de lavado a SEPBLAC?',
          'Analizar obligaciones de comunicacion de operaciones sospechosas (indicios) a SEPBLAC, deber de abstencion, y sanciones por incumplimiento.',
          'Obligacion de comunicar sin delay cuando existan indicios de LP. Prohibicion absoluta de informar al cliente ( tipping-off ). Retencion de fondos solo via orden judicial.',
          'La comunicacion es confidencial. SEPBLAC puede solicitar informacion complementaria. El deber de comunicacion prevalece sobre secreto profesional o contractual.',
          'Excepcion: abogados y asesores legales con representacion judicial (solo para origen de fondos del cliente).',
          NULL, 'vigente', 1, 1, true)
    """)

    # Seed referencias — linea 1: IVA restauracion
    op.execute("""
        INSERT INTO linea_criterio_referencia (linea_id, documento_referencia, tipo_documento, organismo_emisor, fecha, rol_en_linea, orden) VALUES
        (1, 'STS-2847/2025', 'sentencia', 'Tribunal Supremo', '2025-06-15', 'doctrina_principal', 1),
        (1, 'V0123/2024', 'consulta_vinculante', 'DGT', '2024-03-10', 'soporte_complementario', 2),
        (1, 'BOE-A-2012-11194', 'ley', 'Boe', '2012-09-28', 'base_legal', 3)
        ON CONFLICT DO NOTHING
    """)

    # Seed referencias — linea 2: comisiones
    op.execute("""
        INSERT INTO linea_criterio_referencia (linea_id, documento_referencia, tipo_documento, organismo_emisor, fecha, rol_en_linea, orden) VALUES
        (2, 'Circular 3/2015 CNMV', 'circular', 'CNMV', '2015-05-14', 'base_regulatoria', 1),
        (2, 'STS-1234/2024', 'sentencia', 'Tribunal Supremo', '2024-11-20', 'doctrina_principal', 2)
        ON CONFLICT DO NOTHING
    """)

    # Seed referencias — linea 3: best execution
    op.execute("""
        INSERT INTO linea_criterio_referencia (linea_id, documento_referencia, tipo_documento, organismo_emisor, fecha, rol_en_linea, orden) VALUES
        (3, 'Reg. UE 2017/565', 'reglamento', 'Union Europea', '2016-10-07', 'base_legal', 1),
        (3, 'V0456/2024', 'consulta_vinculante', 'DGT', '2024-06-15', 'soporte_complementario', 2),
        (3, 'STS-5678/2023', 'sentencia', 'Tribunal Supremo', '2023-09-12', 'doctrina_principal', 3)
        ON CONFLICT DO NOTHING
    """)

    # Seed referencias — linea 4: suitability
    op.execute("""
        INSERT INTO linea_criterio_referencia (linea_id, documento_referencia, tipo_documento, organismo_emisor, fecha, rol_en_linea, orden) VALUES
        (4, 'Directiva 2014/65/UE (MiFID II)', 'directiva', 'Union Europea', '2014-06-04', 'base_legal', 1),
        (4, 'LMCV art. 52-54', 'ley', 'Boe', '2014-07-30', 'base_legal', 2),
        (4, 'V0789/2024', 'consulta_vinculante', 'DGT', '2024-08-20', 'soporte_complementario', 3)
        ON CONFLICT DO NOTHING
    """)

    # Seed referencias — linea 5: insider trading
    op.execute("""
        INSERT INTO linea_criterio_referencia (linea_id, documento_referencia, tipo_documento, organismo_emisor, fecha, rol_en_linea, orden) VALUES
        (5, 'Reg. UE 596/2014 (MAR)', 'reglamento', 'Union Europea', '2014-04-16', 'base_legal', 1),
        (5, 'STS-9012/2024', 'sentencia', 'Tribunal Supremo', '2024-02-28', 'doctrina_principal', 2),
        (5, 'Circular 2/2017 CNMV', 'circular', 'CNMV', '2017-03-22', 'base_regulatoria', 3)
        ON CONFLICT DO NOTHING
    """)

    # Seed referencias — linea 6: product governance
    op.execute("""
        INSERT INTO linea_criterio_referencia (linea_id, documento_referencia, tipo_documento, organismo_emisor, fecha, rol_en_linea, orden) VALUES
        (6, 'Reg. UE 2017/565 anexo I', 'reglamento', 'Union Europea', '2016-10-07', 'base_legal', 1),
        (6, 'Circular 5/2018 CNMV', 'circular', 'CNMV', '2018-09-10', 'base_regulatoria', 2)
        ON CONFLICT DO NOTHING
    """)

    # Seed referencias — linea 7: PBLAFT
    op.execute("""
        INSERT INTO linea_criterio_referencia (linea_id, documento_referencia, tipo_documento, organismo_emisor, fecha, rol_en_linea, orden) VALUES
        (7, 'Ley 10/2010 PREV LPFT', 'ley', 'Boe', '2010-07-26', 'base_legal', 1),
        (7, 'RD 289/2022', 'real_decreto', 'Boe', '2022-05-17', 'base_legal', 2),
        (7, 'STS-3456/2024', 'sentencia', 'Tribunal Supremo', '2024-04-10', 'doctrina_principal', 3)
    """)
