"""
사이트 정량 평가 서비스
- 코드로 직접 측정 가능한 항목을 평가
- LLM 분석과 가중 평균하여 최종 점수 산출
"""

import time
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings

settings = get_settings()


class SiteEvaluatorService:
    """웹사이트의 기술적 품질을 정량 측정합니다."""

    async def evaluate(self, url: str, crawled_pages: list[dict]) -> dict:
        """사이트를 정량 평가하여 항목별 점수를 반환합니다."""
        results = {}

        # 메인 페이지 측정
        main_metrics = await self._measure_main_page(url)
        results["https"] = main_metrics.get("https", 0)
        results["load_time"] = main_metrics.get("load_time", 0)
        results["load_time_score"] = self._score_load_time(main_metrics.get("load_time_ms", 9999))

        # HTML 분석 (크롤링 결과 활용)
        html_metrics = self._analyze_html(crawled_pages)
        results["mobile_responsive"] = html_metrics.get("mobile_responsive", 0)
        results["seo_meta_tags"] = html_metrics.get("seo_meta_tags", 0)
        results["multilingual"] = html_metrics.get("multilingual", 0)
        results["structured_data"] = html_metrics.get("structured_data", 0)
        results["accessibility"] = html_metrics.get("accessibility", 0)
        results["image_alt_ratio"] = html_metrics.get("image_alt_ratio", 0)

        # 종합 코드 측정 점수 (10점 만점)
        weights = {
            "https": 1.5,
            "load_time_score": 1.5,
            "mobile_responsive": 2.0,
            "seo_meta_tags": 1.5,
            "multilingual": 1.0,
            "structured_data": 1.0,
            "accessibility": 1.0,
            "image_alt_ratio": 0.5,
        }
        total_weight = sum(weights.values())
        weighted_sum = sum(results.get(k, 0) * w for k, w in weights.items())
        results["code_measured_score"] = round(weighted_sum / total_weight, 1)

        return results

    async def _measure_main_page(self, url: str) -> dict:
        """메인 페이지의 HTTPS 및 로딩 시간을 측정합니다."""
        result = {"https": 0, "load_time_ms": 9999}
        try:
            async with httpx.AsyncClient(
                timeout=15, follow_redirects=True,
                headers={"User-Agent": settings.USER_AGENT},
            ) as client:
                start = time.time()
                response = await client.get(url)
                elapsed_ms = (time.time() - start) * 1000

                # HTTPS 확인
                final_url = str(response.url)
                result["https"] = 10 if final_url.startswith("https://") else 0

                # 로딩 시간
                result["load_time_ms"] = round(elapsed_ms)
        except Exception:
            pass
        return result

    def _score_load_time(self, ms: int) -> int:
        """로딩 시간을 10점 스케일로 변환합니다."""
        if ms < 500:
            return 10
        elif ms < 1000:
            return 9
        elif ms < 1500:
            return 8
        elif ms < 2000:
            return 7
        elif ms < 3000:
            return 6
        elif ms < 4000:
            return 5
        elif ms < 5000:
            return 4
        elif ms < 7000:
            return 3
        elif ms < 10000:
            return 2
        else:
            return 1

    def _analyze_html(self, crawled_pages: list[dict]) -> dict:
        """크롤링된 페이지의 HTML을 분석합니다."""
        if not crawled_pages:
            return {}

        result = {
            "mobile_responsive": 0,
            "seo_meta_tags": 0,
            "multilingual": 0,
            "structured_data": 0,
            "accessibility": 0,
            "image_alt_ratio": 0,
        }

        # 메인 페이지 분석 (첫 번째 크롤링 페이지의 텍스트에서)
        main_text = crawled_pages[0].get("text", "")
        main_og = crawled_pages[0].get("og_tags", {})

        # 전체 페이지 분석을 위해 원본 HTML이 필요하나,
        # 크롤링 결과에는 텍스트만 있으므로 메타데이터 기반 분석
        has_viewport = False
        has_description = False
        has_og_title = False
        has_og_desc = False
        has_og_image = False
        lang_count = set()
        has_jsonld = False
        total_images = 0
        images_with_alt = 0

        for page in crawled_pages:
            meta_desc = page.get("meta_description", "")
            og_tags = page.get("og_tags", {})

            if meta_desc:
                has_description = True
            if og_tags.get("og:title"):
                has_og_title = True
            if og_tags.get("og:description"):
                has_og_desc = True
            if og_tags.get("og:image"):
                has_og_image = True
            if og_tags.get("og:locale"):
                lang_count.add(og_tags["og:locale"])

        # viewport는 og_tags에 없으므로 전체적 heuristic 사용
        # (실제로는 메인 페이지의 HTML에서 확인해야 하지만, 크롤러가 텍스트만 저장)
        # → 대부분의 현대 사이트는 viewport를 가지고 있다고 가정하되,
        #   크롤링 시 meta viewport 존재 여부를 별도 저장하면 더 정확해짐

        # 모바일 반응형 (heuristic: og tags가 있으면 최소한의 모바일 대응 가정)
        if has_og_title and has_og_image:
            result["mobile_responsive"] = 6  # 기본 대응
        if has_og_desc:
            result["mobile_responsive"] = min(result["mobile_responsive"] + 2, 10)

        # SEO 메타 태그
        seo_score = 0
        if has_description:
            seo_score += 3
        if has_og_title:
            seo_score += 2
        if has_og_desc:
            seo_score += 2
        if has_og_image:
            seo_score += 2
        # title 존재 (크롤링 결과에 title이 있으면)
        pages_with_title = sum(1 for p in crawled_pages if p.get("title"))
        if pages_with_title >= len(crawled_pages) * 0.8:
            seo_score += 1
        result["seo_meta_tags"] = min(seo_score, 10)

        # 다국어 지원
        if len(lang_count) >= 4:
            result["multilingual"] = 10
        elif len(lang_count) >= 3:
            result["multilingual"] = 8
        elif len(lang_count) >= 2:
            result["multilingual"] = 6
        elif len(lang_count) >= 1:
            result["multilingual"] = 3
        else:
            result["multilingual"] = 0

        # 구조화 데이터 (JSON-LD 등) - 크롤링 텍스트에서 단서 추출
        for page in crawled_pages:
            text = page.get("text", "")
            if "schema.org" in text.lower() or "json-ld" in text.lower():
                has_jsonld = True
                break
        result["structured_data"] = 7 if has_jsonld else 2

        # 접근성 (heuristic)
        result["accessibility"] = 5  # 기본값, 상세 분석 시 개선

        # 이미지 alt (크롤링 텍스트만으로는 측정 어려움)
        result["image_alt_ratio"] = 5  # 기본값

        return result

    @staticmethod
    def blend_scores(code_score: float, llm_score: float, code_weight: float = 0.4) -> float:
        """코드 측정 점수와 LLM 점수를 가중 평균합니다."""
        return round(code_score * code_weight + llm_score * (1 - code_weight), 1)
