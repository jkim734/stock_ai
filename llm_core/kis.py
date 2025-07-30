from dotenv import load_dotenv
import os
import mojito
import pprint
import time

load_dotenv()
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
ACC_NUM = os.getenv('ACC_NUM')

broker = mojito.KoreaInvestment(
    api_key=API_KEY,
    api_secret=SECRET_KEY,
    acc_no=ACC_NUM,
    mock=True
)

def buy_stock(symbol: str, quantity: int = 1):
    
    prices = []
    
    # 1초 간격으로 3번 시세 받아와서 그 중 최저가로 지정가 매수
    for _ in range(3):
        resp = broker.fetch_price(symbol)
        prices.append(int(resp['output']['stck_prpr']))
        print(resp)
        time.sleep(1)
    
    price = min(prices)
    response = broker.create_limit_buy_order(
        symbol=symbol,
        price=price,
        quantity=quantity
    )
    pprint.pprint(response)

def sell_stock(symbol: str, quantity: int, price: int):

    response = broker.create_limit_sell_order(
        symbol=symbol,
        price=price,
        quantity=quantity
    )
    pprint.pprint(response)
    
if __name__ == "__main__":
    buy_stock("005930", 1)
    
    print(broker.fetch_balance())