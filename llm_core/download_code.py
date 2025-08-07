from pykrx import stock
import pandas as pd

# 오늘 날짜 기준 (필요 시 날짜 고정도 가능)
today = pd.Timestamp.today().strftime("%Y%m%d")

# 코스피 시총 상위 100개 가져오기
df_kospi = stock.get_market_cap_by_ticker(today, market="KOSPI")
df_kospi = df_kospi.sort_values("시가총액", ascending=False).head(100)

# 종목명 매핑
df_kospi["name"] = df_kospi.index.map(stock.get_market_ticker_name)

# 필요한 컬럼만
result = df_kospi[["name"]].reset_index()  # index가 종목코드
result.columns = ["code", "name"]

result.to_csv("llm_core/stock_list.csv", index=False, encoding="utf-8-sig")

