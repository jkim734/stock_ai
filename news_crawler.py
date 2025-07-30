"""
네이버 증권 뉴스 및 리서치 크롤링 모듈
"""

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from typing import List, Dict
import logging

# 로깅 설정 (간단한 진행 상황 표시)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class NaverStockNewsCrawler:
    """네이버 증권 뉴스 크롤러"""

    def __init__(self):
        self.base_url = "https://finance.naver.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_main_news(self, limit: int = 10) -> List[Dict]:
        """
        네이버 증권 메인 뉴스 크롤링

        Args:
            limit: 가져올 뉴스 개수

        Returns:
            List[Dict]: 뉴스 정보 리스트
        """
        news_list = []

        try:
            # 네이버 증권 뉴스 페이지 URL
            url = "https://finance.naver.com/news/"
            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 네이버 증권 뉴스 페이지의 다양한 선택자 시도
            news_selectors = [
                '.newslist .articleSubject a',  # 뉴스 리스트의 기사 제목
                '.newsList .articleSubject a',
                '.articleSubject a',            # 기본 기사 제목
                '.news_list .subject a',        # 뉴스 리스트 제목
                '.type2 .subject a',            # type2 스타일의 제목
                '.headline_list .subject a',    # 헤드라인 리스트
                '.articleSubject',              # 제목 요소 자체
                'td.subject a',                 # 테이블 형태의 제목
                '.tb_type1 .subject a',         # 테이블 type1의 제목
                'a[href*="news_read"]',         # 뉴스 읽기 링크 포함
            ]

            news_items = []
            found_selector = None

            for selector in news_selectors:
                try:
                    items = soup.select(selector)
                    if items and len(items) >= 5:  # 최소 5개 이상의 뉴스가 있어야 유효
                        news_items = items[:limit]
                        found_selector = selector
                        logger.info(f"뉴스 리스트 발견: {len(news_items)}개")
                        break
                except Exception as e:
                    logger.error(f"선택자 '{selector}' 시도 중 오류: {e}")
                    continue

            if not news_items:
                # 모든 링크를 찾아서 뉴스 링크 필터링
                logger.info("기본 선택자 실패, 모든 링크에서 뉴스 링크 찾기 시도...")
                all_links = soup.find_all('a', href=True)
                news_links = []

                for link in all_links:
                    href = link.get('href', '')
                    title = link.get_text(strip=True)

                    # 뉴스 링크 패턴 확인
                    if ('news_read' in href or 'article_id' in href) and title and len(title) > 10:
                        news_links.append(link)
                        if len(news_links) >= limit:
                            break

                if news_links:
                    news_items = news_links
                    logger.info(f"필터링을 통해 {len(news_items)}�� 뉴스 링크 발견")
                else:
                    logger.warning("뉴스 리스트를 찾을 수 없습니다.")
                    return news_list

            # 뉴스 항목 처리
            for idx, item in enumerate(news_items):
                try:
                    # 링크 요소 확인
                    if item.name == 'a':
                        title_element = item
                    else:
                        title_element = item.find('a')

                    if not title_element:
                        continue

                    title = title_element.get_text(strip=True)
                    link = title_element.get('href')

                    # 제목이 너무 짧거나 의미없는 경우 스킵
                    if not title or len(title) < 5:
                        continue

                    # URL 정리 - 스킴 문제 해결
                    if link:
                        if link.startswith('/'):
                            # 상대 경로인 경우
                            link = "https://finance.naver.com" + link
                        elif not link.startswith('http'):
                            # 프로토콜이 없는 경우
                            link = "https://finance.naver.com/" + link.lstrip('/')

                    # 상세 뉴스 내용 크롤링 (에러가 발생해도 계속 진행)
                    try:
                        news_detail = self._get_news_detail(link)
                    except Exception as detail_error:
                        logger.warning(f"뉴스 상세 크롤링 실패 ('{title}'): {detail_error}")
                        news_detail = {'content': '', 'publish_date': ''}

                    news_data = {
                        'title': title,
                        'link': link,
                        'content': news_detail.get('content', ''),
                        'publish_date': news_detail.get('publish_date', ''),
                        'category': 'main_news',
                        'crawled_at': datetime.now().isoformat()
                    }

                    news_list.append(news_data)
                    logger.info(f"뉴스 수집 ({len(news_list)}/{limit}): '{title[:50]}...'")

                    # 원하는 개수에 도달하면 중단
                    if len(news_list) >= limit:
                        break

                    # 서버 부하 방지를 위한 딜레이
                    time.sleep(0.5)  # 딜레이 단축

                except Exception as e:
                    logger.error(f"뉴스 항목 처리 중 오류: {e}")
                    continue

            logger.info(f"뉴스 크롤링 완료: 총 {len(news_list)}개 수집")

        except Exception as e:
            logger.error(f"메인 뉴스 크롤링 중 오류: {e}")

        return news_list

    def get_research_reports(self, limit: int = 10) -> List[Dict]:
        """
        네이버 증권 리서치 리포트 크롤링 (최신 리포트 수집)
        각 카테고리별 개별 페이지에서 가장 최신 리포트를 수집

        Args:
            limit: 각 카테고리별로 가져올 리포트 개수

        Returns:
            List[Dict]: 리포트 정보 리스트
        """
        all_reports = []

        # 각 카테고리별 개별 페이지 URL
        category_urls = {
            '종목분석': f"{self.base_url}/research/company_list.naver",
            '산업분석': f"{self.base_url}/research/industry_list.naver",
            '시황정보': f"{self.base_url}/research/market_info_list.naver",
            '투자정보': f"{self.base_url}/research/invest_list.naver"
        }

        logger.info(f"각 카테고리별 최신 리포트 {limit}개씩 수집")

        for category_name, category_url in category_urls.items():
            try:
                logger.info(f"{category_name} 최신 리포트 크롤링 시작... ({category_url})")

                response = self.session.get(category_url)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # 테이블 찾기 - 여러 선택자 시도
                table_selectors = [
                    'table.type_1',
                    'table.type_2',
                    '.board_list table',
                    '.research_list table',
                    'table'
                ]

                table = None
                for selector in table_selectors:
                    table = soup.select_one(selector)
                    if table:
                        logger.info(f"{category_name} 리포트 발견")
                        break

                if not table:
                    logger.warning(f"{category_name}: 테이블을 찾을 수 없습니다.")
                    continue

                # 테이블 행 추출
                rows = table.find_all('tr')
                if len(rows) <= 1:  # 헤더만 있는 경우
                    logger.warning(f"{category_name}: 데이터 행이 없습니다.")
                    continue

                # 헤더 제외하고 데이터 행 처리
                data_rows = rows[1:] if rows[0].find('th') else rows

                count = 0

                # 날짜 필터링 없이 최신 순으로 리포트 수집
                for row in data_rows:
                    if count >= limit:
                        break

                    cells = row.find_all('td')
                    if len(cells) < 3:  # 최소한의 셀 개수
                        continue

                    try:
                        # 제목과 링크 찾기
                        title_link = None
                        title = ""
                        link = ""

                        for cell in cells:
                            a_tag = cell.find('a')
                            if a_tag and a_tag.get('href'):
                                title_link = a_tag
                                title = a_tag.get_text(strip=True)
                                link = a_tag.get('href')

                                # URL 정리 - 올바�� 프로토콜 수정
                                if not link.startswith('http'):
                                    # 상대 경로인 경우 올바른 기본 경로 추가
                                    if link.startswith('/'):
                                        link = self.base_url + link
                                    else:
                                        # research 경로가 누락된 경우 추가
                                        link = f"{self.base_url}/research/{link}"
                                break

                        if not title_link or not title:
                            continue

                        # 발행일 추출 (마지막 셀 또는 날짜가 포함된 셀)
                        publish_date = ""
                        for cell in reversed(cells):  # 뒤에서부터 찾기
                            cell_text = cell.get_text(strip=True)
                            # 날짜 패턴이 있는지 확인
                            if any(char.isdigit() for char in cell_text) and any(sep in cell_text for sep in ['.', '-', '/']):
                                publish_date = cell_text
                                break

                        # 상세 페이지에서 요약 내용 가져오기
                        summary = self._get_research_detail_summary(link)

                        # 증권사/제공자 정보 찾기
                        provider = ""
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            if any(keyword in cell_text for keyword in ['증권', '투자', '자산', '캐피탈']):
                                provider = cell_text
                                break

                        # 회사명 추출 (종목분석의 경우)
                        company = ""
                        if category_name == '종목분석' and len(cells) > 0:
                            company = cells[0].get_text(strip=True)

                        report_data = {
                            'title': title,
                            'link': link,
                            'summary': summary,
                            'provider': provider,
                            'company': company,
                            'publish_date': publish_date if publish_date else 'unknown',
                            'category_name': category_name,
                            'category_key': category_name.lower(),
                            'crawled_at': datetime.now().isoformat()
                        }

                        all_reports.append(report_data)
                        count += 1

                        logger.info(f"{category_name}: '{title}' 리포트 수집 ({count}/{limit})")

                        # 서버 부하 방지
                        time.sleep(1)

                    except Exception as e:
                        logger.error(f"{category_name} 리포트 항목 처리 중 오류: {e}")
                        continue

                logger.info(f"{category_name}: {count}개 최신 리포트 수집 완료")

                # 카테고리 간 딜레이
                time.sleep(2)

            except Exception as e:
                logger.error(f"{category_name} 카테고리 크롤링 중 오류: {e}")
                continue

        return all_reports

    def _get_news_detail(self, link: str) -> Dict:
        """
        뉴스 상�� 내용 크롤링

        Args:
            link: 뉴스 링크

        Returns:
            Dict: 뉴스 내용, 발행일 등 정보
        """
        try:
            response = self.session.get(link)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 기사 본문 추출 (네이버 증권은 일반적으로 'div.article' 또는 'div#articleBody'에 본문이 있음)
            content_div = soup.find('div', {'class': 'article'})
            if not content_div:
                content_div = soup.find('div', {'id': 'articleBody'})

            content = content_div.get_text(strip=True) if content_div else ""

            # 발행일 추출 (메타 태그 또는 기사 본문 내에서 추출 시도)
            publish_date = ""
            date_meta = soup.find('meta', {'property': 'article:published_time'})
            if date_meta and date_meta.get('content'):
                publish_date = date_meta['content']
            else:
                # 본문 내에서 날짜 형식 추출 (예: 2023.03.15. 10:30)
                import re
                date_patterns = [r'(\d{4}[.\-]\d{1,2}[.\-]\d{1,2})', r'(\d{1,2}[.\-]\d{1,2}[.\-]\d{2,4})']
                for pattern in date_patterns:
                    match = re.search(pattern, content)
                    if match:
                        publish_date = match.group(0)
                        break

            return {
                'content': content,
                'publish_date': publish_date
            }

        except Exception as e:
            logger.error(f"뉴스 상세 크롤링 중 오류: {e}")
            return {}

    def _get_research_detail_summary(self, link: str) -> str:
        """
        리서치 리포트 상세 내용에서 요약 추출

        Args:
            link: 리포트 링크

        Returns:
            str: 리포트 요약 내용
        """
        try:
            response = self.session.get(link)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 요약 내용 추출 (일반적으로 'div.summary' 또는 'div#reportSummary'에 요약이 있음)
            summary_div = soup.find('div', {'class': 'summary'})
            if not summary_div:
                summary_div = soup.find('div', {'id': 'reportSummary'})

            summary = summary_div.get_text(strip=True) if summary_div else ""

            return summary

        except Exception as e:
            logger.error(f"리포트 요약 크롤링 중 오류: {e}")
            return ""

    def get_today_summary(self) -> Dict:
        """
        오늘의 주요 뉴스와 리포트 요약 크롤링

        Returns:
            Dict: 오늘의 뉴스와 리포트 데이터
        """
        logger.info("오늘의 주요 뉴스 및 리포트 크롤링 시작")

        # 메인 뉴스 크롤링 (20개로 증가)
        main_news = self.get_main_news(limit=20)
        logger.info(f"메인 뉴스 {len(main_news)}개 수집 완료")

        # 리서치 리포트 크롤링
        research_reports = self.get_research_reports(limit=5)
        logger.info(f"리서치 리포트 {len(research_reports)}개 수집 완료")

        return {
            'main_news': main_news,
            'research_reports': research_reports,
            'crawled_at': datetime.now().isoformat(),
            'total_count': len(main_news) + len(research_reports)
        }

if __name__ == "__main__":
    # 테스트 실행
    crawler = NaverStockNewsCrawler()
    data = crawler.get_today_summary()
    print(f"총 {data['total_count']}개 뉴스/리포트 수집 완료")
