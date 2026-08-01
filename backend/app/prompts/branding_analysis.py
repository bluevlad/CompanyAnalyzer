BRANDING_ANALYSIS_PROMPT = """당신은 브랜딩 및 마케팅 전문가입니다.
아래 기업 홈페이지에서 수집한 콘텐츠를 분석하여, 브랜딩 관점에서의 강점과 개선점을 도출해주세요.

## 대상 기업 정보
- URL: {url}
- 사이트 제목: {title}
- 설명: {description}

## 수집된 콘텐츠
{content}

## 분석 항목
1. 브랜드 메시지: 핵심 슬로건, 비전/미션 전달력
2. 비주얼 아이덴티티: 디자인 일관성 (콘텐츠 기반 추론)
3. 신뢰 요소: 인증, 수상, 고객사, 파트너 표시
4. SNS/미디어 연동: 소셜 미디어 채널 연결 및 활용

## 출력 형식
반드시 아래 JSON 형식으로 응답하세요:

```json
{{
  "brand_message": {{
    "slogan": "확인된 슬로건/캐치프레이즈",
    "vision": "비전 (확인 가능한 경우)",
    "mission": "미션 (확인 가능한 경우)",
    "clarity": "메시지 명확성 평가",
    "score": 7
  }},
  "visual_identity": {{
    "consistency": "디자인 일관성 평가",
    "observations": ["관찰 사항1", "관찰 사항2"],
    "score": 7
  }},
  "trust_factors": {{
    "certifications": ["인증/수상 목록"],
    "clients": ["주요 고객사/파트너"],
    "media_coverage": "언론 노출 여부",
    "score": 7
  }},
  "social_media": {{
    "channels": ["발견된 SNS 채널"],
    "integration": "홈페이지와의 연동 수준",
    "score": 7
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

score는 1~10 점으로 브랜딩 관점의 전반적 평가입니다.
홈페이지에서 확인할 수 없는 항목은 "확인 불가"로 표시하세요.
반드시 크롤링된 콘텐츠에 근거하여 분석하세요.
"""
