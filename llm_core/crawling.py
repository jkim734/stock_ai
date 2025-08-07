import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote
from dataclasses import dataclass
from typing import List, Optional
import json

@dataclass
class NewsItem:
    title: str
    description: str
    press: str
    date: str
    link: str

def clean_text(text: str) -> str:
    return ' '.join(BeautifulSoup(text, 'html.parser').get_text().split()).strip()

def crawl_naver_news_by_keyword(keyword: str, page: int = 1, sort: int = 1) -> List[NewsItem]:
    
    """
    Naver News 검색 결과 페이지를 파싱하여 뉴스 아이템 리스트를 반환합니다.
    :param keyword: 검색할 키워드
    :param page: 페이지 번호 (1부터 시작)
    :param sort: 정렬 기준 (1: 최신순, 2: 관련도 순)
    :return: 뉴스 아이템 리스트
    """
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept-Language': 'ko-KR,ko;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    encoded_keyword = quote(keyword)
    url = f"https://search.naver.com/search.naver?&where=news&query={encoded_keyword}&start={(page - 1) * 10 + 1}&sort={sort}"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    news_items = []
    news_sections = soup.find_all('div', class_='_sghYQmdqcpm83O1jqen')

    for section in news_sections:
        try:
            title_elem = section.find('span', class_=lambda x: x and 'sds-comps-text-type-headline1' in x)
            desc_elem = section.find('span', class_='sds-comps-text-ellipsis-3')
            press_elem = section.find('span', class_='sds-comps-profile-info-title-text')
            date_elem = section.find('div', class_='rHjTun31Lu4itQfimkB3')

            if not title_elem:
                continue

            title = clean_text(title_elem.get_text())
            description = clean_text(desc_elem.get_text()) if desc_elem else ''
            press = clean_text(press_elem.get_text()) if press_elem else 'Unknown'
            date = clean_text(date_elem.get_text()) if date_elem else 'Unknown'

            news_items.append(NewsItem(
                title=title,
                description=description,
                press=press,
                date=date,
                link=url  # 개별 뉴스 링크는 URL 파싱 안 됨 (뉴스 본문 링크 필요시 수정 가능)
            ))
        except Exception:
            continue
    
    # print(f"Crawling results: {news_items}")
    return news_items

if __name__ == "__main__":
    news_items = crawl_naver_news_by_keyword("삼성전자", page=1, sort=1)
    for item in news_items:
        print(f"Title: {item.title}\nDescription: {item.description}\nPress: {item.press}\nDate: {item.date}\nLink: {item.link}\n")
