"""모니터링 대상 기업 seed.

사용법:
    cd backend
    python -m scripts.seed_company --name "Acme" --url https://www.acme.example \
        --keywords "Acme,acme.example" [--industry "제조"] [--recipients admin@example.com,...]

idempotent — 이미 존재하면 갱신만 한다.
"""
import argparse
import asyncio
from typing import List

from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.database.models import Company, MonitoringTarget

DEFAULT_NEWS_SOURCES = ["naver_news", "google_news_rss"]


async def seed(
    name: str,
    url: str,
    keywords: List[str],
    industry: str,
    description: str,
    recipients: List[str],
) -> None:
    async with AsyncSessionLocal() as session:
        # 1) Company upsert
        result = await session.execute(select(Company).where(Company.url == url))
        company = result.scalar_one_or_none()
        if company is None:
            company = Company(
                name=name,
                url=url,
                industry=industry or None,
                description=description or None,
            )
            session.add(company)
            await session.flush()
            print(f"[+] Company created: id={company.id} name={company.name}")
        else:
            print(f"[=] Company exists: id={company.id} name={company.name}")

        # 2) MonitoringTarget upsert
        result = await session.execute(
            select(MonitoringTarget).where(MonitoringTarget.company_id == company.id)
        )
        target = result.scalar_one_or_none()
        if target is None:
            target = MonitoringTarget(
                company_id=company.id,
                keywords=keywords,
                news_sources=DEFAULT_NEWS_SOURCES,
                schedule_daily=True,
                schedule_weekly=True,
                schedule_monthly=True,
                recipient_emails=recipients,
                is_active=True,
            )
            session.add(target)
            await session.flush()
            print(f"[+] MonitoringTarget created: id={target.id}")
        else:
            target.keywords = keywords
            target.news_sources = DEFAULT_NEWS_SOURCES
            target.recipient_emails = recipients
            target.is_active = True
            print(f"[=] MonitoringTarget updated: id={target.id}")

        await session.commit()
        print("[OK] Seed complete.")


def _split_csv(value: str) -> List[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, required=True, help="Company name")
    parser.add_argument("--url", type=str, required=True, help="Company homepage URL")
    parser.add_argument(
        "--keywords",
        type=str,
        required=True,
        help="Comma-separated monitoring keywords",
    )
    parser.add_argument("--industry", type=str, default="", help="Industry label")
    parser.add_argument("--description", type=str, default="", help="Company description")
    parser.add_argument(
        "--recipients",
        type=str,
        default="admin@example.com",
        help="Comma-separated recipient emails",
    )
    args = parser.parse_args()
    asyncio.run(
        seed(
            name=args.name,
            url=args.url,
            keywords=_split_csv(args.keywords),
            industry=args.industry,
            description=args.description,
            recipients=_split_csv(args.recipients),
        )
    )


if __name__ == "__main__":
    main()
