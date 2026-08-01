"""단건 mention 분류 프롬프트 — sentiment, importance, 한줄요약."""

MENTION_CLASSIFIER_PROMPT = """당신은 기업 모니터링 분석가입니다.
아래 외부 언급(뉴스/보도자료) 1건을 빠르게 분류하세요.

## 대상 기업
- 기업명: {company_name}
- 키워드: {keywords}

## 언급 내용
- 출처: {source_name}
- 제목: {title}
- 본문: {content}

## 작업
1. 감성 (positive/neutral/negative)
2. 중요도 점수 (0~100): 경영진이 주목해야 할 정도
3. 카테고리 (product/finance/regulation/partnership/people/tech/marketing/other)
4. 한 줄 요약 (한국어, 80자 이내, 사실 기반)

## 출력 형식 (JSON만)

```json
{{
  "sentiment": "positive",
  "importance_score": 75,
  "category": "product",
  "one_line_summary": "○○기업, 신제품 출시로 시장 점유율 확대"
}}
```
"""
