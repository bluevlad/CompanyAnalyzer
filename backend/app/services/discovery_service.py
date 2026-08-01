"""
Discovery 서비스
- 메인 페이지 + sitemap.xml에서 URL 수집
- 발견된 URL을 카테고리별로 자동 분류
- 본문은 가져오지 않고 URL 구조만 파악
"""

import asyncio
import re
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings

settings = get_settings()

# URL 패턴 → 카테고리 매핑
CATEGORY_PATTERNS = {
    "company": [
        r"/about", r"/company", r"/intro", r"/history", r"/ceo",
        r"/vision", r"/mission", r"/overview", r"/greetings",
        r"/회사", r"/소개", r"/인사말", r"/비전", r"/연혁", r"/조직",
    ],
    "product": [
        r"/product", r"/item", r"/goods", r"/lineup", r"/catalog",
        r"/제품", r"/상품",
    ],
    "solution": [
        r"/solution", r"/platform", r"/솔루션", r"/플랫폼",
    ],
    "service": [
        r"/service", r"/support", r"/customer", r"/faq", r"/help",
        r"/서비스", r"/고객", r"/지원",
    ],
    "technology": [
        r"/tech", r"/rnd", r"/research", r"/patent", r"/innovation",
        r"/기술", r"/연구", r"/특허", r"/핵심역량",
    ],
    "news": [
        r"/news", r"/press", r"/notice", r"/board", r"/blog", r"/media",
        r"/뉴스", r"/공지", r"/보도", r"/게시판",
    ],
    "career": [
        r"/career", r"/recruit", r"/job", r"/hiring", r"/talent",
        r"/채용", r"/인재",
    ],
    "ir": [
        r"/ir", r"/investor", r"/finance", r"/disclosure", r"/stock",
        r"/투자", r"/공시", r"/재무",
    ],
    "ethics": [
        r"/ethics", r"/compliance", r"/esg", r"/sustain", r"/csr",
        r"/윤리", r"/경영",
    ],
    "ci": [
        r"/ci", r"/bi", r"/brand", r"/identity", r"/logo",
    ],
}

# 크롤링 대상에서 제외할 패턴
EXCLUDE_PATTERNS = [
    r"\.(pdf|zip|doc|xls|ppt|jpg|jpeg|png|gif|svg|mp4|mp3|exe|dmg)$",
    r"/login", r"/signin", r"/register", r"/signup",
    r"/cart", r"/checkout", r"/payment",
    r"/admin", r"/wp-admin",
    r"#", r"javascript:", r"mailto:", r"tel:",
]


