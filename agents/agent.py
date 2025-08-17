from dotenv import load_dotenv
import os
from google.adk.agents import Agent, LlmAgent, SequentialAgent, ParallelAgent
from google.adk.runners import Runner
from google.genai import types
from google.adk.sessions import InMemorySessionService


from .sub_agents.sub_agent import *
from .tools import *

os.environ['OTEL_TRACES_EXPORTER'] = 'none' # Disable OpenTelemetry traces
load_dotenv()
MODEL = "gemini-2.0-flash"

APP_NAME = "news_app"
USER_ID = "1234"
SESSION_ID = "session1234"


# policy + competitiveness 판단 파이프라인
# policy_pipeline_agent = SequentialAgent(
#     name="PolicyPipelineAgent",
#     sub_agents=[policy_agent, competitiveness_agent]
# )

# # 회사 중심(company), 업종 중심(policy) 병렬로 처리
# company_policy_agent = ParallelAgent(
#     name="CompanyPolicyAgent",
#     sub_agents=[company_agent, policy_pipeline_agent]
# )


root_agent = SequentialAgent(
    name="StockTradingWorkflow",
    description="매매할 주식을 추천해주는 Agent",
    sub_agents=[company_agent, policy_agent, competitiveness_agent, analyze_agent],
)





# root_agent = LlmAgent(
#     model=MODEL,
#     name="StockAgent",
#     description="정보 수집 Agent",
#     instruction="""
    
#     너는 특정 단어에 대해, 추가적인 인터넷 검색을 통해 정보를 수집하여 전달해주는 전문가야.
    
#     반드시, adk_tavily_tool 을 이용해서 인터넷 검색을 수행한 결과를 이용해야 해.
#     """,
#     tools=[adk_tavily_tool]
# )

async def setup_session_and_runner():
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
    return session, runner

# Agent Interaction
async def call_agent_async(query):
    content = types.Content(role='user', parts=[types.Part(text=query)])
    session, runner = await setup_session_and_runner()
    events = runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

    async for event in events:
        if event.is_final_response() and event.author == "AnalysisAgent":
            final_response = event.content.parts[0].text
            print("Agent Response: ", final_response)
            return final_response


if __name__ == "__main__":
    import asyncio
    query = """
    국내 방산주가 급등하면서 글로벌 1위 방산 업체인 미국 록히드마틴보다 고평가된 것으로 나타났다. 국내 방산주 주가가 지나치게 높은 수준이라고 판단했는지, 외국인은 이달 주요 방산주를 순매도하고 있다.

한화에어로스페이스(881,000원 ▼ 51,000 -5.47%), LIG넥스원(513,000원 ▼ 90,000 -14.93%), 현대로템(183,500원 ▼ 9,400 -4.87%), 한국항공우주(90,800원 ▼ 2,700 -2.89%), 한화시스템(52,800원 ▼ 3,900 -6.88%) 등 주요 방산주는 올해 들어 주가가 70~300% 급등했다. 주요국이 국방비를 증액하는 가운데 국내 업체의 수출이 증가하면서 실적 기대가 커진 결과다.

하지만 주가 상승세가 지나치게 가팔라 실적 대비 주가가 과열됐다는 경고도 나온다.
    """
    final_response = asyncio.run(call_agent_async(query))
    print(f"FINAL RESPONSE: {final_response}\n")