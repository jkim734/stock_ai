from gemini import *
import json


def classify_llm(article: str):
    """
    특정 종목 기사 / 정책 기사 분류
    """
    prompt = """
너는 뉴스 기사 분류 전문가야.  
너의 임무는 주어진 뉴스 기사가 **특정 기업에 영향을 주는 기사인지**, 아니면 **산업 전체 또는 업종에 영향을 주는 정책 관련 기사인지**를 판단하는 거야.  

### 분류 기준은 다음과 같아:

- 특정 기업 이름(예: 삼성전자, LG에너지솔루션 등)이 **직접적으로** 기사에 언급되고,  
  기업의 실적, 제품, 이슈 등이 주요 내용일 경우 → `"경제 기사"`

- 정부 정책, 규제 변화, 지원책, 세금 제도 등 **업종 전체**에 영향을 줄 수 있는 내용일 경우 → `"정책 기사"`

- 두 경우에 해당하지 않거나 판단이 어려울 경우 → `"불분명"`

---

### 다음 주의사항을 꼭 고려해서 답변해줘:
1. 위에 정의해놓은 **경제 기사** 또는 **정책 기사** 둘 중 확실하게 하나로 분류되는 기사가 아니면 억지로 분류하지 말고 **불분명** 으로 답해줘야 해.

---

### 출력 형식은 아래 JSON으로 정확히 맞춰줘:

```json
{{
  "category": "경제 기사" 또는 "정책 기사" 또는 "불분명",
  "reason": "<이 기사를 그렇게 분류한 이유를 간단하고 명확하게 설명>"
}}

---

### 기사: 
{}
    """.format(article)
    
    answer = ask_question_to_gemini_cache(prompt)
    answer_dict = json_match(answer)
    print(answer_dict)
    
    return answer_dict['category']

def policy_llm(article: str):
    
    """
    정책 관련 기사에서 수혜/피해 category 분석
    """
    
    prompt = """
너는 기사 분석 전문가이자 산업 분석가야.  
너의 임무는 주어진 기사 내용을 바탕으로,  
해당 정책이 어떤 업종(산업 분야)에 수혜를 줄 수 있고,  
어떤 업종에는 피해나 부정적 영향을 줄 수 있는지를 추론하는 것이야.  

### 다음 기준을 참고해 판단해줘:

1. **정책의 주요 내용**을 정확히 요약하고,
2. **직접적인 영향**을 받는 업종을 우선 고려하고,
3. **간접적인 파급 효과**도 신중히 고려해 판단하며,
4. 각 업종에 대해 수혜인지, 피해인지, 중립인지 분류하고,
5. 그 이유도 간단히 설명해줘.


### 다음 주의사항을 꼭 고려해서 답변해줘:

1. 다른 정보는 제외하고, 기사에서 알 수 있는 내용만 판단의 근거로 사용해줘.
2. 기사의 내용만을 근거로 했을 때, 명확하게 **수혜** 또는 **피해**가 예상되는 경우에만 수혜 또는 피해 로 판단해줘.
3. 여러 요인이 혼재되어 있는 경우에는, 그냥 "불분명" 으로 판단해주는게 좋아.
4. 너무 많은 업종을 나열하기보다는, **가장 핵심적인 업종** 2~3개에 집중해서 판단해줘.


### 출력 형식은 다음과 같아:

```json
{{
  "summary": "<정책의 핵심 내용을 간결히 요약>",
  "positive": [
    {{"category": "업종1", "reason": "수혜를 입는 이유"}},
    {{"category": "업종2", "reason": "수혜를 입는 이유"}}
  ],
  "negative": [
    {{"category": "업종A", "reason": "피해를 입는 이유"}},
    {{"category": "업종B", "reason": "피해를 입는 이유"}}
  ],
  "중립_또는_영향_불분명": [
    {{"category": "업종X", "reason": "영향이 명확하지 않거나 중립적인 이유"}}
  ]
}}

### 기사: 
{}
    """.format(article)
    answer = ask_question_to_gemini_cache(prompt)
    json_dict = json_match(answer)
    print(f"policy_llm answer: {json_dict}")
    return json_dict['positive']


def competitive_llm(category: str, reason: str, article: str):
    prompt = """
너는 산업 분석 전문가이자 국내 상장기업 분석에 특화된 리서치 애널리스트야.
정책 관련 기사 분석 전문가가 호재 업종으로 판단한 업종과 그 근거를 바탕으로,
해당 업종에서 경쟁우위를 가진 대표 국내 상장사 1~2개를 선정하고 그 이유를 명확하게 설명해주는 것이 너의 임무야.
아래 업종(Category) 및 최근 업계 기사들을 바탕으로, 해당 업종에서 경쟁우위를 가진 대표 국내 상장사 1~2개를 선정하고 그 이유를 명확하게 설명해줘.

### 판단 기준:
- 시장 점유율  
- 기술력  
- 성장성  
- 정부 정책 수혜 가능성  
- 실적/재무 안정성  
- 글로벌 진출 여부 등 종합 평가  
- 기사 내 정보 기준으로 합리적 추론 수준에서 설명  
- 국내 상장사 대상

### 출력 형식은 아래 JSON으로 정확히 맞춰줘:
```json
{{
  "category": "업종명",
  "companies": [
    {{
      "company": "기업명1",
      "reason": "이유1"
    }},
    {{
      "company": "기업명2",
      "reason": "이유2"
    }}
  ]
}}

---
업종:
{}

호재 판단 이유:
{}

관련 기사:
{}

    """.format(category, reason, article)
    answer = ask_question_to_gemini_cache(prompt)
    answer_dict = json_match(answer)
    print(f"competitive_llm answer: {answer_dict}")
    return answer_dict
    
    
def company_llm(article: str):
    prompt = """
너는 기업 뉴스 분석 전문가야.

다음에 제공되는 뉴스 기사를 읽고, 해당 기사가 어떤 기업에 대해  
**호재(긍정적), 악재(부정적), 중립(영향 없음 또는 혼재)** 중 무엇으로 평가할 수 있는지 판단해줘.

### 규칙
1. 확실하게 호재 또는 악재인 경우에만 호재/악재로 판단하고, 애매하거나 호재, 악재가 혼재되어 있는 경우에는 **중립** 으로 판단해줘.
2. company 필드에는 정확하게 **기업명** (삼성전자, 현대자동차 등) 만 넣어줘.

반드시 다음 형식으로만 출력해:

```json
{{
  "company": "<기업명>",
  "eval": "호재" 또는 "악재" 또는 "중립",
  "reason": "<기사 내용을 근거로 판단한 간결한 설명>"
}}

---

뉴스 기사:
{}
    
    """.format(article)
    answer = ask_question_to_gemini_cache(prompt)
    answer_dict = json_match(answer)
    print(f"company_llm answer: {answer_dict}")
    return answer_dict
    


if __name__ == "__main__":
    # article = """
    # 정부는 새로운 환경 보호 정책을 발표했습니다. 이 정책은 재생 가능 에너지 산업에 큰 수혜를 줄 것으로 예상되며, 특히 태양광 및 풍력 발전 업종이 가장 큰 혜택을 볼 것입니다. 반면, 석유 및 가스 산업은 이 정책으로 인해 부정적인 영향을 받을 것으로 보입니다. 또한, 전통적인 제조업체들은 이 정책의 영향이 불분명하여 중립적인 입장에 있을 것으로 판단됩니다.
    # """
    article = """
    
    """
    print(policy_llm(article))
    # print(classify_llm(article))
    # competitive_llm("2차전지", article)
    # company_llm(article)
    