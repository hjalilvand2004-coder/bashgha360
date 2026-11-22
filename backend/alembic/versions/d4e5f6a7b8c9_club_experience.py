"""v1.3 تجربهٔ باشگاه: مأموریت‌های ملموس، گروه علاقه‌ای، نشان داستان‌محور، پاداش تجربه‌ساز +
جدول‌های onboarding_profiles، mission_invites، showcase_stories.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-17
"""
import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- ستون‌های تجربه‌محور روی جداول موجود ----
    op.add_column("missions", sa.Column("mission_kind", sa.String(30), nullable=False, server_default="standard"))
    op.add_column("missions", sa.Column("output_fa", sa.String(300), nullable=False, server_default=""))
    op.add_column("missions", sa.Column("duration_label_fa", sa.String(40), nullable=False, server_default=""))
    op.add_column("missions", sa.Column("team_size_hint", sa.String(40), nullable=False, server_default=""))
    op.add_column("missions", sa.Column("interest_tags", sa.String(200), nullable=False, server_default=""))

    op.add_column("learning_groups", sa.Column("interest_tag", sa.String(60), nullable=False, server_default=""))
    op.add_column("learning_groups", sa.Column("goal_fa", sa.String(300), nullable=False, server_default=""))
    op.add_column("learning_groups", sa.Column("expected_output_fa", sa.String(300), nullable=False, server_default=""))
    op.add_column("learning_groups", sa.Column("duration_label_fa", sa.String(60), nullable=False, server_default=""))

    op.add_column("badge_definitions", sa.Column("story_fa", sa.String(400), nullable=False, server_default=""))
    op.add_column("reward_items", sa.Column("kind", sa.String(20), nullable=False, server_default="physical"))

    # ---- جداول جدید ----
    op.create_table(
        "onboarding_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("university_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("student_ref_id", sa.String(36), nullable=True),
        sa.Column("persona", sa.String(20), nullable=False),
        sa.Column("interests_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("first_mission_id", sa.String(36), nullable=True),
        sa.Column("first_badge_awarded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_onboarding_user"),
        comment="شروع فوری ۱۵ دقیقه‌ای — مسیر انتخابی + علاقه‌ها + اولین دستاورد",
    )
    op.create_index("ix_onboarding_profiles_university_id", "onboarding_profiles", ["university_id"])
    op.create_index("ix_onboarding_profiles_student_ref_id", "onboarding_profiles", ["student_ref_id"])

    op.create_table(
        "mission_invites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("university_id", sa.String(36), nullable=False),
        sa.Column("mission_id", sa.String(36), sa.ForeignKey("missions.id"), nullable=False),
        sa.Column("inviter_student_ref_id", sa.String(36), nullable=False),
        sa.Column("invitee_contact", sa.String(200), nullable=False, server_default=""),
        sa.Column("invite_code", sa.String(24), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("joined_student_ref_id", sa.String(36), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note_fa", sa.String(300), nullable=False,
                  server_default="پاداش این دعوت به مشارکت مشترک شماست، نه تعداد دعوت‌ها."),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("invite_code", name="uq_mission_invite_code"),
        comment="دعوت دوست برای مأموریت مشترک — بدون امتیاز جذب",
    )
    op.create_index("ix_mission_invites_university_id", "mission_invites", ["university_id"])
    op.create_index("ix_mission_invites_mission_id", "mission_invites", ["mission_id"])
    op.create_index("ix_mission_invites_inviter_student_ref_id", "mission_invites", ["inviter_student_ref_id"])

    op.create_table(
        "showcase_stories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("university_id", sa.String(36), nullable=False),
        sa.Column("title_fa", sa.String(200), nullable=False),
        sa.Column("body_fa", sa.Text(), nullable=False, server_default=""),
        sa.Column("kind", sa.String(20), nullable=False, server_default="build"),
        sa.Column("has_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("subject_label_fa", sa.String(200), nullable=False, server_default=""),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("learning_groups.id"), nullable=True),
        sa.Column("mission_id", sa.String(36), sa.ForeignKey("missions.id"), nullable=True),
        sa.Column("state", sa.String(20), nullable=False, server_default="published"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        comment="فضای دستاوردها — روایت‌های کوتاه به‌جای رتبه‌بندی؛ انتشار فقط با رضایت",
    )
    op.create_index("ix_showcase_stories_university_id", "showcase_stories", ["university_id"])


def downgrade() -> None:
    op.drop_table("showcase_stories")
    op.drop_table("mission_invites")
    op.drop_index("ix_onboarding_profiles_student_ref_id", table_name="onboarding_profiles")
    op.drop_index("ix_onboarding_profiles_university_id", table_name="onboarding_profiles")
    op.drop_table("onboarding_profiles")
    op.drop_column("reward_items", "kind")
    op.drop_column("badge_definitions", "story_fa")
    op.drop_column("learning_groups", "duration_label_fa")
    op.drop_column("learning_groups", "expected_output_fa")
    op.drop_column("learning_groups", "goal_fa")
    op.drop_column("learning_groups", "interest_tag")
    op.drop_column("missions", "interest_tags")
    op.drop_column("missions", "team_size_hint")
    op.drop_column("missions", "duration_label_fa")
    op.drop_column("missions", "output_fa")
    op.drop_column("missions", "mission_kind")