class DiscoveryService:
    def __init__(self):
        self.discovered: dict[str, dict] = {}  # url -> {category, depth, title, priority}

    def _classify_url(self, url: str) -> str:
        """URL 패턴으로 카테고리를 분류합니다."""
        path = urlparse(url).path.lower()
        for category, patterns in CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    return category
        return "other"

    def _get_priority(self, category: str) -> int:
        """카테고리별 크롤링 우선순위를 반환합니다. (낮을수록 높은 우선순위)"""
        priority_map = {
            "company": 1, "product": 2, "solution": 2, "service": 3,
            "technology": 3, "news": 5, "career": 7, "ir": 6,
            "ethics": 6, "ci": 6, "other": 8,
        }
        return priority_map.get(category, 8)

    def _should_exclude(self, url: str) -> bool:
        """제외 대상 URL인지 확인합니다."""
        for pattern in EXCLUDE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def _extract_links_from_html(self, html: str, base_url: str) -> list[dict]:
        """HTML에서 내부 링크와 제목을 추출합니다."""
        soup = BeautifulSoup(html, "lxml")
        base_domain = urlparse(base_url).netloc
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            if parsed.netloc != base_domain or parsed.scheme not in ("http", "https"):
                continue

            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean_url.endswith("/") and len(parsed.path) > 1:
                clean_url = clean_url.rstrip("/")

            if self._should_exclude(clean_url):
                continue

            if clean_url not in self.discovered:
                title = a_tag.get_text(strip=True)[:200] or None
                links.append({"url": clean_url, "title": title})

        return links

    async def _parse_sitemap(self, base_url: str, client: httpx.AsyncClient) -> list[str]:
        """sitemap.xml에서 URL을 추출합니다."""
        urls = []
        sitemap_url = urljoin(base_url, "/sitemap.xml")
        try:
            response = await client.get(sitemap_url)
            if response.status_code == 200 and "xml" in response.headers.get("content-type", ""):
                soup = BeautifulSoup(response.text, "lxml-xml")
                for loc in soup.find_all("loc"):
                    url = loc.get_text(strip=True)
                    parsed = urlparse(url)
                    if parsed.netloc == urlparse(base_url).netloc:
                        urls.append(url)
        except Exception:
            pass
        return urls

    async def discover(self, url: str) -> list[dict]:
        """홈페이지 구조를 파악하여 URL 목록과 카테고리를 반환합니다."""
        self.discovered.clear()
        base_domain = urlparse(url).netloc
        max_pages = 100  # Discovery 단계 최대 URL 수

        rp = await self._check_robots_txt(url)

        async with httpx.AsyncClient(
            timeout=settings.CRAWL_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": settings.USER_AGENT},
        ) as client:
            # 1. 메인 페이지에서 링크 수집
            try:
                response = await client.get(url)
                if response.status_code == 200 and "text/html" in response.headers.get("content-type", ""):
                    html = response.text
                    main_title = ""
                    soup = BeautifulSoup(html, "lxml")
                    if soup.title and soup.title.string:
                        main_title = soup.title.string.strip()

                    # 메인 페이지 등록
                    self.discovered[url] = {
                        "url": url,
                        "category": "company",
                        "depth": 0,
                        "priority": 1,
                        "title": main_title,
                        "parent_url": None,
                    }

                    # nav, header의 링크를 우선 수집
                    for nav_area in soup.find_all(["nav", "header"]):
                        for link_info in self._extract_links_from_html(str(nav_area), url):
                            if link_info["url"] not in self.discovered:
                                category = self._classify_url(link_info["url"])
                                self.discovered[link_info["url"]] = {
                                    "url": link_info["url"],
                                    "category": category,
                                    "depth": 1,
                                    "priority": self._get_priority(category),
                                    "title": link_info["title"],
                                    "parent_url": url,
                                }

                    # 전체 페이지 링크 수집
                    for link_info in self._extract_links_from_html(html, url):
                        if link_info["url"] not in self.discovered and len(self.discovered) < max_pages:
                            category = self._classify_url(link_info["url"])
                            self.discovered[link_info["url"]] = {
                                "url": link_info["url"],
                                "category": category,
                                "depth": 1,
                                "priority": self._get_priority(category),
                                "title": link_info["title"],
                                "parent_url": url,
                            }
            except Exception:
                pass

            # 2. sitemap.xml에서 추가 URL 수집
            sitemap_urls = await self._parse_sitemap(url, client)
            for sitemap_url in sitemap_urls:
                if sitemap_url not in self.discovered and len(self.discovered) < max_pages:
                    if not self._should_exclude(sitemap_url):
                        category = self._classify_url(sitemap_url)
                        self.discovered[sitemap_url] = {
                            "url": sitemap_url,
                            "category": category,
                            "depth": 1,
                            "priority": self._get_priority(category),
                            "title": None,
                            "parent_url": None,
                        }

            # 3. 주요 카테고리 페이지에서 2depth 링크 수집 (제품/솔루션 상세)
            depth1_pages = [
                d for d in self.discovered.values()
                if d["depth"] == 1 and d["category"] in ("product", "solution", "service")
            ]
            depth1_pages.sort(key=lambda x: x["priority"])

            for page in depth1_pages[:10]:  # 최대 10개 카테고리 페이지만 2depth 탐색
                if len(self.discovered) >= max_pages:
                    break

                try:
                    if not self._is_allowed(rp, page["url"]):
                        continue
                    response = await client.get(page["url"])
                    if response.status_code == 200 and "text/html" in response.headers.get("content-type", ""):
                        for link_info in self._extract_links_from_html(response.text, page["url"]):
                            if link_info["url"] not in self.discovered and len(self.discovered) < max_pages:
                                category = self._classify_url(link_info["url"])
                                if category == "other":
                                    category = page["category"]
                                self.discovered[link_info["url"]] = {
                                    "url": link_info["url"],
                                    "category": category,
                                    "depth": 2,
                                    "priority": self._get_priority(category) + 1,
                                    "title": link_info["title"],
                                    "parent_url": page["url"],
                                }
                    await asyncio.sleep(settings.CRAWL_DELAY_SECONDS)
                except Exception:
                    continue

        # 결과를 우선순위순으로 정렬하여 반환
        result = list(self.discovered.values())
        result.sort(key=lambda x: (x["priority"], x["depth"]))
        return result

    async def _check_robots_txt(self, base_url: str) -> RobotFileParser:
        rp = RobotFileParser()
        robots_url = urljoin(base_url, "/robots.txt")
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    rp.parse(response.text.splitlines())
                else:
                    rp.allow_all = True
        except Exception:
            rp.allow_all = True
        return rp

    def _is_allowed(self, rp: RobotFileParser, url: str) -> bool:
        try:
            return rp.can_fetch(settings.USER_AGENT, url)
        except Exception:
            return True
