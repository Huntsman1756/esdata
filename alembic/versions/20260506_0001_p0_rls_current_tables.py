"""P0 RLS current tables hardening.

Revision ID: 20260506_0001_p0_rls_current_tables
Revises: 20260501_0054_aeat_modelo_recurso
Create Date: 2026-05-06 00:01:00
"""

from alembic import op

revision = "20260506_0001_p0_rls_current_tables"
down_revision = "20260501_0054_aeat_modelo_recurso"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS source_freshness_snapshot (
            id BIGSERIAL PRIMARY KEY,
            snapshot_id TEXT NOT NULL UNIQUE,
            source_id TEXT NOT NULL,
            snapshot_version TEXT NOT NULL,
            snapshot_at TEXT NOT NULL,
            last_success_at TEXT,
            last_status TEXT NOT NULL,
            stale BOOLEAN NOT NULL DEFAULT true,
            cadencia TEXT NOT NULL,
            modo_deteccion_cambios TEXT NOT NULL,
            manifest_hash TEXT NOT NULL DEFAULT '',
            payload JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_source_snapshot_source
        ON source_freshness_snapshot(source_id, snapshot_at)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_source_snapshot_version
        ON source_freshness_snapshot(snapshot_version)
        """
    )

    op.execute("GRANT USAGE ON SCHEMA public TO service_role")
    op.execute("GRANT USAGE ON SCHEMA public TO esdata")
    op.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")

    op.execute(
        """
        DO $$
        DECLARE
            t RECORD;
        BEGIN
            FOR t IN
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename <> 'alembic_version'
            LOOP
                EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC', t.tablename);
                EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tablename);
                EXECUTE format('GRANT ALL ON TABLE public.%I TO service_role', t.tablename);
                EXECUTE format('GRANT ALL ON TABLE public.%I TO esdata', t.tablename);

                EXECUTE format('DROP POLICY IF EXISTS service_role_all ON public.%I', t.tablename);
                EXECUTE format('DROP POLICY IF EXISTS esdata_all ON public.%I', t.tablename);

                EXECUTE format(
                    'CREATE POLICY service_role_all ON public.%I '
                    'FOR ALL TO service_role USING (true) WITH CHECK (true)',
                    t.tablename
                );
                EXECUTE format(
                    'CREATE POLICY esdata_all ON public.%I FOR ALL TO esdata USING (true) WITH CHECK (true)',
                    t.tablename
                );
            END LOOP;
        END $$
        """
    )

    # Static safety marker: modelo_recurso was added after the original RLS migration.
    op.execute("ALTER TABLE public.modelo_recurso ENABLE ROW LEVEL SECURITY")

    op.execute(
        """
        DO $$
        DECLARE
            p RECORD;
        BEGIN
            SELECT schemaname, tablename, policyname, roles
            INTO p
            FROM pg_policies
            WHERE schemaname = 'public'
              AND tablename <> 'alembic_version'
              AND roles && ARRAY['public', 'anon', 'authenticated']::name[]
            LIMIT 1;

            IF FOUND THEN
                RAISE EXCEPTION 'Forbidden public/anon/authenticated policy %.%: % roles=%',
                    p.schemaname, p.tablename, p.policyname, p.roles;
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    # Intentional no-op: this migration enforces S-TIER RLS zero-policy over all
    # current public tables. Reversing it could leave RLS enabled without usable
    # service_role/esdata policies and lock out the API runtime.
    pass
