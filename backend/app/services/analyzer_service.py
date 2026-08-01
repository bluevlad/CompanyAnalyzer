"""
AI 분석 서비스
- Ollama를 활용한 기업 홈페이지 분석
- 카테고리별 분석 (사업/디지털/브랜딩/종합)
"""

import json

import ollama as ollama_lib

from app.core.config import get_settings
from app.prompts.business_analysis import BUSINESS_ANALYSIS_PROMPT
from app.prompts.digital_analysis import DIGITAL_ANALYSIS_PROMPT
from app.prompts.branding_analysis import BRANDING_ANALYSIS_PROMPT
from app.prompts.summary_analysis import SUMMARY_ANALYSIS_PROMPT

settings = get_settings()


class AnalyzerService:
    def __init__(self):
        self.client = ollama_lib.AsyncClient(host=settings.OLLAMA_BASE_URL)
        self.model = settings.ANALYSIS_MODEL

    async def analyze(self, preprocessed_data: dict) -> dict:
        """전처리된 데이터를 기반으로 기업을 분석합니다."""
        # Layer 1 구조화 텍스트가 있으면 우선 사용 (더 효율적)
        combined_text = preprocessed_data.get("structured_text") or preprocessed_data["combined_text"]
        meta = preprocessed_data["meta"]
        extract_tokens = preprocessed_data.get("extract_tokens", 0)

        if not combined_text.strip():
            return {"error": "분석할 콘텐츠가 없습니다."}

        results = {}
        total_tokens = 0

        # 카테고리별 분석 수행
        categories = {
            "business": BUSINESS_ANALYSIS_PROMPT,
            "digital": DIGITAL_ANALYSIS_PROMPT,
            "branding": BRANDING_ANALYSIS_PROMPT,
        }

        for category, prompt_template in categories.items():
            result, tokens = await self._call_llm(
                prompt_template, combined_text, meta
            )
            results[category] = result
            total_tokens += tokens

        # 종합 분석 (이전 분석 결과를 포함)
        summary_result, summary_tokens = await self._call_summary(
            combined_text, meta, results
        )
        results["summary"] = summary_result
        total_tokens += summary_tokens

        return {
            "results": results,
            "total_tokens": total_tokens + extract_tokens,
        }

    async def _call_llm(
        self, prompt_template: str, content: str, meta: dict
    ) -> tuple[dict, int]:
        """Ollama를 호출하여 분석합니다."""
        user_message = prompt_template.format(
            url=meta.get("main_url", ""),
            title=meta.get("main_title", ""),
            description=meta.get("main_description", ""),
            content=content,
        )

        try:
            response = await self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": user_message}],
                options={"num_predict": 4096, "temperature": 0.3},
            )

            text = response["message"]["content"]
            tokens = response.get("prompt_eval_count", 0) + response.get("eval_count", 0)

            # JSON 파싱 시도
            result = self._parse_json_response(text)
            return result, tokens

        except Exception as e:
            return {"error": str(e)}, 0

    async def _call_summary(
        self, content: str, meta: dict, category_results: dict
    ) -> tuple[dict, int]:
        """종합 분석을 수행합니다."""
        previous_results = json.dumps(category_results, ensure_ascii=False, indent=2)

        user_message = SUMMARY_ANALYSIS_PROMPT.format(
            url=meta.get("main_url", ""),
            title=meta.get("main_title", ""),
            content=content,
            previous_results=previous_results,
        )

        try:
            response = await self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": user_message}],
                options={"num_predict": 4096, "temperature": 0.3},
            )

            text = response["message"]["content"]
            tokens = response.get("prompt_eval_count", 0) + response.get("eval_count", 0)
            result = self._parse_json_response(text)
            return result, tokens

        except Exception as e:
            return {"error": str(e)}, 0

    def _parse_json_response(self, text: str) -> dict:
        """LLM 응답에서 JSON을 추출합니다."""
        # JSON 블록 추출 시도
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            text = text[start:end].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_text": text}
