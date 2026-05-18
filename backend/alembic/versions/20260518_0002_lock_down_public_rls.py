"""Add explicit deny-all RLS policies for public schema tables."""

from __future__ import annotations

from alembic import op


revision = "20260518_0002"
down_revision = "20260518_0001"
branch_labels = None
depends_on = None


POLICY_TABLES = (
    "users",
    "sessions",
    "posts",
    "post_media",
    "comments",
    "likes",
    "favorites",
)


def upgrade() -> None:
    for table_name in POLICY_TABLES:
        op.execute(
            f"""
            CREATE POLICY deny_all_{table_name}_api_access
            ON public.{table_name}
            AS RESTRICTIVE
            FOR ALL
            TO anon, authenticated
            USING (false)
            WITH CHECK (false)
            """
        )


def downgrade() -> None:
    for table_name in POLICY_TABLES:
        op.execute(f"DROP POLICY IF EXISTS deny_all_{table_name}_api_access ON public.{table_name}")
