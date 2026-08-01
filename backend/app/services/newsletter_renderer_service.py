"""Newsletter 레코드를 HTML로 렌더링하고 이메일로 발송한다.

PR#4 범위에서는 daily 템플릿만 구현. weekly/monthly는 PR#6에서 추가.
"""
from __future__ import annotations

import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.database.models import (
    Mention,
    MonitoringTarget,
    Newsletter,
    NewsletterMention,
)

logger = logging.getLogger(__name__)
settings = get_settings()

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

TEMPLATE_BY_PERIOD = {
    "daily": "briefing_daily.html",
    "weekly": "briefing_weekly.html",   # PR#6
    "monthly": "briefing_monthly.html", # PR#6
}


class NewsletterRendererService:
    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    async def render(
        self, session: AsyncSession, newsletter_id: int
    ) -> Optional[str]:
        """Newsletter id로 HTML을 만들고 newsletter.html_content에 저장."""
        result = await session.execute(
            select(Newsletter)
            .options(selectinload(Newsletter.target).selectinload(MonitoringTarget.company))
            .where(Newsletter.id == newsletter_id)
        )
        newsletter = result.scalar_one_or_none()
        if newsletter is None:
            logger.warning("newsletter %s not found", newsletter_id)
            return None

        template_name = TEMPLATE_BY_PERIOD.get(newsletter.period_type)
        if template_name is None:
            logger.error("no template for period=%s", newsletter.period_type)
            return None

        # 인용된 mention 조회 (rank 순)
        link_result = await session.execute(
            select(NewsletterMention, Mention)
            .join(Mention, Mention.id == NewsletterMention.mention_id)
            .where(NewsletterMention.newsletter_id == newsletter.id)
            .order_by(NewsletterMention.rank.asc().nullslast())
        )
        mentions = []
        for _link, m in link_result.all():
            mentions.append(
                {
                    "title": m.title,
                    "url": m.url,
                    "source_name": m.source_name,
                    "published_at": (
                        m.published_at.strftime("%Y-%m-%d %H:%M") if m.published_at else ""
                    ),
                    "sentiment": m.sentiment,
                    "importance_score": m.importance_score,
                }
            )

        period_label = (
            f"{newsletter.period_start.strftime('%Y-%m-%d')} ~ "
            f"{newsletter.period_end.strftime('%Y-%m-%d')}"
        )
        company_name = (
            newsletter.target.company.name if newsletter.target and newsletter.target.company else "(unknown)"
        )

        try:
            template = self.env.get_template(template_name)
        except Exception as exc:
            logger.error("template load failed: %s", exc)
            return None

        html = template.render(
            company_name=company_name,
            period_label=period_label,
            mention_count=len(mentions),
            ai=newsletter.ai_summary or {},
            mentions=mentions,
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        )

        newsletter.html_content = html
        await session.commit()
        return html

    async def send(
        self, session: AsyncSession, newsletter_id: int
    ) -> dict:
        """렌더 후 SMTP로 발송. Newsletter.sent_at, sent_to 갱신."""
        if not settings.SMTP_HOST:
            return {"success": False, "error": "SMTP not configured"}

        html = await self.render(session, newsletter_id)
        if html is None:
            return {"success": False, "error": "render failed"}

        result = await session.execute(
            select(Newsletter)
            .options(selectinload(Newsletter.target))
            .where(Newsletter.id == newsletter_id)
        )
        newsletter = result.scalar_one_or_none()
        if newsletter is None:
            return {"success": False, "error": "not found"}

        recipients = (newsletter.target.recipient_emails or []) if newsletter.target else []
        if not recipients:
            return {"success": False, "error": "no recipients"}

        msg = MIMEMultipart("alternative")
        msg["Subject"] = newsletter.subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(self._plain_text_fallback(newsletter), "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER or None,
                password=settings.SMTP_PASSWORD or None,
                use_tls=settings.SMTP_USE_TLS,
            )
        except Exception as exc:
            logger.error("smtp send failed: %s", exc)
            newsletter.error_message = str(exc)
            await session.commit()
            return {"success": False, "error": str(exc)}

        newsletter.sent_at = datetime.utcnow()
        newsletter.sent_to = recipients
        newsletter.error_message = None
        await session.commit()
        logger.info("newsletter %s sent to %s", newsletter_id, recipients)
        return {"success": True, "recipients": recipients}

    @staticmethod
    def _plain_text_fallback(newsletter: Newsletter) -> str:
        ai = newsletter.ai_summary or {}
        lines = [newsletter.subject, ""]
        if ai.get("headline"):
            lines.append(ai["headline"])
            lines.append("")
        for line in ai.get("summary_3lines") or []:
            lines.append(f"- {line}")
        lines.append("")
        for i, ev in enumerate(ai.get("key_events") or [], 1):
            lines.append(f"[{i}] {ev.get('title','')}")
            if ev.get("description"):
                lines.append(f"    {ev['description']}")
        lines.append("")
        lines.append("[경영자 지침]")
        for i, act in enumerate(ai.get("executive_actions") or [], 1):
            lines.append(f"{i}. {act.get('action','')}")
        return "\n".join(lines)
