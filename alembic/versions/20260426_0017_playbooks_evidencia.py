"""add playbook_operativo, playbook_step and evidencia_control tables

Creates operational playbook tables for Fase 19
(Playbooks operativos y evidencia de cumplimiento):

- playbook_operativo: operational procedures linked to regulatory obligations
- playbook_step: individual steps within a playbook
- evidencia_control: required evidence and proof items for audit trail

Revision ID: 20260426_0017_playbooks_evidencia
Revises: 20260426_0016_editorial_internal
Create Date: 2026-04-26 00:00:00

"""

from alembic import op
import sqlalchemy as sa

revision = "20260426_0017_playbooks_evidencia"
down_revision = "20260426_0016_editorial_internal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "playbook_operativo",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("codigo", sa.Text(), nullable=False, unique=True,
                   comment="Codigo unico del playbook (ej: PLAYBOOK-CNMV-IR)"),
        sa.Column("nombre", sa.Text(), nullable=False,
                   comment="Nombre descriptivo del procedimiento operativo"),
        sa.Column("obligacion_codigo", sa.Text(), nullable=True,
                   comment="FK a obligacion_regulatoria.codigo"),
        sa.Column("descripcion", sa.Text(), nullable=True,
                   comment="Descripcion operativa del playbook completo"),
        sa.Column("frecuencia", sa.Text(), nullable=True,
                   comment="frecuencia del procedimiento (mensual, trimestral, anual, eventual)"),
        sa.Column("owner_rol", sa.Text(), nullable=True,
                   comment="Rol responsable de ejecutar el playbook"),
        sa.Column("owner_id", sa.Text(), nullable=True,
                   comment="Identificador del responsable asignado"),
        sa.Column("sistema_apoyo", sa.Text(), nullable=True,
                   comment="Sistema o herramienta de apoyo al procedimiento"),
        sa.Column("errores_frecuentes", sa.Text(), nullable=True,
                   comment="Errores comunes y como evitarlos"),
        sa.Column("estado", sa.Text(), nullable=False, server_default=sa.text("'activo'::text"),
                   comment="activo, inactivo, revisar, obsoleto"),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("version_anterior_id", sa.dialects.postgresql.UUID(), nullable=True,
                   comment="FK a playbook_operativo.id de version anterior"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["obligacion_codigo"], ["obligacion_regulatoria.codigo"]),
        sa.ForeignKeyConstraint(["version_anterior_id"], ["playbook_operativo.id"]),
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_playbook_operativo_obligacion
            ON playbook_operativo(obligacion_codigo)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_playbook_operativo_estado
            ON playbook_operativo(estado)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_playbook_operativo_owner
            ON playbook_operativo(owner_rol)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_playbook_operativo_frecuencia
            ON playbook_operativo(frecuencia)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_playbook_operativo_texto_trgm
            ON playbook_operativo USING gin (nombre gin_trgm_ops)
        """
    )

    op.create_table(
        "playbook_step",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("playbook_id", sa.dialects.postgresql.UUID(), nullable=False,
                   comment="FK a playbook_operativo.id"),
        sa.Column("orden", sa.Integer(), nullable=False,
                   comment="Orden numerico del paso dentro del playbook"),
        sa.Column("titulo", sa.Text(), nullable=False,
                   comment="Titulo corto del paso"),
        sa.Column("descripcion", sa.Text(), nullable=True,
                   comment="Descripcion detallada del paso"),
        sa.Column("tipo_paso", sa.Text(), nullable=False, server_default=sa.text("'accion'::text"),
                   comment="tipo de paso (accion, revision, aprobacion, captura, verificacion, otro)"),
        sa.Column("responsable_rol", sa.Text(), nullable=True,
                   comment="Rol responsable de ejecutar este paso"),
        sa.Column("input_requerido", sa.Text(), nullable=True,
                   comment="Inputs o datos necesarios para ejecutar el paso"),
        sa.Column("output_esperado", sa.Text(), nullable=True,
                   comment="Output o deliverable esperado del paso"),
        sa.Column("prerrequisito_step_id", sa.dialects.postgresql.UUID(), nullable=True,
                   comment="FK a playbook_step.id — paso que debe completarse antes"),
        sa.Column("checklist", sa.Text(), nullable=True, server_default=sa.text("'[]'::text"),
                   comment="Checklist JSON de sub-tareas del paso"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["playbook_id"], ["playbook_operativo.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prerrequisito_step_id"], ["playbook_step.id"]),
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_playbook_step_playbook
            ON playbook_step(playbook_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_playbook_step_orden
            ON playbook_step(playbook_id, orden)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_playbook_step_tipo
            ON playbook_step(tipo_paso)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_playbook_step_responsable
            ON playbook_step(responsable_rol)
        """
    )

    op.create_table(
        "evidencia_control",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("codigo", sa.Text(), nullable=False, unique=True,
                   comment="Codigo unico de evidencia (ej: EVID-CNMV-IR-001)"),
        sa.Column("playbook_id", sa.dialects.postgresql.UUID(), nullable=False,
                   comment="FK a playbook_operativo.id"),
        sa.Column("step_id", sa.dialects.postgresql.UUID(), nullable=True,
                   comment="FK a playbook_step.id — evidencia especifica de un paso"),
        sa.Column("nombre", sa.Text(), nullable=False,
                   comment="Nombre descriptivo de la evidencia requerida"),
        sa.Column("descripcion", sa.Text(), nullable=True,
                   comment="Descripcion de que constituye evidencia valida"),
        sa.Column("tipo_evidencia", sa.Text(), nullable=False, server_default=sa.text("'documento'::text"),
                   comment="tipo de evidencia (documento, log, captura, aprobacion, extracto, reporte, otro)"),
        sa.Column("formato_requerido", sa.Text(), nullable=True,
                   comment="Formato esperado (pdf, xml, json, captura_pantalla, otro)"),
        sa.Column("conservacion_dias", sa.Integer(), nullable=True,
                   comment="Dias minimos de conservacion requeridos"),
        sa.Column("obligatoria", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("estado", sa.Text(), nullable=False, server_default=sa.text("'requerido'::text"),
                   comment="requerido, capturado, verificado, rechazado, exento"),
        sa.Column("capturado_en", sa.Date(), nullable=True,
                   comment="Fecha en que se capturo la evidencia"),
        sa.Column("verificado_por", sa.Text(), nullable=True,
                   comment="Identificador de quien verifico la evidencia"),
        sa.Column("verificado_en", sa.Date(), nullable=True,
                   comment="Fecha de verificacion"),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["playbook_id"], ["playbook_operativo.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["playbook_step.id"]),
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_evidencia_control_playbook
            ON evidencia_control(playbook_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_evidencia_control_step
            ON evidencia_control(step_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_evidencia_control_tipo
            ON evidencia_control(tipo_evidencia)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_evidencia_control_estado
            ON evidencia_control(estado)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_evidencia_control_obligatoria
            ON evidencia_control(obligatoria)
            WHERE obligatoria = true
        """
    )

    # --- Seed: playbook for CNMV-IR-RESERVADA ---
    op.execute(
        """
        INSERT INTO playbook_operativo (
            codigo, nombre, obligacion_codigo, descripcion,
            frecuencia, owner_rol, estado, version
        )
        SELECT
            'PLAYBOOK-CNMV-IR',
            'Preparacion y remision de informacion reservada a la CNMV',
            NULL,
            'Procedimiento operativo para la preparacion, revision y remision de los estados de informacion reservada exigidos por la Circular 9/2008 de la CNMV a las entidades supervisadas.',
            'mensual',
            'compliance',
            'activo',
            1
        WHERE NOT EXISTS (
            SELECT 1 FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'
        )
        """
    )

    # --- Seed: steps for CNMV playbook ---
    op.execute(
        """
        INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, checklist)
        SELECT p.id, 1, 'Recopilar datos contables mensuales',
              'Extraer los datos contables y financieros del mes desde el sistema de contabilidad y tesoreria.',
              'accion', 'contabilidad',
              'Libro mayor, extractos bancarios, registros de tesoreria',
              'Dataset de datos contables del periodo',
              '["Verificar integridad de datos","Conciliar balances","Validar cuentas maestras"]'
        FROM playbook_operativo p WHERE p.codigo = 'PLAYBOOK-CNMV-IR'
        """
    )

    op.execute(
        """
        INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
        SELECT p.id, 2, 'Preparar estados financieros reservados',
              'Elaborar los estados de informacion reservada conforme al formato exigido por la CNMV (balance, cuenta de resultados, notas).',
              'captura', 'contabilidad',
              'Dataset de datos contables del periodo, plantillas CNMV',
              'Estados financieros reservados del periodo',
              (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 1 LIMIT 1),
              '["Formato CNMV vigente","Cruce con estados publicos","Notas a cuentas completas"]'
        FROM playbook_operativo p WHERE p.codigo = 'PLAYBOOK-CNMV-IR'
        """
    )

    op.execute(
        """
        INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
        SELECT p.id, 3, 'Revision de compliance',
              'El responsable de compliance revisa los estados reservados y valida el cumplimiento de la normativa aplicable.',
              'revision', 'compliance',
              'Estados financieros reservados, normativa CNMV vigente',
              'Informe de revision de compliance firmado',
              (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 2 LIMIT 1),
              '["Validar ratios prudenciales","Verificar limites de riesgo","Confirmar cumplimiento normativo"]'
        FROM playbook_operativo p WHERE p.codigo = 'PLAYBOOK-CNMV-IR'
        """
    )

    op.execute(
        """
        INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
        SELECT p.id, 4, 'Aprobacion por direccion',
              'La direccion general aprueba los estados financieros reservados antes de su remision a la CNMV.',
              'aprobacion', 'direccion_general',
              'Estados financieros reservados, informe de compliance',
              'Acta de aprobacion de estados reservados',
              (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 3 LIMIT 1),
              '["Aprobacion formal por escrito","Registro de aprobacion"]'
        FROM playbook_operativo p WHERE p.codigo = 'PLAYBOOK-CNMV-IR'
        """
    )

    op.execute(
        """
        INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
        SELECT p.id, 5, 'Remision a la CNMV',
              'Enviar los estados reservados a la CNMV a traves del canal electronico habilitado dentro del plazo legal (primeros 20 dias del mes siguiente).',
              'accion', 'compliance',
              'Estados aprobados, certificado digital, canal CNMV',
              'Acuse de recibo de la CNMV',
              (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 4 LIMIT 1),
              '["Verificar fecha limite","Confirmar acuse de recibo","Archivar evidencia de envio"]'
        FROM playbook_operativo p WHERE p.codigo = 'PLAYBOOK-CNMV-IR'
        """
    )

    # --- Seed: evidence items for CNMV playbook ---
    op.execute(
        """
        INSERT INTO evidencia_control (
            codigo, playbook_id, nombre, descripcion, tipo_evidencia,
            formato_requerido, conservacion_dias, obligatoria, estado
        )
        SELECT
            'EVID-CNMV-IR-001',
            (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'),
            'Estados financieros reservados del periodo',
            'Estados de informacion reservada (balance, cuenta de resultados, notas) elaborados conforme a la Circular 9/2008 CNMV.',
            'documento',
            'pdf',
            3650,
            true,
            'requerido'
        WHERE NOT EXISTS (SELECT 1 FROM evidencia_control WHERE codigo = 'EVID-CNMV-IR-001')
        """
    )

    op.execute(
        """
        INSERT INTO evidencia_control (
            codigo, playbook_id, step_id, nombre, descripcion, tipo_evidencia,
            formato_requerido, conservacion_dias, obligatoria, estado
        )
        SELECT
            'EVID-CNMV-IR-002',
            (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'),
            (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 3 LIMIT 1),
            'Informe de revision de compliance',
            'Informe del responsable de compliance validando el cumplimiento normativo de los estados reservados.',
            'documento',
            'pdf',
            3650,
            true,
            'requerido'
        WHERE NOT EXISTS (SELECT 1 FROM evidencia_control WHERE codigo = 'EVID-CNMV-IR-002')
        """
    )

    op.execute(
        """
        INSERT INTO evidencia_control (
            codigo, playbook_id, step_id, nombre, descripcion, tipo_evidencia,
            formato_requerido, conservacion_dias, obligatoria, estado
        )
        SELECT
            'EVID-CNMV-IR-003',
            (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'),
            (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 4 LIMIT 1),
            'Acta de aprobacion por direccion',
            'Documento formal de aprobacion de los estados reservados por la direccion general.',
            'aprobacion',
            'pdf',
            3650,
            true,
            'requerido'
        WHERE NOT EXISTS (SELECT 1 FROM evidencia_control WHERE codigo = 'EVID-CNMV-IR-003')
        """
    )

    op.execute(
        """
        INSERT INTO evidencia_control (
            codigo, playbook_id, step_id, nombre, descripcion, tipo_evidencia,
            formato_requerido, conservacion_dias, obligatoria, estado
        )
        SELECT
            'EVID-CNMV-IR-004',
            (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-CNMV-IR'),
            (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-CNMV-IR' AND s.orden = 5 LIMIT 1),
            'Acuse de recibo CNMV',
            'Confirmacion electronica de envio y recepcion por parte de la CNMV.',
            'log',
            'xml',
            3650,
            true,
            'requerido'
        WHERE NOT EXISTS (SELECT 1 FROM evidencia_control WHERE codigo = 'EVID-CNMV-IR-004')
        """
    )

    # --- Seed: playbook for SEPBLAC-INDICIO-M19 ---
    op.execute(
        """
        INSERT INTO playbook_operativo (
            codigo, nombre, obligacion_codigo, descripcion,
            frecuencia, owner_rol, estado, version
        )
        SELECT
            'PLAYBOOK-SEPBLAC-INDICIO',
            'Comunicacion de operativas sospechosas por indicio (Modelo 19 SEPBLAC)',
            NULL,
            'Procedimiento operativo para la deteccion, evaluacion y comunicacion de operativas sospechosas a SEPBLAC mediante el Modelo 19.',
            'eventual',
            'compliance',
            'activo',
            1
        WHERE NOT EXISTS (
            SELECT 1 FROM playbook_operativo WHERE codigo = 'PLAYBOOK-SEPBLAC-INDICIO'
        )
        """
    )

    # --- Seed: steps for SEPBLAC playbook ---
    op.execute(
        """
        INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, checklist)
        SELECT p.id, 1, 'Deteccion del indicio',
              'Identificar un indicio de actividad sospechosa en las operaciones del cliente o contraparte.',
              'accion', 'compliance',
              'Datos de la operacion, perfil del cliente, historial transaccional',
              'Registro interno del indicio detectado',
              '["Describir el hecho","Identificar las partes involucradas","Documentar la fecha y monto"]'
        FROM playbook_operativo p WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO'
        """
    )

    op.execute(
        """
        INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
        SELECT p.id, 2, 'Evaluacion interna',
              'Evaluar si el indicio constituye una operativa sospechosa que debe comunicarse a SEPBLAC.',
              'revision', 'compliance',
              'Registro del indicio, analisis de riesgo del cliente, normativa PBCFT',
              'Informe de evaluacion con conclusion',
              (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO' AND s.orden = 1 LIMIT 1),
              '["Analizar patrones","Verificar historial","Consultar lista de riesgos"]'
        FROM playbook_operativo p WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO'
        """
    )

    op.execute(
        """
        INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
        SELECT p.id, 3, 'Completar Modelo 19',
              'Rellenar el formulario oficial Modelo 19 de comunicacion por indicio con toda la informacion requerida.',
              'captura', 'compliance',
              'Informe de evaluacion, datos del cliente, datos de la operacion, formulario Modelo 19',
              'Modelo 19 completado y revisado',
              (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO' AND s.orden = 2 LIMIT 1),
              '["Datos completos del sujeto","Descripcion detallada del hecho","Documentacion de soporte"]'
        FROM playbook_operativo p WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO'
        """
    )

    op.execute(
        """
        INSERT INTO playbook_step (playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol, input_requerido, output_esperado, prerrequisito_step_id, checklist)
        SELECT p.id, 4, 'Comunicacion a SEPBLAC',
              'Enviar el Modelo 19 a SEPBLAC a traves del canal electronico oficial dentro del plazo de 1 mes desde el hecho.',
              'accion', 'compliance',
              'Modelo 19 completado, certificado digital, canal SEPBLAC',
              'Confirmacion de envio a SEPBLAC',
              (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO' AND s.orden = 3 LIMIT 1),
              '["Verificar certificado digital","Confirmar recepcion","Archivar copia"]'
        FROM playbook_operativo p WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO'
        """
    )

    # --- Seed: evidence items for SEPBLAC playbook ---
    op.execute(
        """
        INSERT INTO evidencia_control (
            codigo, playbook_id, nombre, descripcion, tipo_evidencia,
            formato_requerido, conservacion_dias, obligatoria, estado
        )
        SELECT
            'EVID-SEPBLAC-IND-001',
            (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-SEPBLAC-INDICIO'),
            'Registro interno del indicio detectado',
            'Documento interno que registra los hechos que constituyen el indicio de actividad sospechosa.',
            'documento',
            'pdf',
            5475,
            true,
            'requerido'
        WHERE NOT EXISTS (SELECT 1 FROM evidencia_control WHERE codigo = 'EVID-SEPBLAC-IND-001')
        """
    )

    op.execute(
        """
        INSERT INTO evidencia_control (
            codigo, playbook_id, step_id, nombre, descripcion, tipo_evidencia,
            formato_requerido, conservacion_dias, obligatoria, estado
        )
        SELECT
            'EVID-SEPBLAC-IND-002',
            (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-SEPBLAC-INDICIO'),
            (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO' AND s.orden = 2 LIMIT 1),
            'Informe de evaluacion interna',
            'Informe del responsable de compliance con la evaluacion y conclusion sobre la comunicacion obligatoria.',
            'documento',
            'pdf',
            5475,
            true,
            'requerido'
        WHERE NOT EXISTS (SELECT 1 FROM evidencia_control WHERE codigo = 'EVID-SEPBLAC-IND-002')
        """
    )

    op.execute(
        """
        INSERT INTO evidencia_control (
            codigo, playbook_id, step_id, nombre, descripcion, tipo_evidencia,
            formato_requerido, conservacion_dias, obligatoria, estado
        )
        SELECT
            'EVID-SEPBLAC-IND-003',
            (SELECT id FROM playbook_operativo WHERE codigo = 'PLAYBOOK-SEPBLAC-INDICIO'),
            (SELECT s.id FROM playbook_step s JOIN playbook_operativo p ON p.id = s.playbook_id WHERE p.codigo = 'PLAYBOOK-SEPBLAC-INDICIO' AND s.orden = 4 LIMIT 1),
            'Confirmacion de envio a SEPBLAC',
            'Acuse de recibo o confirmacion electronica del envio del Modelo 19 a SEPBLAC.',
            'log',
            'xml',
            5475,
            true,
            'requerido'
        WHERE NOT EXISTS (SELECT 1 FROM evidencia_control WHERE codigo = 'EVID-SEPBLAC-IND-003')
        """
    )


def downgrade() -> None:
    op.drop_table("evidencia_control")
    op.drop_table("playbook_step")
    op.drop_table("playbook_operativo")
