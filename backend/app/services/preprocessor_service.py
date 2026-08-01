"""
콘텐츠 전처리 서비스
- 크롤링 결과를 LLM 분석에 적합한 형태로 변환
- Layer 1: 페이지별 구조화 추출 (gemma3:4b)
- 토큰 최적화 (중복 제거, 길이 제한)
"""

import json

import ollama as ollama_lib

from app.core.config import get_settings

settings = get_settings()

PAGE_EXTRACTION_PROMPT = """아래 웹페이지 콘텐츠에서 구조화된 정보를 JSON으로 추출하세요.

페이지 URL: {url}
페이지 제목: {title}

콘텐츠:
{text}

다음 JSON 형식으로 응답하세요 (필드가 없으면 빈 값):
```json
{{
  "page_type": "company|product|solution|service|technology|news|career|ir|other",
  "summary": "페이지 핵심 내용 2-3문장 요약",
  "products": ["발견된 제품/서비스명"],
  "features": ["주요 특징/기능"],
  "specs": {{}},
  "key_claims": ["기업이 주장하는 핵심 강점/차별점"],
  "certifications": ["발견된 인증/수상"],
  "numbers": {{}},
  "contact_info": {{}}
}}
```
반드시 유효한 JSON만 출력하세요."""


class PreprocessorService:

    MAX_PAGE_TEXT_LENGTH = 5000
    MAX_TOTAL_TEXT_LENGTH = 30000

    def preprocess(self, crawled_pages: list[dict]) -> dict:
        """크롤링 결과를 LLM 분석용으로 전처리합니다."""
        if not crawled_pages:
            return {"pages": [], "meta": {}, "combined_text": ""}

        processed_pages = []
        seen_texts = set()

        for page in crawled_pages:
            text = page.get("text", "")

            text_hash = hash(text[:200])
            if text_hash in seen_texts:
                continue
            seen_texts.add(text_hash)

            if len(text) > self.MAX_PAGE_TEXT_LENGTH:
                text = text[:self.MAX_PAGE_TEXT_LENGTH] + "\n...(truncated)"

            processed_pages.append({
                "url": page.get("url", ""),
                "title": page.get("title", ""),
                "meta_description": page.get("meta_description", ""),
                "text": text,
            })

        combined_parts = []
        total_length = 0

        for p in processed_pages:
            section = f"## {p['title']} ({p['url']})\n{p['text']}"
            if total_length + len(section) > self.MAX_TOTAL_TEXT_LENGTH:
                break
            combined_parts.append(section)
            total_length += len(section)

        main_page = crawled_pages[0] if crawled_pages else {}
        meta = {
            "main_url": main_page.get("url", ""),
            "main_title": main_page.get("title", ""),
            "main_description": main_page.get("meta_description", ""),
            "og_tags": main_page.get("og_tags", {}),
            "total_pages": len(crawled_pages),
            "processed_pages": len(processed_pages),
        }

        return {
            "pages": processed_pages,
            "meta": meta,
            "combined_text": "\n\n".join(combined_parts),
        }

    async def preprocess_with_extraction(self, crawled_pages: list[dict]) -> dict:
        """Layer 1: 페이지별 구조화 추출 후 통합 데이터를 반환합니다."""
        if not crawled_pages:
            return {"pages": [], "meta": {}, "combined_text": "", "extracted": []}

        basic = self.preprocess(crawled_pages)
        client = ollama_lib.AsyncClient(host=settings.OLLAMA_BASE_URL)
        extracted = []
        total_extract_tokens = 0

        for page in basic["pages"][:15]:  # 최대 15페이지 추출
            text = page.get("text", "").strip()
            if len(text) < 50:
                continue

            prompt = PAGE_EXTRACTION_PROMPT.format(
                url=page.get("url", ""),
                title=page.get("title", ""),
                text=text[:3000],
            )

            try:
                response = await client.chat(
                    model=settings.PREPROCESSING_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    options={"num_predict": 1024, "temperature": 0.1},
                )
                resp_text = response["message"]["content"]
                total_extract_tokens += response.get("prompt_eval_count", 0) + response.get("eval_count", 0)

                result = self._parse_json(resp_text)
                result["source_url"] = page.get("url", "")
                result["source_title"] = page.get("title", "")
                extracted.append(result)
            except Exception:
                extracted.append({
                    "source_url": page.get("url", ""),
                    "source_title": page.get("title", ""),
                    "summary": page.get("text", "")[:200],
                    "error": "extraction_failed",
                })

        # 추출 결과를 combined_text 대신 사용할 구조화된 텍스트 생성
        structured_parts = []
        for ext in extracted:
            section = f"## {ext.get('source_title', '')} ({ext.get('source_url', '')})\n"
            if ext.get("summary"):
                section += f"요약: {ext['summary']}\n"
            if ext.get("products"):
                section += f"제품: {', '.join(ext['products'])}\n"
            if ext.get("features"):
                section += f"특징: {', '.join(ext['features'])}\n"
            if ext.get("key_claims"):
                section += f"핵심주장: {', '.join(ext['key_claims'])}\n"
            if ext.get("certifications"):
                section += f"인증: {', '.join(ext['certifications'])}\n"
            if ext.get("numbers") and isinstance(ext["numbers"], dict):
                for k, v in ext["numbers"].items():
                    section += f"{k}: {v}\n"
            structured_parts.append(section)

        basic["extracted"] = extracted
        basic["structured_text"] = "\n\n".join(structured_parts)
        basic["extract_tokens"] = total_extract_tokens

        return basic

    def _parse_json(self, text: str) -> dict:
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
            return {"raw_text": text[:300]}
