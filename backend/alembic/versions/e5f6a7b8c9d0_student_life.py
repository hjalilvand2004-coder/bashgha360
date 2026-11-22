"""v1.5 پایلوت زندگی دانشجویی: جداول چهار وعدهٔ محصول —
peer_activities/participants/reports، opportunities/regs، portfolio_bundles/enrollments،
student_proposals/proposal_votes. هیچ کلید خارجی به دفترکل امتیاز وجود ندارد.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-22
"""
import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "peer_activities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("university_id", sa.String(36), nullable=False),
        sa.Column("host_student_ref_id", sa.String(36), nullable=False),
        sa.Column("title_fa", sa.String(200), nullable=False),
        sa.Column("activity_kind", sa.String(20), nullable=False, server_default="other"),
        sa.Column("time_label_fa", sa.String(100), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location_fa", sa.String(200), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("trial_ok", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("interest_tags", sa.String(200), nullable=False, server_default=""),
        sa.Column("state", sa.String(12), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_peer_activities_university_id", "peer_activities", ["university_id"])
    op.create_index("ix_peer_activities_host", "peer_activities", ["host_student_ref_id"])

    op.create_table(
        "peer_participants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("university_id", sa.String(36), nullable=False),
        sa.Column("activity_id", sa.String(36), sa.ForeignKey("peer_activities.id"), nullable=False),
        sa.Column("student_ref_id", sa.String(36), nullable=False),
        sa.Column("mode", sa.String(10), nullable=False, server_default="trial"),
        sa.Column("state", sa.String(10), nullable=False, server_default="joined"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("activity_id", "student_ref_id", name="uq_peer_participant"),
    )
    op.create_index("ix_peer_participants_university_id", "peer_participants", ["university_id"])

    op.create_table(
        "peer_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("university_id", sa.String(36), nullable=False),
        sa.Column("activity_id", sa.String(36), sa.ForeignKey("peer_activities.id"), nullable=False),
        sa.Column("reporter_student_ref_id", sa.String(36), nullable=False),
        sa.Column("reason_fa", sa.Text(), nullable=False),
        sa.Column("state", sa.String(10), nullable=False, server_default="open"),
        sa.Column("resolution_note_fa", sa.String(400), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_peer_reports_university_id", "peer_reports", ["university_id"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("university_id", sa.String(36), nullable=False),
        sa.Column("title_fa", sa.String(200), nullable=False),
        sa.Column("what_fa", sa.Text(), nullable=False, server_default=""),
        sa.Column("location_fa", sa.String(200), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("cost_label_fa", sa.String(60), nullable=False, server_default="رایگان"),
        sa.Column("is_free", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("prereq_fa", sa.String(200), nullable=False, server_default="هیچ"),
        sa.Column("solo_friendly", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("kind", sa.String(20), nullable=False, server_default="other"),
        sa.Column("state", sa.String(12), nullable=False, server_default="published"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_opportunities_university_id", "opportunities", ["university_id"])

    op.create_table(
        "opportunity_regs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("university_id", sa.String(36), nullable=False),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("student_ref_id", sa.String(36), nullable=False),
        sa.Column("position_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("state", sa.String(12), nullable=False, server_default="registered"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("opportunity_id", "student_ref_id", name="uq_opportunity_reg"),
    )
    op.create_index("ix_opportunity_regs_university_id", "opportunity_regs", ["university_id"])

    op.create_table(
        "portfolio_bundles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("university_id", sa.String(36), nullable=False),
        sa.Column("title_fa", sa.String(200), nullable=False),
        sa.Column("output_fa", sa.String(300), nullable=False),
        sa.Column("tools_fa", sa.String(400), nullable=False, server_default=""),
        sa.Column("guide_fa", sa.String(400), nullable=False, server_default=""),
        sa.Column("feedback_note_fa", sa.String(400), nullable=False, server_default=""),
        sa.Column("steps_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("estimated_hours", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("newcomer_seats", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("state", sa.String(12), nullable=False, server_default="published"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_portfolio_bundles_university_id", "portfolio_bundles", ["university_id"])

    op.create_table(
        "bundle_enrollments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("university_id", sa.String(36), nullable=False),
        sa.Column("bundle_id", sa.String(36), sa.ForeignKey("portfolio_bundles.id"), nullable=False),
        sa.Column("student_ref_id", sa.String(36), nullable=False),
        sa.Column("is_newcomer_seat", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("steps_done_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("output_url", sa.String(400), nullable=True),
        sa.Column("output_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("state", sa.String(10), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("bundle_id", "student_ref_id", name="uq_bundle_enrollment"),
    )
    op.create_index("ix_bundle_enrollments_university_id", "bundle_enrollments", ["university_id"])

    op.create_table(
        "student_proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("university_id", sa.String(36), nullable=False),
        sa.Column("author_student_ref_id", sa.String(36), nullable=False),
        sa.Column("title_fa", sa.String(200), nullable=False),
        sa.Column("body_fa", sa.Text(), nullable=False, server_default=""),
        sa.Column("support_fa", sa.String(300), nullable=False, server_default=""),
        sa.Column("kind", sa.String(20), nullable=False, server_default="program"),
        sa.Column("state", sa.String(14), nullable=False, server_default="received"),
        sa.Column("decision_note_fa", sa.String(400), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_student_proposals_university_id", "student_proposals", ["university_id"])

    op.create_table(
        "proposal_votes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("university_id", sa.String(36), nullable=False),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("student_proposals.id"), nullable=False),
        sa.Column("student_ref_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("proposal_id", "student_ref_id", name="uq_proposal_vote"),
    )
    op.create_index("ix_proposal_votes_university_id", "proposal_votes", ["university_id"])


def downgrade() -> None:
    for t in ("proposal_votes", "student_proposals", "bundle_enrollments", "portfolio_bundles",
              "opportunity_regs", "opportunities", "peer_reports", "peer_participants", "peer_activities"):
        op.drop_table(t)
