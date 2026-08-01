SUMMARY_ANALYSIS_PROMPT = """당신은 기업 분석 종합 전문가입니다.
아래 기업 홈페이지의 개별 분석 결과(사업/디지털/브랜딩)를 종합하여, 최종 분석 리포트를 작성해주세요.

## 대상 기업 정보
- URL: {url}
- 사이트 제목: {title}

## 홈페이지 콘텐츠 (참고용)
{content}

## 개별 분석 결과
{previous_results}

## 종합 분석 요청
위 개별 분석 결과를 종합하여:
1. 기업의 핵심 강점 Top 5를 도출
2. 우선 개선이 필요한 항목 Top 5를 도출
3. 각 개선점에 대한 구체적이고 실행 가능한 제안 제시
4. 전체적인 기업 온라인 프레즌스 종합 평가

## 출력 형식
반드시 아래 JSON 형식으로 응답하세요:

```json
{{
  "company_name": "기업명",
  "one_line_summary": "기업 한줄 요약",
  "top_strengths": [
    {{
      "rank": 1,
      "title": "강점 항목",
      "description": "상세 설명",
      "category": "business/digital/branding",
      "evidence": "근거"
    }}
  ],
  "top_improvements": [
    {{
      "rank": 1,
      "title": "개선 항목",
      "description": "상세 설명",
      "category": "business/digital/branding",
      "suggestion": "구체적이고 실행 가능한 개선 제안",
      "priority": "high/medium/low"
    }}
  ],
  "overall_scores": {{
    "business": 8,
    "digital": 7,
    "branding": 6,
    "overall": 7
  }},
  "overall_assessment": "전체적인 종합 평가 (2~3문장)"
}}
```

각 score는 1~10 점입니다.
반드시 개별 분석 결과에 근거하여 종합하세요.
"""
