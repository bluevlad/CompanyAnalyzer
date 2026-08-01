"""
크롤링 서비스
- robots.txt 준수
- Rate Limiting (최소 2초 간격)
- 주요 페이지 자동 탐색 및 수집
"""

import asyncio
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings

settings = get_settings()

# 주요 페이지 키워드 (우선순위 크롤링)
PRIORITY_KEYWORDS = [
    "about", "company", "business", "product", "service",
    "solution", "technology", "contact", "team", "career",
    "회사소개", "사업영역", "제품", "서비스", "기술", "솔루션",
    "인사말", "비전", "연혁", "조직",
]


class CrawlerService:
    def __init__(self):
        self.visited_urls: set = set()
        self.results: list[dict] = []

    async def check_robots_txt(self, base_url: str) -> RobotFileParser:
        """robots.txt를 확인하여 크롤링 허용 여부를 판단합니다."""
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
        """robots.txt 기준으로 크롤링 허용 여부를 확인합니다."""
        try:
            return rp.can_fetch(settings.USER_AGENT, url)
        except Exception:
            return True

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """HTML에서 내부 링크를 추출하고 우선순위 정렬합니다."""
        soup = BeautifulSoup(html, "lxml")
        base_domain = urlparse(base_url).netloc
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            # 같은 도메인의 HTTP(S) 링크만
            if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
                # 파일 다운로드 제외
                if not any(full_url.lower().endswith(ext) for ext in
                           (".pdf", ".zip", ".doc", ".xls", ".ppt", ".jpg", ".png", ".gif")):
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if clean_url not in self.visited_urls:
                        links.append(clean_url)

        # 우선순위 키워드가 포함된 URL을 앞으로
        def priority_score(url: str) -> int:
            url_lower = url.lower()
            for i, keyword in enumerate(PRIORITY_KEYWORDS):
                if keyword in url_lower:
                    return i
            return len(PRIORITY_KEYWORDS)

        links = list(set(links))
        links.sort(key=priority_score)
        return links

    def _extract_content(self, html: str) -> dict:
        """HTML에서 핵심 콘텐츠를 추출합니다."""
        soup = BeautifulSoup(html, "lxml")

        # 불필요 태그 제거
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        # 메타 정보 추출
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"]

        og_tags = {}
        for og in soup.find_all("meta", attrs={"property": lambda x: x and x.startswith("og:")}):
            og_tags[og["property"]] = og.get("content", "")

        # 본문 텍스트 추출
        body = soup.find("body")
        text = body.get_text(separator="\n", strip=True) if body else soup.get_text(separator="\n", strip=True)

        # 빈 줄 제거 및 정리
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        clean_text = "\n".join(lines)

        return {
            "title": title,
            "meta_description": meta_desc,
            "og_tags": og_tags,
            "text": clean_text,
            "text_length": len(clean_text),
        }

    async def crawl(self, url: str) -> list[dict]:
        """기업 홈페이지를 크롤링합니다."""
        self.visited_urls.clear()
        self.results.clear()

        # robots.txt 확인
        rp = await self.check_robots_txt(url)

        # 크롤링 대상 URL 큐
        urls_to_crawl = [url]

        async with httpx.AsyncClient(
            timeout=settings.CRAWL_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": settings.USER_AGENT},
        ) as client:
            while urls_to_crawl and len(self.results) < settings.MAX_CRAWL_PAGES:
                current_url = urls_to_crawl.pop(0)

                if current_url in self.visited_urls:
                    continue

                if not self._is_allowed(rp, current_url):
                    continue

                self.visited_urls.add(current_url)

                try:
                    response = await client.get(current_url)
                    if response.status_code != 200:
                        continue

                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type:
                        continue

                    html = response.text
                    content = self._extract_content(html)
                    content["url"] = current_url
                    content["status_code"] = response.status_code
                    self.results.append(content)

                    # 내부 링크 추출 및 큐에 추가
                    new_links = self._extract_links(html, current_url)
                    urls_to_crawl.extend(new_links)

                except Exception:
                    continue

                # Rate limiting
                await asyncio.sleep(settings.CRAWL_DELAY_SECONDS)

        return self.results
