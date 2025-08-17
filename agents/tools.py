from google.adk.tools import google_search
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import mojito
import pandas_ta as ta
import pandas as pd
from urllib.parse import quote
import yfinance as yf
from google.adk.tools.crewai_tool import CrewaiTool
from crewai_tools import SerperDevTool

from google.adk.tools.langchain_tool import LangchainTool
from langchain_community.tools import TavilySearchResults

load_dotenv()
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
ACC_NUM = os.getenv('ACC_NUM')

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

SERPER_API_KEY = os.getenv("TAVILY_API_KEY")

broker = mojito.KoreaInvestment(
    api_key=API_KEY,
    api_secret=SECRET_KEY,
    acc_no=ACC_NUM,
    mock=True
)

tavily_tool_instance = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True,
    include_images=False,
)

adk_tavily_tool = LangchainTool(
    tool=tavily_tool_instance,
    name="InternetSearchTool",
    description="특정 키워드에 대해 인터넷 검색을 해 주는 도구"
)

from datetime import datetime, timedelta

def summarize_indicators(df: pd.DataFrame, ticker: str = "", close: str = "Close") -> str:
    """
    기술적 지표가 포함된 DataFrame을 받아 요약 텍스트를 생성합니다.
    """
    latest = df.dropna().iloc[-1]  # NaN 포함 지표 제외하고 최신값 사용
    summary = []

    summary.append(f"[{ticker} 기술적 지표 요약]")

    # RSI
    rsi = latest["rsi"]
    if rsi > 70:
        summary.append(f"- RSI({rsi:.1f}): 과매수 구간")
    elif rsi < 30:
        summary.append(f"- RSI({rsi:.1f}): 과매도 구간")
    else:
        summary.append(f"- RSI({rsi:.1f}): 중립")

    # MACD
    macd = latest["macd"]
    summary.append(f"- MACD({macd:.2f}): {'양전환' if macd > 0 else '음전환'} 상태")

    # 볼린저밴드
    close = latest[close]
    bb_upper = latest["bb_upper"]
    bb_lower = latest["bb_lower"]
    if close >= bb_upper * 0.98:
        summary.append("- 주가가 볼린저밴드 상단에 근접 → 단기 과열 가능성")
    elif close <= bb_lower * 1.02:
        summary.append("- 주가가 볼린저밴드 하단에 근접 → 단기 반등 가능성")

    # 이평선
    sma20 = latest["sma20"]
    if close > sma20:
        summary.append(f"- 20일 이평선({sma20:.2f})보다 현재가({close:.2f})가 높음 → 상승 추세")
    else:
        summary.append(f"- 20일 이평선({sma20:.2f})보다 현재가({close:.2f})가 낮음 → 하락 또는 횡보 추세")

    return "\n".join(summary)


def get_stock_data(ticker: str) -> str:
    """
    기술적 지표를 계산하여 해당 종목의 기술적 지표 요약 분석 결과를 도출하는 도구.

    Args:
        ticker (str): 조회할 종목의 Ticker 코드 (예: '005930.KS')

    Returns:
        str: 기술적 지표(RSI, MACD, 볼린저밴드, 이동평균선)를 기반으로 생성된 종목 요약 분석 보고서입니다.
    """
    
    end_date = datetime.today()
    start_date = end_date - timedelta(days=60)
    
    df = yf.download(
        ticker,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=False
    )
    # 컬럼 정리
    
    try:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [' '.join(col).strip() for col in df.columns.values]

        # 유효한 Close 컬럼 자동 감지
        close_col = next((col for col in df.columns if 'Close' in col and 'Adj' not in col), None)
        if not close_col:
            raise ValueError("Close 컬럼을 찾을 수 없습니다.")
            
        # 기술적 지표 추가
        df["rsi"] = ta.rsi(df[close_col], length=14)
        macd = ta.macd(df[close_col])
        df["macd"] = macd["MACD_12_26_9"]
        bb = ta.bbands(df[close_col], length=20)
        df["bb_upper"] = bb["BBU_20_2.0"]
        df["bb_lower"] = bb["BBL_20_2.0"]
        df["sma20"] = ta.sma(df[close_col], length=20)
        print(df)

        return summarize_indicators(df, ticker=ticker, close=close_col)
    except Exception as e:
        return f"error: {e}"







from dataclasses import dataclass
import html
import time

@dataclass
class NewsItem:
    title: str
    description: str
    press: str
    date: str
    link: str

def clean_text(text: str) -> str:
    """HTML 태그 및 엔티티 제거"""
    return BeautifulSoup(html.unescape(text), "html.parser").get_text(strip=True)

def search_naver_news(keyword: str, page: int = 1, sort: int = 1) -> Dict:
    """
    특정 keyword 대해 Naver News에 검색을 수행하고, 결과로 뉴스 본문을 반환합니다.

    Args:
        keyword (str): 검색할 기업 이름
        page (int): 페이지 번호 (1부터 시작)
        sort (int): 정렬 기준 (1: 최신순, 2: 관련도 순)

    Returns:
        Dict: 뉴스 본문 딕셔너리
    """

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'X-Naver-Client-Id': NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': NAVER_CLIENT_SECRET
    }

    params = {
        'query': keyword,
        'start': (page - 1) * 10 + 1,
        'display': 10,
        'sort': 'date' if sort == 1 else 'sim'
    }

    response = requests.get('https://openapi.naver.com/v1/search/news.json', headers=headers, params=params)
    data = response.json()

    descriptions = [
        clean_text(item["description"])
        for item in data.get("items", [])
        if "description" in item
    ]

    return {"status": "success", "message": f"{descriptions}"}

    



if __name__ == "__main__":
    print(search_naver_news("삼성전자"))