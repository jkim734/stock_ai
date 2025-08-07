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

load_dotenv()
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
ACC_NUM = os.getenv('ACC_NUM')

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

broker = mojito.KoreaInvestment(
    api_key=API_KEY,
    api_secret=SECRET_KEY,
    acc_no=ACC_NUM,
    mock=True
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


def get_stock_data(ticker: str) -> pd.DataFrame:
    """
    기술적 지표를 계산하여 해당 종목의 기술적 지표 요약 분석 리포트를 반환합니다.

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
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [' '.join(col).strip() for col in df.columns.values]

    # 유효한 Close 컬럼 자동 감지
    close_col = next((col for col in df.columns if 'Close' in col and 'Adj' not in col), None)
    if not close_col:
        raise ValueError("Close 컬럼을 찾을 수 없습니다.")
        
    # 기술적 지표 추가
    df["rsi"] = ta.rsi(df[close_col], length=14)
    macd = ta.macd(df[close_col])
    print(macd)
    df["macd"] = macd["MACD_12_26_9"]
    bb = ta.bbands(df[close_col], length=20)
    df["bb_upper"] = bb["BBU_20_2.0"]
    df["bb_lower"] = bb["BBL_20_2.0"]
    df["sma20"] = ta.sma(df[close_col], length=20)

    return summarize_indicators(df, ticker=ticker, close=close_col)







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

def search_naver_news(keyword: str, page: int = 1, sort: int = 1) -> List[str]:
    """
    기업 종목에 대해 Naver News에 검색을 수행하고, 결과로 뉴스 본문을 반환합니다.

    Args:
        keyword (str): 검색할 기업 이름
        page (int): 페이지 번호 (1부터 시작)
        sort (int): 정렬 기준 (1: 최신순, 2: 관련도 순)

    Returns:
        List[str]: 뉴스 본문 리스트
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

    return descriptions
    
    



if __name__ == "__main__":
    # 예시: 네이버 금융에서 삼성전자 관련 리포트 검색
    
    # kospi = broker.fetch_kospi_symbols()
    # ticker_name_map = dict(zip(kospi['한글명'], kospi['단축코드']))
    # print(ticker_name_map)
    # print(ticker_name_map['삼성전자'])
    
    # reports = search_naver_news('삼성전자')
    # print(len(reports), "reports found for 삼성전자")
    # for report in reports:
    #     print(report)
    print(get_stock_data("005930.KS"))