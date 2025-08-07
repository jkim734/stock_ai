from dotenv import load_dotenv
import os
from google.adk.agents import Agent, LlmAgent, SequentialAgent, ParallelAgent


from .sub_agents.sub_agent import company_agent, policy_agent, competitiveness_agent, analyze_agent

load_dotenv()
MODEL = "gemini-2.0-flash"


# policy + competitiveness 판단 파이프라인
policy_pipeline_agent = SequentialAgent(
    name="PolicyPipelineAgent",
    sub_agents=[policy_agent, competitiveness_agent]
)

# 회사 중심(company), 업종 중심(policy) 병렬로 처리
company_policy_agent = ParallelAgent(
    name="CompanyPolicyAgent",
    sub_agents=[company_agent, policy_pipeline_agent]
)



# root_agent = Agent(
#     model=MODEL,
#     name="StockTradingWorkflow",
#     description="매매할 주식을 추천해주는 Agent",
#     instruction="""
#     당신은 자동화된 주식 매매 의사결정 시스템의 핵심 에이전트입니다.

#     당신의 역할은 다음과 같습니다:
#     1. 기술적 지표 분석 에이전트 및 뉴스 분석 에이전트의 결과를 종합하여, 특정 종목에 대한 매수 또는 매도 여부를 판단합니다.
#     2. 필요시 직접 기술적 분석, 뉴스 요약 툴을 호출하여 추가 정보를 수집할 수 있습니다.
#     3. 판단 근거를 명확히 제시하며, 판단 결과는 structured output 형식으로 아래와 같이 반환합니다:

#     [Example]
#     {
#     "company": "삼성전자"
#     "action": "BUY or SELL or HOLD",
#     "confidence": 0~1,
#     "reason": "간결한 판단 근거",
#     "related_indicators": {"RSI": 28, "MA20": "상승"},
#     "news_sentiment": "호재" 
#     }

#     규칙:
#     - 뉴스가 악재일 경우 매수를 보류하고, 호재일 경우 매수를 지지하세요.
#     - 툴 호출을 통해 정보를 충분히 확보한 후 판단하세요.
#     - 판단이 어려울 경우 HOLD를 반환하세요.

#     당신의 목표는 수익률을 극대화하면서도 신중하고 근거 있는 결정을 내리는 것입니다.
#     """,
#     sub_agents=[company_agent, policy_pipeline_agent, analyze_agent]
# )

root_agent = SequentialAgent(
    name="StockTradingWorkflow",
    description="매매할 주식을 추천해주는 Agent",
    sub_agents=[company_policy_agent, analyze_agent]
)