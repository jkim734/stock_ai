import time
from typing import Optional
from dotenv import load_dotenv
import os
import re
import regex
import json
load_dotenv()

from google import genai
from google.genai import types

model_name = "gemini-2.0-flash-001"

# .env 파일에서 API 키 로드 (보안 강화)
client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))

def ask_question_to_gemini_cache(prompt, max_retries=5, retry_delay=5):
    """
    Gemini API를 사용하여 질문에 대한 답변을 얻습니다.
    뉴스 분석에 최적화된 버전입니다.
    """
    start_time = time.time()

    for attempt in range(max_retries):
        try:
            # API 키 확인
            api_key = os.getenv("GOOGLE_AI_API_KEY")
            if not api_key:
                raise Exception("GOOGLE_AI_API_KEY 환경 변수가 설정되지 않았습니다.")

            api_start = time.time()

            # Gemini API 호출
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=2048
                )
            )

            return response.text

        except Exception as e:
            error_msg = str(e).lower()
            print(f"API 오류 (시도 {attempt + 1}/{max_retries}): {e}")

            if hasattr(e, 'code') and e.code == 503:
                print(f"⏳ API 사용량 한도 초과 (시도 {attempt + 1}/{max_retries}). {retry_delay}초 후 재시도...")
                time.sleep(retry_delay)
            elif "invalid api key" in error_msg or "authentication" in error_msg:
                print("❌ API 키가 유효하지 않습니다. .env 파일을 확인하세요.")
                break
            elif "quota" in error_msg or "limit" in error_msg:
                print(f"⏳ API 사용량 한도 초과. {retry_delay}초 후 재시도...")
                time.sleep(retry_delay)
            else:
                print(f"🚨 Gemini API 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise

    print(f"{max_retries}번 시도 후 실패. 총 소요시간: {time.time() - start_time:.2f}초")
    return None

def create_news_analysis_prompt(combined_text: str) -> str:
    """
    뉴스 분석을 위한 통합 프롬프트 생성
    """
    return f"""
너는 국내 상장사와 주요 산업 분석에 특화된 금융 뉴스 분석 전문가야.

{combined_text}

뉴스 기사에 대해, 기계적 추출이 아닌 **생성적 요약**으로 다음 항목들을 JSON 형식으로 분석해주세요:

1. overall_sentiment: 전체적인 시장 감정 (positive/negative/neutral)
2. sentiment_score: 감정 점수 (-100 ~ +100, 숫자로만)
3. key_themes: 주요 테마들 (배열)
4. market_impact: 시장에 미칠 영향 예측 (2-3문장)
5. summary: 전체 뉴스 요약 (3-4문장)
6. investment_signals: 투자 시그널 (buy/sell/hold)

### 출력 형식 (JSON)
{{
  "overall_sentiment": "positive/negative/neutral",
  "sentiment_score": 숫자,
  "key_themes": ["테마1", "테마2", "테마3"],
  "market_impact": "시장 영향 분석",
  "summary": "전체 뉴스 요약",
  "investment_signals": "buy/sell/hold"
}}

### 분석 가이드라인:
• 답변 형식: 반드시 유효한 JSON 구조로 작성해주세요
• 언어: 한국어로 자연스럽게 작성
• 분석 스타일: 객관적이고 균형잡힌 관점 유지
• 근거: 실제 데이터와 시장 동향에 기반한 분석
• 투자 조언: 과도한 투기보다는 신중한 투자 관점 제시

응답은 반드시 JSON 형식으로만 해주세요.
"""

def ask_news_analysis(prompt, max_retries=3):
    """
    뉴스 분석 전용 Gemini API 호출 함수
    JSON 응답을 기대하는 뉴스 분석에 최적화
    """
    return ask_question_to_gemini_cache(prompt, max_retries=max_retries)

def create_research_reports_analysis_prompt(combined_text: str) -> str:
    """
    리서치 리포트 분석을 위한 통합 프롬프트 생성
    """
    return f"""
너는 국내 증권사 리서치 분석에 특화된 금융 전문가야.

다음 네이버 증권 리서치 뉴스와 리포트들을 카테고리별로 분석해주세요:

{combined_text}

뉴스와 리포트에 대해, 종합적이고 심층적인 분석으로 다음 항목들을 JSON 형식으로 분석해주세요:

1. category_summary: 카테고리별 요약 (각 카테고리당 2-3문장씩, 객체 형태)
2. top_mentioned_stocks: 가장 많이 언급된 종목들 (배열, 최대 10개)
3. key_industries: 주요 관심 산업/섹터들 (배열, 최대 8개)
4. investment_themes: 주요 투자 테마들 (배열, 최대 8개)
5. market_outlook: 전체 시장 전망 (bullish/bearish/neutral)
6. risk_factors: 주요 리스크 요인들 (배열, 각 한 문장, 최대 5개)
7. opportunities: 투자 기회들 (배열, 각 한 문장, 최대 5개)
8. analyst_consensus: 애널리스트들의 전반적 합의 사항 (2-3문장)
9. summary: 전체 리포트 종합 분석 (4-5문장)

### 출력 형식 (JSON)
{{
  "category_summary": {{
    "종목분석": "종목분석 카테고리 요약 2-3문장",
    "산업분석": "산업분석 카테고리 요약 2-3문장",
    "시황정보": "시황정보 카테고리 요약 2-3문장",
    "투자정보": "투자정보 카테고리 요약 2-3문장"
  }},
  "top_mentioned_stocks": ["종목1", "종목2", "종목3"],
  "key_industries": ["산업1", "산업2", "산업3"],
  "investment_themes": ["테마1", "테마2", "테마3"],
  "market_outlook": "bullish/bearish/neutral",
  "risk_factors": ["리스크 요인 1", "리스크 요인 2"],
  "opportunities": ["투자 기회 1", "투자 기회 2"],
  "analyst_consensus": "애널리스트 합의 사항 2-3문장",
  "summary": "전체 종합 분석 4-5문장"
}}

### 분석 가이드라인:
• 답변 형식: 반드시 유효한 JSON 구조로 작성해주세요
• 언어: 한국어로 자연스럽게 작성
• 분석 스타일: 객관적이고 전문적인 관점 유지
• 근거: 실제 리포트 내용과 시장 동향에 기반한 분석
• 투자 조언: 신중하고 균형잡힌 투자 관점 제시
• 완성도: 모든 9개 항목을 빠짐없이 포함해야 함

응답은 반드시 JSON 형식으로만 해주세요.
"""

def create_individual_news_analysis_prompt(news_item: dict) -> str:
    """
    개별 뉴스 분석을 위한 프롬프트 생성
    """
    title = news_item.get('title', '')
    content = news_item.get('content', '')

    # 내용이 없으면 제목만 사용
    text_to_analyze = content if content.strip() else title

    return f"""
너는 국내 상장사와 주요 산업 분석에 특화된 금융 뉴스 분석 전문가야.

다음 뉴스 기사를 분석해주세요:

제목: {title}
내용: {text_to_analyze[:500]}

뉴스 기사에 대해, 기계적 추출이 아닌 **생성적 요약**으로 다음 항목들을 JSON 형식으로 분석해주세요:

1. summary: 주요 이슈 한 문장 요약
2. entities: 관련 기업명과/또는 업종명 명시
3. impact: 업계·시장 파급 영��� 또는 의미 부각
4. type: 기업 또는 산업 (정확히 이 두 단어 중 하나만)
5. reason: 이 기사 분류의 근거 (기업/산업)

### 분류 지침:
- 특정 기업(예: 삼성전자, 현대차 등)에 대한 기사면 "type": "기업"으로,
- 정부 정책, 산업 정책, 경제 지표(금리, 환율 등), 법/제도, 또는 특정 산업 전체에 대한 기사면 "type": "산업"으로 분류.
- 분류 사유는 기사 내용 근거를 1문장으로 명확히 설명할 것.

### 출력 형식 (JSON)
{{
  "summary": "<주요 이슈 한 문장 요약>",
  "entities": "<관련 기업명과/또는 업종명 명시>",
  "impact": "<업계·시장 파급 영향 또는 의미 부각>",
  "type": "기업 또는 산업",
  "reason": "<이 기사 분류의 근거 (기업/산업)>"
}}

### 분석 가이드라인:
• 답변 형식: 반드시 유효한 JSON 구조로 작성해주세요
• 언어: 한국어로 자연스럽게 작��
• 분석 스타일: 객관적이고 균형잡힌 관점 유지
• 근거: 실제 데이터와 시장 동향에 기반한 분석
• 투자 조언: 과도한 투기보다는 신중한 투자 관점 제시

응답은 반드시 JSON 형식으로만 해주세요.
"""

def json_match(input_string):
    """
    Use regex to extract JSON from a string.
    """
    if not input_string:
        return None

    print("응답 텍스트에서 JSON 추출 시도...")

    # 1. 백틱으로 감싸진 JSON 찾기 (개선된 regex 사용)
    pattern_backticks = r'```json\s*(\{.*?\})\s*```'
    m = re.search(pattern_backticks, input_string, re.DOTALL)
    if m:
        json_str = m.group(1)
        try:
            result = json.loads(json_str)
            print("백틱 JSON 추출 성공")
            return result
        except json.JSONDecodeError as e:
            print(f"백틱 JSON 파싱 실패: {e}")
            # 손상된 JSON 복구 시도
            fixed_json = _try_fix_json(json_str)
            if fixed_json:
                return fixed_json

    # 2. regex 라이브러리가 있다면 고급 패턴 사용
    try:
        pattern_simple = r'(\{(?:[^{}]|(?R))*\})'
        m = regex.search(pattern_simple, input_string)
        if m:
            json_str = m.group(1)
            try:
                result = json.loads(json_str)
                print("고급 regex JSON 추출 성공")
                return result
            except json.JSONDecodeError as e:
                print(f"고급 regex JSON 파싱 실패: {e}")
                # 손상된 JSON 복구 시도
                fixed_json = _try_fix_json(json_str)
                if fixed_json:
                    return fixed_json
    except NameError:
        # regex 라이브러리가 없는 경우 기본 패턴 사용
        pass

    # 3. 기본 re 모듈로 간단한 패턴 시도
    try:
        # 여러 JSON 객체를 찾아서 가장 완전한 것 선택
        json_candidates = []

        # 모든 { } 찾기
        brace_count = 0
        start_pos = -1

        for i, char in enumerate(input_string):
            if char == '{':
                if brace_count == 0:
                    start_pos = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_pos != -1:
                    json_candidate = input_string[start_pos:i+1]
                    json_candidates.append(json_candidate)

        # 가장 긴 JSON 후보를 먼저 시도
        json_candidates.sort(key=len, reverse=True)

        for json_str in json_candidates:
            try:
                result = json.loads(json_str)
                print("기본 JSON 추출 성공")
                return result
            except json.JSONDecodeError:
                # 손상된 JSON 복구 시도
                fixed_json = _try_fix_json(json_str)
                if fixed_json:
                    return fixed_json
                continue

    except Exception as e:
        print(f"기본 JSON 파싱 중 오류: {e}")

    print("JSON 추출 실패")
    return None

def _try_fix_json(json_str: str) -> Optional[dict]:
    """
    손상된 JSON을 복구하려고 시도
    """
    print("손상된 JSON 복구 시도...")

    try:
        # 1. 흔한 문제들 수정
        fixed_str = json_str

        # 잘못된 키 이름 패턴 수정 (예: "텍스트key": -> "key":)
        import re
        fixed_str = re.sub(r'"[^"]*[가-힣][^"]*([a-zA-Z_][a-zA-Z0-9_]*)":', r'"\1":', fixed_str)

        # 중간에 끊어진 문자열 + 키 패턴 수정
        fixed_str = re.sub(r'"[^"]*"([a-zA-Z_][a-zA-Z0-9_]*)":', r'", "\1":', fixed_str)

        # 잘 구분된 쉼표 패턴 수정
        fixed_str = re.sub(r',\s*}', '}', fixed_str)
        fixed_str = re.sub(r',\s*]', ']', fixed_str)

        # 2. JSON 파싱 재시도
        result = json.loads(fixed_str)
        print("JSON 복구 성공!")
        return result

    except json.JSONDecodeError as e:
        print(f"JSON 복구 실패: {e}")

        # 3. 부분 복구 시도 - 유효한 필드만 추출
        try:
            partial_data = {}

            # 간단한 키-값 쌍 추출
            simple_patterns = [
                (r'"([^"]+)":\s*"([^"]*)"', str),  # 문자열 값
                (r'"([^"]+)":\s*(\d+(?:\.\d+)?)', float),  # 숫자 값
                (r'"([^"]+)":\s*(true|false)', bool),  # 불린 값
            ]

            for pattern, value_type in simple_patterns:
                matches = re.findall(pattern, json_str)
                for key, value in matches:
                    try:
                        if value_type == bool:
                            partial_data[key] = value.lower() == 'true'
                        elif value_type == float:
                            partial_data[key] = float(value)
                        else:
                            partial_data[key] = value
                    except:
                        continue

            if partial_data:
                print(f"부분 JSON 복구 성공: {len(partial_data)}개 필드")
                return partial_data

        except Exception as e:
            print(f"부분 복구도 실패: {e}")

    return None