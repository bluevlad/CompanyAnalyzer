DIGITAL_ANALYSIS_PROMPT = """당신은 웹사이트 UX/UI 및 디지털 마케팅 전문가입니다.
아래 기업 홈페이지에서 수집한 콘텐츠를 분석하여, 디지털 관점에서의 강점과 개선점을 도출해주세요.

## 대상 기업 정보
- URL: {url}
- 사이트 제목: {title}
- 설명: {description}

## 수집된 콘텐츠
{content}

## 분석 항목
1. UX/UI 품질: 사이트 구조, 네비게이션, 사용성
2. 콘텐츠 품질: 정보 최신성, 충분성, 다국어 지원
3. SEO 상태: 메타태그, 구조화 데이터, 키워드 활용
4. 기술 인상: 페이지 구조, 현대적 웹 기술 활용 여부

## 출력 형식
반드시 아래 JSON 형식으로 응답하세요:

```json
{{
  "ux_ui": {{
    "site_structure": "사이트 구조 평가",
    "navigation": "네비게이션 평가",
    "usability": "사용성 평가",
    "score": 7
  }},
  "content_quality": {{
    "freshness": "정보 최신성 평가",
    "completeness": "정보 충분성 평가",
    "multilingual": "다국어 지원 여부",
    "multimedia": "멀티미디어 활용 평가",
    "score": 7
  }},
  "seo": {{
    "meta_tags": "메타태그 활용 평가",
    "structured_data": "구조화 데이터 평가",
    "keyword_usage": "키워드 활용 평가",
    "score": 7
  }},
  "technology": {{
    "modern_web": "현대적 웹 기술 활용 여부",
    "observations": ["관찰 사항1", "관찰 사항2"]
  }},
  "strengths": [
    {{
      "title": "강점 항목",
      "description": "상세 설명",
      "evidence": "근거"
    }}
  ],
  "improvements": [
    {{
      "title": "개선 항목",
      "description": "상세 설명",
      "suggestion": "구체적 개선 제안"
    }}
  ],
  "score": 7
}}
```

score는 1~10 점으로 디지털 관점의 전반적 평가입니다.
반드시 크롤링된 콘텐츠에 근거하여 분석하세요.
"""
