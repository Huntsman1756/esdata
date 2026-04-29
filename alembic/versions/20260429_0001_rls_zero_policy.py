"""Enable RLS on all public tables with zero public policies.

S-TIER: AGENTS.md regla 2 — RLS Zero Policy
- RLS obligatorio en todas las tablas del esquema public
- Sin policies para public/anon/authenticated
- Acceso solo via service_role (backend)

# Revision ID: 20260429_0001_rls_zero_policy
# Revises: 20260428_0051_idd_solvency_models
# Create Date: 2026-04-29 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260429_0001_rls_zero_policy"
down_revision = "20260428_0051_idd_solvency_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Crear rol service_role si no existe
    op.execute(sa.text("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN CREATE ROLE service_role; END IF; END $$"))

    # 2. Otorgar USAGE al schema public a service_role
    op.execute(sa.text("GRANT USAGE ON SCHEMA public TO service_role"))

    # 3. Revocar todos los permisos de PUBLIC en schema public
    op.execute(sa.text("REVOKE ALL ON SCHEMA public FROM PUBLIC"))

    # 4. Para cada tabla en public:
    #    a. Revocar permisos de PUBLIC
    #    b. Habilitar RLS
    #    c. Dar permisos a service_role
    #    d. Crear policy para service_role que permita todo
    #    e. NO crear ninguna policy para public/anon/authenticated

    # Tablas a excluir (extensiones, alembic_version es una tabla de metadata)
    # Todas las demas tablas en public reciben RLS

    op.execute(sa.text("""
        DO $$
        DECLARE
            t RECORD;
        BEGIN
            FOR t IN
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
            LOOP
                -- Revocar todo de PUBLIC en esta tabla
                EXECUTE format('REVOKE ALL ON TABLE %I FROM PUBLIC', t.tablename);

                -- Habilitar RLS
                EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t.tablename);

                -- Forzar RLS incluso para dueños (no afecta a service_role vs esdata,
                -- pero sigue el principio de defense in depth)
                -- NOT FORCE para que service_role con GRANT pueda acceder

                -- Otorgar permisos a service_role
                EXECUTE format('GRANT ALL ON TABLE %I TO service_role', t.tablename);

                -- Crear policy para service_role (lectura + escritura)
                EXECUTE format(
                    'CREATE POLICY service_role_all ON %I FOR ALL TO service_role USING (true) WITH CHECK (true)',
                    t.tablename
                );
            END LOOP;
        END $$
    """))

    # 5. Dar permisos de USAGE a esdata (el rol de app actual)
    op.execute(sa.text("GRANT USAGE ON SCHEMA public TO esdata"))
    op.execute(sa.text("""
        DO $$
        DECLARE
            t RECORD;
        BEGIN
            FOR t IN
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
            LOOP
                EXECUTE format('GRANT ALL ON TABLE %I TO esdata', t.tablename);
                -- esdata tambien necesita la policy
                EXECUTE format(
                    'CREATE POLICY esdata_all ON %I FOR ALL TO esdata USING (true) WITH CHECK (true)',
                    t.tablename
                );
            END LOOP;
        END $$
    """))


def downgrade() -> None:
    # Revocar RLS de todas las tablas y eliminar policies
    op.execute(sa.text("""
        DO $$
        DECLARE
            t RECORD;
        BEGIN
            FOR t IN
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
            LOOP
                -- Eliminar policies
                EXECUTE format('DROP POLICY IF EXISTS service_role_all ON %I', t.tablename);
                EXECUTE format('DROP POLICY IF EXISTS esdata_all ON %I', t.tablename);

                -- Deshabilitar RLS
                EXECUTE format('ALTER TABLE %I DISABLE ROW LEVEL SECURITY', t.tablename);

                -- Devolver permisos a PUBLIC
                EXECUTE format('GRANT ALL ON TABLE %I TO PUBLIC', t.tablename);
            END LOOP;
        END $$
    """))

    # Revocar permisos de service_role
    op.execute(sa.text("REVOKE ALL ON SCHEMA public FROM service_role"))
    op.execute(sa.text("DROP ROLE IF EXISTS service_role"))
