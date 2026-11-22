"""sso_system_settings: ثبت این سامانه در پورتال ورود یکپارچهٔ دانشجو۳۶۰ (تک‌ردیفی).

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-17
"""
import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

# مقادیر پیش‌فرض هم‌سان با پورتال مرکزی — در seed/سرویس هم اعمال می‌شود
DEFAULT_ROW = sa.table(
    "sso_system_settings",
    sa.column("id", sa.String),
    sa.column("app_key", sa.String),
    sa.column("display_name_fa", sa.String),
    sa.column("entry_url", sa.String),
    sa.column("description_fa", sa.String),
    sa.column("client_id", sa.String),
    sa.column("sort_order", sa.Integer),
    sa.column("icon_emoji", sa.String),
    sa.column("is_active", sa.Boolean),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    op.create_table(
        "sso_system_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("app_key", sa.String(80), nullable=False),
        sa.Column("display_name_fa", sa.String(200), nullable=False),
        sa.Column("entry_url", sa.String(400), nullable=False),
        sa.Column("description_fa", sa.String(300), nullable=False, server_default=""),
        sa.Column("client_id", sa.String(120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("icon_emoji", sa.String(16), nullable=False, server_default="🎓"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("app_key", name="uq_sso_system_settings_app_key"),
        comment="ثبت این سامانه در پورتال ورود یکپارچه (SSO)",
    )
    from datetime import datetime, timezone

    _now = datetime.now(timezone.utc)
    op.bulk_insert(
        DEFAULT_ROW,
        [{
            "id": "11111111-2222-4222-8222-000000000001",
            "app_key": "daneshjooclub",
            "display_name_fa": "باشگاه دانشجو۳۶۰",
            "entry_url": "http://188.212.96.235:8089/api/v1/auth/sso/login",
            "description_fa": "امتیاز، کارت خدمات و امکانات دانشجویی",
            "client_id": "daneshjooclub360",
            "sort_order": 14,
            "icon_emoji": "🥇",
            "is_active": True,
            "created_at": _now,
            "updated_at": _now,
        }],
    )


def downgrade() -> None:
    op.drop_table("sso_system_settings")
