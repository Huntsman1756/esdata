"""Revoke EXECUTE on user-defined functions from PUBLIC.

S-TIER: AGENTS.md regla 8 — Revocar execute a public/anon tras CREATE FUNCTION.
- Todas las funciones definidas por el usuario pierden EXECUTE de PUBLIC
- Excepciones: funciones de extensiones (pgvector, etc.)
- service_role y esdata mantienen EXECUTE explicito

# Revision ID: 20260429_0002_revoke_function_execute
# Revises: 20260429_0001_rls_zero_policy
# Create Date: 2026-04-29 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260429_0002_revoke_function_execute"
down_revision = "20260429_0001_rls_zero_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Revocar EXECUTE de PUBLIC en todas las funciones definidas por el usuario
    #    Excluir funciones de extensiones (pg_catalog, information_schema, pg_toast)
    op.execute(sa.text("""
        DO $$
        DECLARE
            f RECORD;
        BEGIN
            FOR f IN
                SELECT p.oid, p.proname, n.nspname
                FROM pg_proc p
                JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                  AND n.nspname !~ '^pg_'
                  AND p.prokind = 'f'
            LOOP
                -- Revocar EXECUTE de PUBLIC
                EXECUTE format('REVOKE EXECUTE ON FUNCTION %I.%I(%s) FROM PUBLIC',
                    f.nspname, f.proname,
                    (SELECT pg_get_function_identity_arguments(f.oid))
                );

                -- Otorgar EXECUTE a service_role (para acceso backend)
                EXECUTE format('GRANT EXECUTE ON FUNCTION %I.%I(%s) TO service_role',
                    f.nspname, f.proname,
                    (SELECT pg_get_function_identity_arguments(f.oid))
                );

                -- Otorgar EXECUTE a esdata (rol de app)
                EXECUTE format('GRANT EXECUTE ON FUNCTION %I.%I(%s) TO esdata',
                    f.nspname, f.proname,
                    (SELECT pg_get_function_identity_arguments(f.oid))
                );
            END LOOP;
        END $$
    """))

    # 2. Verificar: mostrar funciones que quedaron sin EXECUTE publico
    op.execute(sa.text("""
        DO $$
        DECLARE
            count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO count
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
              AND n.nspname !~ '^pg_'
              AND p.prokind = 'f'
              AND NOT EXISTS (
                  SELECT 1 FROM pg_auth_members am
                  JOIN pg_roles r ON am.member = r.oid
                  WHERE am.roleid = (
                      SELECT oid FROM pg_roles WHERE rolname = 'public'
                  )
                    AND am.member != (
                        SELECT oid FROM pg_roles WHERE rolname = 'postgres'
                    )
                    AND p.oid = (
                        SELECT oid FROM pg_proc
                        WHERE proname = p.proname
                          AND pronamespace = p.pronamespace
                          AND pg_get_function_identity_arguments(oid) = pg_get_function_identity_arguments(p.oid)
                    )
              );
            RAISE NOTICE 'Functions with EXECUTE revoked from PUBLIC: %', count;
        END $$
    """))


def downgrade() -> None:
    # Restaurar EXECUTE a PUBLIC en todas las funciones definidas por el usuario
    op.execute(sa.text("""
        DO $$
        DECLARE
            f RECORD;
        BEGIN
            FOR f IN
                SELECT p.oid, p.proname, n.nspname
                FROM pg_proc p
                JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                  AND n.nspname !~ '^pg_'
                  AND p.prokind = 'f'
            LOOP
                -- Restaurar EXECUTE a PUBLIC (por defecto en Postgres)
                EXECUTE format('GRANT EXECUTE ON FUNCTION %I.%I(%s) TO PUBLIC',
                    f.nspname, f.proname,
                    (SELECT pg_get_function_identity_arguments(f.oid))
                );
            END LOOP;
        END $$
    """))
