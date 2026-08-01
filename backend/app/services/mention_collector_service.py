"""외부 언급 수집 서비스.

소스:
  - 네이버 뉴스 검색 API (NAVER_NEWS_CLIENT_ID/SECRET 필요)
  - Google News RSS (인증 불필요)

각 키워드에 대해 검색 → BeautifulSoup으로 본문 정제 → content_hash로 중복 제거
→ Mention 레코드 upsert.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import quote_plus

import feedparser
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.models import Mention, MonitoringTarget

logger = logging.getLogger(__name__)
settings = get_settings()


def _content_hash(url: str, title: str) -> str:
    return hashlib.sha256(f"{url}|{title}".encode("utf-8")).hexdigest()


def _strip_html(html: str | None) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "lxml").get_text(separator=" ", strip=True)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


class MentionCollectorService:
    """모니터링 대상의 키워드로 외부 뉴스/언급을 수집한다."""

    def __init__(self) -> None:
        self.timeout = httpx.Timeout(15.0)

    # ─────────────────────── 소스별 수집기 ──────────────────────────────

    async def fetch_naver_news(self, keyword: str, display: int = 30) -> list[dict]:
        """네이버 검색 API — News."""
        if not settings.NAVER_NEWS_CLIENT_ID or not settings.NAVER_NEWS_CLIENT_SECRET:
            logger.warning("NAVER_NEWS credentials missing — skipping naver_news")
            return []

        url = "https://openapi.naver.com/v1/search/news.json"
        params = {"query": keyword, "display": display, "sort": "date"}
        headers = {
            "X-Naver-Client-Id": settings.NAVER_NEWS_CLIENT_ID,
            "X-Naver-Client-Secret": settings.NAVER_NEWS_CLIENT_SECRET,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.error("naver_news fetch failed for '%s': %s", keyword, exc)
            return []

        items = []
        for item in data.get("items", []):
            link = item.get("originallink") or item.get("link") or ""
            title = _strip_html(item.get("title"))
            description = _strip_html(item.get("description"))
            published_at = _parse_dt(item.get("pubDate"))
            items.append(
                {
                    "source_type": "news",
                    "source_name": "네이버뉴스",
                    "url": link,
                    "title": title,
                    "raw_content": description,
                    "published_at": published_at,
                    "author": None,
                }
            )
        return items

    async def fetch_google_news_rss(self, keyword: str) -> list[dict]:
        """Google News RSS — 인증 불필요."""
        lang = settings.GOOGLE_NEWS_RSS_LANG
        country = settings.GOOGLE_NEWS_RSS_COUNTRY
        q = quote_plus(keyword)
        url = (
            f"https://news.google.com/rss/search?q={q}"
            f"&hl={lang}&gl={country}&ceid={country}:{lang}"
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                feed_text = resp.text
        except Exception as exc:
            logger.error("google_news_rss fetch failed for '%s': %s", keyword, exc)
            return []

        # feedparser는 동기 — run_in_executor로 wrap
        loop = asyncio.get_running_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, feed_text)

        items = []
        for entry in feed.entries[: settings.MENTION_FETCH_LIMIT]:
            link = getattr(entry, "link", "")
            title = _strip_html(getattr(entry, "title", ""))
            summary = _strip_html(getattr(entry, "summary", ""))
            published = getattr(entry, "published", None)
            published_at = _parse_dt(published)
            source_name = "Google News"
            src = getattr(entry, "source", None)
            if src and isinstance(src, dict) and src.get("title"):
                source_name = f"Google News / {src['title']}"
            items.append(
                {
                    "source_type": "news",
                    "source_name": source_name,
                    "url": link,
                    "title": title,
                    "raw_content": summary,
                    "published_at": published_at,
                    "author": None,
                }
            )
        return items

    # ─────────────────────── 통합 수집 ──────────────────────────────────

    async def collect(
        self, session: AsyncSession, target: MonitoringTarget
    ) -> list[Mention]:
        """target.keywords + news_sources에 따라 수집하고 DB에 upsert."""
        if not target.is_active:
            logger.info("target %s inactive — skip", target.id)
            return []

        keywords: list[str] = target.keywords or []
        sources: list[str] = target.news_sources or []
        all_items: list[dict] = []

        for keyword in keywords:
            for source in sources:
                if source == "naver_news":
                    items = await self.fetch_naver_news(keyword)
                elif source == "google_news_rss":
                    items = await self.fetch_google_news_rss(keyword)
                else:
                    logger.warning("unknown source: %s", source)
                    continue
                # 매칭된 키워드 기록
                for it in items:
                    it.setdefault("matched_keywords", []).append(keyword)
                all_items.extend(items)
                # 외부 API rate limit 보호
                await asyncio.sleep(0.5)

        # URL+title 기준으로 같은 키워드 중복 제거 (같은 기사를 여러 키워드로 잡힌 경우 매칭만 합침)
        merged: dict[str, dict] = {}
        for it in all_items:
            if not it.get("url") or not it.get("title"):
                continue
            h = _content_hash(it["url"], it["title"])
            if h in merged:
                merged[h]["matched_keywords"] = sorted(
                    set(merged[h].get("matched_keywords", []) + it.get("matched_keywords", []))
                )
            else:
                it["content_hash"] = h
                merged[h] = it

        return await self._upsert(session, target.id, list(merged.values()))

    async def _upsert(
        self, session: AsyncSession, target_id: int, items: Iterable[dict]
    ) -> list[Mention]:
        saved: list[Mention] = []
        for it in items:
            existing = await session.execute(
                select(Mention).where(Mention.content_hash == it["content_hash"])
            )
            mention = existing.scalar_one_or_none()
            if mention is not None:
                # 매칭 키워드만 보강
                merged_kw = sorted(
                    set((mention.matched_keywords or []) + (it.get("matched_keywords") or []))
                )
                mention.matched_keywords = merged_kw
                continue

            mention = Mention(
                target_id=target_id,
                source_type=it["source_type"],
                source_name=it.get("source_name"),
                url=it["url"][:1000],
                title=(it.get("title") or "")[:500],
                published_at=it.get("published_at"),
                author=it.get("author"),
                raw_content=it.get("raw_content"),
                content_hash=it["content_hash"],
                matched_keywords=it.get("matched_keywords") or [],
            )
            session.add(mention)
            saved.append(mention)

        await session.commit()
        logger.info(
            "target=%s collected=%s new=%s", target_id, len(list(items)), len(saved)
        )
        return saved
