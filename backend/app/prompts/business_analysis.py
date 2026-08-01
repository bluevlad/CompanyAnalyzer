BUSINESS_ANALYSIS_PROMPT = """당신은 기업 분석 전문가입니다.
아래 기업 홈페이지에서 수집한 콘텐츠를 분석하여, 사업 관점에서의 강점과 개선점을 도출해주세요.

## 대상 기업 정보
- URL: {url}
- 사이트 제목: {title}
- 설명: {description}

## 수집된 콘텐츠
{content}

## 분석 항목
1. 핵심 사업 영역: 주요 사업 분야 및 비즈니스 모델
2. 제품/서비스 라인업: 제공하는 제품/서비스의 종류와 특징
3. 차별화 포인트: 경쟁사 대비 독자적 강점
4. 고객/타겟 시장: 주요 고객군 및 시장
5. 기업 규모/연혁: 설립, 규모, 성장 과정

## 출력 형식
반드시 아래 JSON 형식으로 응답하세요:

```json
{{
  "core_business": {{
    "areas": ["사업 영역 1", "사업 영역 2"],
    "business_model": "비즈니스 모델 설명",
    "description": "핵심 사업 요약"
  }},
  "products_services": [
    {{
      "name": "제품/서비스명",
      "description": "설명",
      "features": ["특징1", "특징2"]
    }}
  ],
  "differentiators": [
    {{
      "title": "차별화 포인트",
      "description": "상세 설명",
      "evidence": "근거"
    }}
  ],
  "target_market": {{
    "customers": ["고객군1", "고객군2"],
    "markets": ["시장1", "시장2"]
  }},
  "company_profile": {{
    "name": "기업명",
    "founded": "설립연도 (확인 가능한 경우)",
    "size": "규모 (확인 가능한 경우)",
    "history_highlights": ["주요 연혁"]
  }},
  "strengths": [
    {{
      "title": "강점 항목",
      "description": "상세 설명",
      "evidence": "홈페이지 콘텐츠 기반 근거"
    }}
  ],
  "improvements": [
    {{
      "title": "개선 항목",
      "description": "상세 설명",
      "suggestion": "구체적 개선 제안"
    }}
  ],
  "score": 8
}}
```

score는 1~10 점으로 사업 관점의 전반적 평가입니다.
홈페이지에서 확인할 수 없는 항목은 "확인 불가"로 표시하세요.
반드시 크롤링된 콘텐츠에 근거하여 분석하세요.
"""
