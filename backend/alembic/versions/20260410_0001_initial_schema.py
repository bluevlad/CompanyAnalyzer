"""initial schema with monitoring & newsletter tables

Revision ID: 20260410_0001
Revises:
Create Date: 2026-04-10

기존 운영 DB(companies/analyses/...)는 이미 SQLAlchemy create_all()로 생성된
상태이므로 이 마이그레이션은 신규 테이블만 생성한다. 신규 환경에서는 기존
테이블도 생성되어야 하므로 IF NOT EXISTS 패턴으로 모두 idempotent하게 작성.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260410_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    # ─── 기존 테이블 (이미 존재하면 skip) ────────────────────────────────
    if not _has_table(bind, "companies"):
        op.create_table(
            "companies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("url", sa.String(500), nullable=False),
            sa.Column("industry", sa.String(100), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
        )
        op.create_index("ix_companies_id", "companies", ["id"])

    if not _has_table(bind, "analyses"):
        op.create_table(
            "analyses",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("crawled_pages", sa.Integer(), server_default="0"),
            sa.Column("total_tokens", sa.Integer(), server_default="0"),
            sa.Column("analysis_duration", sa.Float(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("email_sent", sa.Boolean(), server_default=sa.false()),
            sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("email_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_analyses_id", "analyses", ["id"])

    if not _has_table(bind, "analysis_results"):
        op.create_table(
            "analysis_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "analysis_id", sa.Integer(), sa.ForeignKey("analyses.id"), nullable=False
            ),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("content", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_analysis_results_id", "analysis_results", ["id"])

    if not _has_table(bind, "crawled_pages"):
        op.create_table(
            "crawled_pages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "analysis_id", sa.Integer(), sa.ForeignKey("analyses.id"), nullable=False
            ),
            sa.Column("url", sa.String(500), nullable=False),
            sa.Column("title", sa.String(300), nullable=True),
            sa.Column("content_text", sa.Text(), nullable=True),
            sa.Column("content_length", sa.Integer(), server_default="0"),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("crawled_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_crawled_pages_id", "crawled_pages", ["id"])

    # ─── 신규 모니터링 테이블 ────────────────────────────────────────────
    op.create_table(
        "monitoring_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("news_sources", sa.JSON(), nullable=False),
        sa.Column("schedule_daily", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("schedule_weekly", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("schedule_monthly", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("recipient_emails", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_monitoring_targets_id", "monitoring_targets", ["id"])

    op.create_table(
        "mentions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "target_id",
            sa.Integer(),
            sa.ForeignKey("monitoring_targets.id"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_name", sa.String(100), nullable=True),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("author", sa.String(200), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("sentiment", sa.String(10), nullable=True),
        sa.Column("importance_score", sa.Integer(), nullable=True),
        sa.Column("matched_keywords", sa.JSON(), nullable=True),
        sa.Column("one_line_summary", sa.String(500), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_mentions_id", "mentions", ["id"])
    op.create_index("ix_mentions_target_id", "mentions", ["target_id"])
    op.create_index("ix_mentions_content_hash", "mentions", ["content_hash"])

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "mention_id",
            sa.Integer(),
            sa.ForeignKey("mentions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("chroma_id", sa.String(100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rag_chunks_id", "rag_chunks", ["id"])

    op.create_table(
        "newsletters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "target_id",
            sa.Integer(),
            sa.ForeignKey("monitoring_targets.id"),
            nullable=False,
        ),
        sa.Column("period_type", sa.String(10), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("subject", sa.String(300), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.JSON(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_to", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "target_id", "period_type", "period_start", name="uq_newsletter_period"
        ),
    )
    op.create_index("ix_newsletters_id", "newsletters", ["id"])
    op.create_index("ix_newsletters_target_id", "newsletters", ["target_id"])

    op.create_table(
        "newsletter_mentions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "newsletter_id",
            sa.Integer(),
            sa.ForeignKey("newsletters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mention_id", sa.Integer(), sa.ForeignKey("mentions.id"), nullable=False
        ),
        sa.Column("rank", sa.Integer(), nullable=True),
    )
    op.create_index("ix_newsletter_mentions_id", "newsletter_mentions", ["id"])


def downgrade() -> None:
    op.drop_table("newsletter_mentions")
    op.drop_table("newsletters")
    op.drop_table("rag_chunks")
    op.drop_table("mentions")
    op.drop_table("monitoring_targets")
    # 기존 테이블은 downgrade에서 삭제하지 않음 (운영 데이터 보호)
