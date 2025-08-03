"""
네이버 증권 뉴스 및 리서치 크롤링 모듈
"""

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from typing import List, Dict
import logging
import json
import re

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

                    # 상세 뉴스 내용 ���롤링 (에러가 발생해도 계속 진행)
                    try:
                        news_detail = self._get_news_detail(link)
                    except Exception as detail_error:
                        logger.warning(f"뉴스 상세 크롤링 실패 ('{title}'): {detail_error}")
                        news_detail = {'content': '', 'publish_date': ''}

                    news_data = {
                        'title': title,
                        'link': link,
                        'content': news_detail.get('content', ''),
                        'full_html': news_detail.get('full_html', ''),  # HTML 전체 내용 추가
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
        네이버 증권 리서치 리포트 크롤링 - 개선된 버전
        https://finance.naver.com/research/ 메인 페이지에서 각 카테고리별 최신 리포트 수집

        Args:
            limit: 각 카테고리별로 가져올 리�������������트 개수

        Returns:
            List[Dict]: 리포트 정보 리스트
        """
        all_reports = []

        # 네이버 금융 리서치 메인 페이지
        main_research_url = "https://finance.naver.com/research/"

        # 각 카테고리별 URL 패턴
        category_urls = {
            '종목분석': f"{main_research_url}company_list.naver",
            '산업분석': f"{main_research_url}industry_list.naver",
            '시황정보': f"{main_research_url}market_info_list.naver",
            '투자정보': f"{main_research_url}invest_list.naver"
        }

        logger.info(f"네이버 금융 리서치에서 각 카테고리별 최신 리포트 {limit}개씩 수집")

        for category_name, category_url in category_urls.items():
            try:
                logger.info(f"{category_name} 리포트 크롤링 시작... ({category_url})")

                response = self.session.get(category_url, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # 리포트 테이블 찾기 - 네이버 금융 리서치 구조에 맞는 선택자
                table_selectors = [
                    'table.type_1',  # 주로 사용되는 테이블 클래스
                    'table.type_2',
                    'table[summary*="리포트"]',
                    'div.box_type_m table',  # 사진에서 확인한 구조
                    'table'
                ]

                table = None
                for selector in table_selectors:
                    table = soup.select_one(selector)
                    if table and len(table.find_all('tr')) > 1:  # 헤더 외에 데이터가 있���지 확인
                        logger.info(f"{category_name} 리포트 테이블 발견 (선택자: {selector})")
                        break

                if not table:
                    logger.warning(f"{category_name}: 리포트 테이블을 찾을 수 없습니다.")
                    continue

                # 테이블의 모든 행 추출
                rows = table.find_all('tr')
                if len(rows) <= 1:
                    logger.warning(f"{category_name}: 데이터 행이 없습니다.")
                    continue

                # 헤더 행 제외
                data_rows = rows[1:] if rows[0].find('th') else rows

                count = 0

                for row in data_rows:
                    if count >= limit:
                        break

                    cells = row.find_all('td')
                    if len(cells) < 2:  # 최소 2개 셀 필요 (제목, 날짜 등)
                        continue

                    try:
                        # 제목과 링크 찾기 - 다양한 패턴 시도
                        title = ""
                        link = ""

                        # 첫 번째 또는 두 번째 셀에서 링크 찾기
                        for cell in cells[:3]:  # 처음 3개 셀에서 찾기
                            a_tag = cell.find('a')
                            if a_tag and a_tag.get('href'):
                                title = a_tag.get_text(strip=True)
                                link = a_tag.get('href')

                                # 제목이 의미있는지 확인
                                if len(title) > 5 and not title.isdigit():
                                    break

                        if not title or not link:
                            continue

                        # URL 정리
                        if link.startswith('/'):
                            link = "https://finance.naver.com" + link
                        elif not link.startswith('http'):
                            link = f"https://finance.naver.com/research/{link}"

                        # 발행일 추출 - 보통 마지막 셀들에서 찾을 수 있음
                        publish_date = ""
                        for cell in reversed(cells):
                            cell_text = cell.get_text(strip=True)
                            # 날짜 패턴 확인 (YY.MM.DD, YYYY.MM.DD 등)
                            if self._is_valid_date(cell_text):
                                publish_date = cell_text
                                break

                        # 증권사/제공자 정보 추출
                        provider = ""
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            if any(keyword in cell_text for keyword in ['증권', '투자', '자산', '캐피탈', 'Securities']):
                                provider = cell_text
                                break

                        # 리포트 상세 페이지에서 실제 본문 추출
                        content = self._get_research_report_content(link)

                        report_data = {
                            'title': title,
                            'link': link,
                            'summary': content,  # 실제 리포트 본문을 summary로 저장
                            'provider': provider,
                            'publish_date': publish_date if publish_date else 'unknown',
                            'category_name': category_name,
                            'category_key': category_name.lower(),
                            'crawled_at': datetime.now().isoformat()
                        }

                        all_reports.append(report_data)
                        count += 1

                        logger.info(f"{category_name}: '{title}' 리포트 수집 완료 ({count}/{limit})")

                        # 서버 부하 방지
                        time.sleep(1)

                    except Exception as e:
                        logger.error(f"{category_name} 리포트 처리 중 오류: {e}")
                        continue

                logger.info(f"{category_name}: {count}개 리포트 수집 완료")

                # 카테고리 간 딜레이
                time.sleep(2)

            except Exception as e:
                logger.error(f"{category_name} 카테고리 크롤링 중 ���류: {e}")
                continue

        return all_reports

    def _get_research_report_content(self, link: str) -> str:
        """
        리서치 리포트 상세 페이지에서 실제 본문 내용 추출

        Args:
            link: 리포트 상세 페이지 링크

        Returns:
            str: 리포트 본문 내용
        """
        try:
            response = self.session.get(link, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 리포트 본문을 위한 다양한 선택자 시도
            content_selectors = [
                # 네이버 금융 리서치 리포트 구조
                'div.view_cnt',  # 사진에서 확인한 구조
                'td.view_cnt',
                'div.report_content',
                'div.research_content',
                'div.content',
                'div.article_content',
                'div.view_content',
                'div#content',
                'div.summary',
                'div.report_summary',

                # 일반적인 본문 선택자
                'div[class*="content"]',
                'div[class*="view"]',
                'td[class*="content"]',
                'td[class*="view"]'
            ]

            content = ""

            for selector in content_selectors:
                try:
                    content_div = soup.select_one(selector)
                    if content_div:
                        # 불필요한 요소 제거
                        unwanted_selectors = [
                            'script', 'style', 'iframe', 'noscript',
                            '.ad', '.advertise', '.advertisement',
                            '.related', '.comment', '.social',
                            'nav', 'header', 'footer',
                            '.link', '.btn', 'button',
                            '.print', '.share'
                        ]

                        for unwanted_selector in unwanted_selectors:
                            for unwanted in content_div.select(unwanted_selector):
                                unwanted.decompose()

                        # 텍스트 추출
                        text = content_div.get_text(separator=' ', strip=True)

                        # 연속된 공백 정리
                        import re
                        text = re.sub(r'\s+', ' ', text).strip()

                        # 네이버 거래연결 관련 불��요한 텍스트 제거
                        unwanted_phrases = [
                            "네이버 주식거래연결",
                            "빠른 주문을 도와드립니다",
                            "증권사의 로그인을 연결",
                            "네이버는 증권사 서비스의 시스템 장���에 따른 법적 책임을 지지 않습니다"
                        ]

                        for phrase in unwanted_phrases:
                            if phrase in text:
                                # 이런 문구가 포함된 경우 다른 선택자 시도
                                text = ""
                                break

                        # 의미있는 길이의 본문인지 확인
                        if len(text) > 100:
                            logger.info(f"리포트 본문 추출 성공 (선택자: {selector}, 길이: {len(text)}자)")
                            logger.info(f"본문 미리보기: {text[:200]}...")
                            content = text
                            break

                except Exception as e:
                    logger.warning(f"선택자 '{selector}' 처리 중 오류: {e}")
                    continue

            # 선택자로 찾지 못한 경우 p 태그들 결합
            if not content or len(content) < 100:
                try:
                    paragraphs = soup.find_all('p')
                    if paragraphs:
                        paragraph_texts = []
                        for p in paragraphs:
                            p_text = p.get_text(strip=True)
                            # 불필요한 내용 필터링
                            if (len(p_text) > 20 and
                                not any(unwanted in p_text for unwanted in
                                       ['주식거래연결', '로그인을 연결', '법적 책임', '시스템 장애'])):
                                paragraph_texts.append(p_text)

                        if paragraph_texts:
                            content = ' '.join(paragraph_texts)
                            content = re.sub(r'\s+', ' ', content).strip()
                            logger.info(f"p태그 결합으로 리포트 ��문 추출 (길이: {len(content)}자)")

                except Exception as e:
                    logger.warning(f"p 태그 추출 중 오류: {e}")

            return content

        except Exception as e:
            logger.warning(f"리포트 본문 크롤링 중 오류 ({link}): {e}")
            return ""

    def _get_news_detail(self, link: str) -> Dict:
        """
        뉴스 상세 내용 크롤링 - 네이버 뉴스의 JavaScript 동적 로딩 문제 해결

        Args:
            link: 뉴스 링크

        Returns:
            Dict: 뉴스 내용(전체 본문), HTML 컨텐츠, 발행일 등 정보
        """
        try:
            logger.info(f"뉴스 상세 크롤링 시작: {link}")

            # 네이버 뉴스 페이지 접근
            response = self.session.get(link, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # 먼저 네이버 뉴스인지 확인
            is_naver_news = 'news.naver.com' in link or 'finance.naver.com' in link

            if is_naver_news:
                logger.info("네이버 뉴스 페이지로 확인됨")

                # 원본 기사 링크 찾기 시도
                original_link_selectors = [
                    'a.media_end_head_origin_link',
                    'a[href*="originallink"]',
                    'a.link_news_origin',
                    '.press_logo a',
                    'a[title*="원문보기"]',
                    'a.media_end_head_origin'
                ]

                original_url = ""
                for selector in original_link_selectors:
                    original_link_elem = soup.select_one(selector)
                    if original_link_elem and original_link_elem.get('href'):
                        original_url = original_link_elem['href']
                        logger.info(f"원본 기사 링크 발견: {original_url}")
                        break

                # 원본 기사가 있고 외부 사이트인 경우 원본에서 추출
                if original_url and original_url.startswith('http') and 'naver.com' not in original_url:
                    try:
                        logger.info("원본 기사에서 본문 추출 시도")
                        original_response = self.session.get(original_url, timeout=15)
                        original_response.raise_for_status()
                        original_soup = BeautifulSoup(original_response.content, 'html.parser')

                        content = self._extract_content_from_soup(original_soup, "원본 기사")
                        if content and len(content) > 100:
                            publish_date = self._extract_publish_date_from_soup(original_soup, original_url)
                            return {
                                'content': content,
                                'full_html': '',
                                'publish_date': publish_date
                            }
                    except Exception as e:
                        logger.warning(f"원본 기사 처리 실패: {e}")

            # 네이버 뉴스 페이지에서 직접 추출
            logger.info("네이버 뉴스 페이지에서 직접 본문 추출 시도")
            content = self._extract_content_from_soup(soup, "네이버 뉴스")

            # 발행일 추출
            publish_date = self._extract_publish_date_from_soup(soup, link)

            # 본문이 너무 짧으면 대안 방법 시도
            if not content or len(content) < 30:
                logger.info("대안적 방법으로 본문 추출 시도")
                content = self._extract_content_alternative(soup, link)

            logger.info(f"본문 추출 완료 - 길이: {len(content)}자")

            return {
                'content': content,
                'full_html': '',
                'publish_date': publish_date
            }

        except Exception as e:
            logger.warning(f"뉴스 상세 크롤링 중 오류 ({link}): {e}")
            return {
                'content': '',
                'full_html': '',
                'publish_date': ''
            }

    def _extract_content_from_soup(self, soup: BeautifulSoup, source_type: str) -> str:
        """
        BeautifulSoup 객체에서 본문 내용 추출 - 네이버 뉴스 HTML 구조 기반

        Args:
            soup: BeautifulSoup 객체
            source_type: 소스 타입 (로깅용)

        Returns:
            str: 추출된 본문 내용
        """
        content = ""

        # 디버깅을 위한 HTML 구조 확인
        logger.info(f"{source_type} HTML 구조 분석 시작")

        # 페이지에 있는 모든 article 태그 찾기
        articles = soup.find_all('article')
        logger.info(f"발견된 article 태그 수: {len(articles)}")

        for i, article in enumerate(articles):
            article_id = article.get('id', 'no-id')
            article_class = article.get('class', [])
            logger.info(f"Article {i+1}: id='{article_id}', class='{article_class}'")

            # dic_area를 찾았다면 내부 구조 확인
            if 'dic_area' in article_id:
                logger.info(f"dic_area 발견! 내부 요소 확인")
                # 모든 하위 요소들 확인
                children = article.find_all(['p', 'div', 'span', 'strong'])
                logger.info(f"dic_area 내부 요소 수: {len(children)}")

                for j, child in enumerate(children[:10]):  # 처음 10개만 확인
                    child_tag = child.name
                    child_class = child.get('class', [])
                    child_text = child.get_text(strip=True)[:50]  # 처음 50자���
                    logger.info(f"  Child {j+1}: <{child_tag}> class='{child_class}' text='{child_text}...'")

        # 사진에서 확인한 정확한 네이버 뉴스 구조를 우선으로 시도
        content_selectors = [
            # 사진에서 확인한 정확한 네이버 뉴스 구조
            'article#dic_area.go_trans._article_content',
            'article#dic_area',
            'div#dic_area',

            # 네이버 뉴스 본문 컨테이너의 다양한 패턴
            'div#newsct_article',
            'div.newsct_article',
            'div#contents div#newsct_article',
            'div.newsct_body',
            'div#contents.newsct_body div#newsct_article',

            # 일반적인 뉴스 사이트 패턴
            'div#articleBodyContents',
            'article.article-body',
            'div.article-body',
            'div.news-content',
            'div.article-content',
            'div.content-body',
            'div.post-content',
            'div.entry-content',

            # 더 일반적인 패턴
            'div[class*="content"]',
            'div[class*="article"]',
            'div[id*="content"]',
            'div[id*="article"]',
            'main',
            'section[class*="content"]'
        ]

        for selector in content_selectors:
            try:
                content_div = soup.select_one(selector)
                if content_div:
                    logger.info(f"{source_type}에서 선택자 '{selector}' 발견")

                    # 내부 요소들 확인
                    all_elements = content_div.find_all()
                    logger.info(f"선택된 요소 내부에 {len(all_elements)}개 하위 요소 발견")

                    # 네이버 뉴스 특화 불필요 요소 제거
                    unwanted_selectors = [
                        'script', 'style', 'iframe', 'noscript',
                        '.ad', '.advertise', '.advertisement',
                        '.related', '.comment', '.social',
                        'nav', 'header', 'footer', '.sidebar',
                        '.media_end_head', '.byline', '.copyright',
                        '.journalist', '.reporter_info',
                        '.end_photo_org',  # 사진 설명 제거
                        '.media_end_head_info',  # 헤더 정보 제거
                        '.media_end_head_journalist',  # 기자 정보 제거
                        'span.end_photo_org',  # 사진 관련 span 제거
                        '.media_end_summary',  # 요약 제거
                        'strong.media_end_summary'  # 요약 제거
                    ]

                    removed_count = 0
                    for unwanted_selector in unwanted_selectors:
                        unwanted_elements = content_div.select(unwanted_selector)
                        for unwanted in unwanted_elements:
                            unwanted.decompose()
                            removed_count += 1

                    logger.info(f"불필요한 요소 {removed_count}개 제거")

                    # 텍스트 추출 전에 남은 요소들 확인
                    remaining_elements = content_div.find_all()
                    logger.info(f"정리 후 남은 요소 수: {len(remaining_elements)}")

                    # 남은 요소들의 텍스트 길이 확인
                    total_text = content_div.get_text(strip=True)
                    logger.info(f"전체 텍스트 길이: {len(total_text)}자")

                    if len(total_text) > 20:
                        # 텍스트 추출 - 줄바꿈을 유지하면서 추출
                        text = content_div.get_text(separator='\n', strip=True)

                        # 빈 줄 제거하고 한 줄로 정리
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        text = ' '.join(lines)

                        # 연속된 공백 정리
                        import re
                        text = re.sub(r'\s+', ' ', text).strip()

                        # 네이버 특화 불필요 문구 제거
                        unwanted_phrases = [
                            "무단전재 및 재배포 금지",
                            "저작권자",
                            "ⓒ",
                            "Copyright",
                            "All rights reserved",
                            "본 기사는",
                            "기자 "
                        ]

                        for phrase in unwanted_phrases:
                            if phrase in text:
                                # 해당 문구 이후 부분 제거
                                text = text.split(phrase)[0].strip()

                        # 최소 길이 체크 (의미있는 뉴스 본문이어야 함)
                        if len(text) > 30:  # 최소 30자 이상으로 낮춤
                            logger.info(f"{source_type}에서 본문 추출 성공 (선택자: {selector}, 길이: {len(text)}자)")
                            logger.info(f"본문 미리보기: {text[:200]}...")
                            content = text
                            break
                        else:
                            logger.info(f"추출된 텍스트가 너무 짧음: {len(text)}자")
                    else:
                        logger.info(f"선택된 요소에 텍스트가 거의 없음: {len(total_text)}자")

            except Exception as e:
                logger.warning(f"선택자 '{selector}' 처리 중 오류: {e}")
                continue

        # 선택자로 찾지 못한 경우 더 적극적인 방법 시도
        if not content or len(content) < 30:
            try:
                logger.info(f"{source_type}에서 모든 텍스트 요소 직접 탐색")

                # 모든 p, div, span 태그에서 텍스트 수집
                all_text_elements = soup.find_all(['p', 'div', 'span'])
                logger.info(f"전체 텍스트 요소 수: {len(all_text_elements)}")

                meaningful_texts = []
                for element in all_text_elements:
                    element_text = element.get_text(strip=True)
                    # 길이가 20자 이상이고 의미있는 텍스트인지 확인
                    if (len(element_text) > 20 and
                        not any(skip_word in element_text for skip_word in [
                            '광고', '제공:', '저작권', '무단전재', '재배포금지',
                            'Copyright', 'ⓒ', '기자', '데스크', 'javascript',
                            'function', 'var ', 'document', 'window'
                        ])):
                        meaningful_texts.append(element_text)

                logger.info(f"의미���는 텍스트 요소 수: {len(meaningful_texts)}")

                if meaningful_texts:
                    # 가장 긴 텍스트들을 조합 (최대 5개)
                    sorted_texts = sorted(meaningful_texts, key=len, reverse=True)
                    content = ' '.join(sorted_texts[:5])

                    # 연속된 공백 정리
                    import re
                    content = re.sub(r'\s+', ' ', content).strip()

                    if len(content) > 100:
                        logger.info(f"{source_type}에서 직접 탐색으로 본문 추출 (길이: {len(content)}자)")
                        logger.info(f"본문 미리보기: {content[:200]}...")

            except Exception as e:
                logger.warning(f"직접 탐색 중 오류: {e}")

        return content

    def _extract_content_alternative(self, soup: BeautifulSoup, link: str) -> str:
        """
        대안적인 방법으로 본문 추출

        Args:
            soup: BeautifulSoup 객체
            link: 원본 링크

        Returns:
            str: 추출된 본문 내용
        """
        content = ""

        try:
            # 1. JSON-LD 구조화 ���이터에서 추출
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        # articleBody 또는 text 필드 찾기
                        if 'articleBody' in data:
                            content = data['articleBody']
                            logger.info(f"JSON-LD에서 본문 추출 성공 (길이: {len(content)}자)")
                            break
                        elif 'text' in data:
                            content = data['text']
                            logger.info(f"JSON-LD에서 텍스트 추출 성공 (길이: {len(content)}자)")
                            break
                except:
                    continue

            # 2. 메타 태그에서 description 추출
            if not content or len(content) < 50:
                meta_desc = soup.find('meta', {'name': 'description'})
                if not meta_desc:
                    meta_desc = soup.find('meta', {'property': 'og:description'})

                if meta_desc and meta_desc.get('content'):
                    content = meta_desc['content']
                    logger.info(f"메타 description에서 내용 추출 (길이: {len(content)}자)")

            # 3. 모든 텍스트에서 가장 긴 연속 문단 찾기
            if not content or len(content) < 50:
                all_text = soup.get_text()
                # 줄바꿈으로 분할하여 가장 긴 문단 찾기
                lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                longest_content = max(lines, key=len, default="")

                if len(longest_content) > 100:
                    content = longest_content
                    logger.info(f"가장 긴 문단에서 내용 추출 (길이: {len(content)}자)")

        except Exception as e:
            logger.warning(f"대안적 본문 추출 중 오류: {e}")

        return content

    def _extract_publish_date_from_soup(self, soup: BeautifulSoup, url: str) -> str:
        """
        BeautifulSoup 객체에��� 발행일 추출

        Args:
            soup: BeautifulSoup 객체
            url: 원본 URL

        Returns:
            str: 추출된 발행일
        """
        publish_date = ""

        # 1. 네이버 뉴스 특화 선택자
        date_selectors = [
            'span[data-date-time]',
            'span.media_end_head_info_datestamp_time',
            'span._ARTICLE_DATE_TIME',
            '.media_end_head_info_datestamp_time',
            'time[datetime]',
            '.article_info .date',
            '.byline .date',
            '.news_end .date'
        ]

        for selector in date_selectors:
            try:
                date_elements = soup.select(selector)
                for date_element in date_elements:
                    # data-date-time 속성 확인
                    date_attr = date_element.get('data-date-time')
                    if date_attr:
                        publish_date = date_attr
                        logger.info(f"발행일 발견 (data-date-time): {publish_date}")
                        break

                    # datetime 속��� 확인
                    datetime_attr = date_element.get('datetime')
                    if datetime_attr:
                        publish_date = datetime_attr
                        logger.info(f"발행일 발견 (datetime): {publish_date}")
                        break

                    # 텍스트에서 날짜 패턴 확인
                    date_text = date_element.get_text(strip=True)
                    if self._is_valid_date(date_text):
                        publish_date = date_text
                        logger.info(f"발행일 발견 (텍스트): {publish_date}")
                        break

                if publish_date:
                    break
            except:
                continue

        # 2. 메타 태그에서 발행일 추출
        if not publish_date:
            meta_selectors = [
                'meta[property="article:published_time"]',
                'meta[name="pubdate"]',
                'meta[property="og:article:published_time"]',
                'meta[name="date"]'
            ]

            for selector in meta_selectors:
                try:
                    meta_tag = soup.select_one(selector)
                    if meta_tag and meta_tag.get('content'):
                        publish_date = meta_tag['content']
                        logger.info(f"발행일 발견 (메타태그): {publish_date}")
                        break
                except:
                    continue

        # 3. URL에서 날짜 추출
        if not publish_date:
            import re
            url_date_match = re.search(r'date=(\d{4}-?\d{2}-?\d{2})', url)
            if url_date_match:
                publish_date = url_date_match.group(1)
                logger.info(f"발행일 발견 (URL): {publish_date}")

        return publish_date

    def _is_valid_date(self, text: str) -> bool:
        """
        텍스트가 유효한 날짜 형식인지 확인

        Args:
            text: 확인할 텍스트

        Returns:
            bool: 유효한 날짜 형식인지 여부
        """
        import re

        date_patterns = [
            r'\d{4}[-./]\d{1,2}[-./]\d{1,2}',  # 2025-08-03
            r'\d{1,2}[-./]\d{1,2}[-./]\d{2,4}',  # 08-03-2025
            r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일',  # 2025년 8월 3일
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO 형식
            r'\d{2}\.\d{2}\.\d{2}',  # 25.08.03
            r'\d{4}\.\d{2}\.\d{2}',  # 2025.08.03
        ]

        for pattern in date_patterns:
            if re.search(pattern, text):
                return True

        return False

    def get_today_summary(self) -> Dict:
        """
        오늘의 주요 뉴스와 리포트 요약 크롤링

        Returns:
            Dict: 오늘의 뉴스와 리포트 데이터
        """
        logger.info("오늘의 주요 뉴스 크롤링 시작")

        # 메인 뉴스 크롤링 (20개로 증가)
        main_news = self.get_main_news(limit=20)
        logger.info(f"메인 뉴스 {len(main_news)}개 수집 완료")

        # 리서치 리포트 크롤링 (복구)
        research_reports = self.get_research_reports(limit=5)
        logger.info(f"리서치 리포��� {len(research_reports)}개 수집 완료")

        return {
            'main_news': main_news,
            'research_reports': research_reports,
            'crawled_at': datetime.now().isoformat(),
            'total_count': len(main_news) + len(research_reports)
        }

class NaverNewsHeadlineCrawler:
    """네이버 뉴스 헤드라인 크롤러"""

    def __init__(self):
        self.base_url = "https://news.naver.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_headline_news(self, section_id: str = "101", limit: int = 20) -> List[Dict]:
        """
        네이버 뉴스 헤드라인 크롤링

        Args:
            section_id: 뉴스 섹션 ID (101: 정치, 102: 경제, 103: 사회 등)
            limit: 가져올 뉴스 개수

        Returns:
            List[Dict]: 뉴스 정보 리스트
        """
        news_list = []

        try:
            # 네이버 뉴스 섹션 페이지 URL
            url = f"https://news.naver.com/section/{section_id}"
            logger.info(f"네이버 뉴스 섹션 크롤링 시작: {url}")

            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 헤드라인 뉴스 선택자들
            headline_selectors = [
                '.section_headline .sa_text_title',  # 헤드라인 제목
                '.section_latest .sa_text_title',    # 최신 뉴스 제목
                '.sa_text_title',                     # 일반 뉴스 제목
                'a[href*="/article/"]',              # 기사 링크
            ]

            news_links = []

            # 헤드라인 뉴스 링크 수집
            for selector in headline_selectors:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        if element.name == 'a':
                            link = element
                        else:
                            link = element.find_parent('a') or element.find('a')

                        if link and link.get('href'):
                            href = link.get('href')
                            title = link.get_text(strip=True)

                            # 뉴스 기사 링크인지 확인
                            if '/article/' in href and title and len(title) > 5:
                                full_url = href if href.startswith('http') else f"https://news.naver.com{href}"
                                news_links.append({
                                    'title': title,
                                    'url': full_url
                                })

                        if len(news_links) >= limit:
                            break

                    if len(news_links) >= limit:
                        break

                except Exception as e:
                    logger.warning(f"선택자 '{selector}' 처리 중 오류: {e}")
                    continue

            # 중복 제거 (URL 기준)
            seen_urls = set()
            unique_news = []
            for news in news_links:
                if news['url'] not in seen_urls:
                    seen_urls.add(news['url'])
                    unique_news.append(news)
                    if len(unique_news) >= limit:
                        break

            logger.info(f"헤드라인 뉴스 {len(unique_news)}개 발견")

            # 각 뉴스의 본문 내용 크롤링
            for idx, news_item in enumerate(unique_news):
                try:
                    logger.info(f"뉴스 본문 크롤링 중... ({idx + 1}/{len(unique_news)})")

                    # 뉴스 본문 크롤링
                    content_data = self._get_news_content(news_item['url'])

                    news_data = {
                        'id': idx + 1,
                        'title': news_item['title'],
                        'url': news_item['url'],
                        'content': content_data.get('content', ''),
                        'summary': content_data.get('summary', ''),
                        'publish_date': content_data.get('publish_date', ''),
                        'media': content_data.get('media', ''),
                        'category': f'section_{section_id}',
                        'crawled_at': datetime.now().isoformat()
                    }

                    news_list.append(news_data)
                    logger.info(f"뉴스 수집 완료 ({len(news_list)}/{limit}): '{news_item['title'][:50]}...'")

                    # 서버 부하 방지
                    time.sleep(1)

                except Exception as e:
                    logger.error(f"뉴스 본문 크롤링 실패: {e}")
                    # 본문을 가져오지 못해도 기본 정보는 저장
                    news_data = {
                        'id': idx + 1,
                        'title': news_item['title'],
                        'url': news_item['url'],
                        'content': '',
                        'summary': '',
                        'publish_date': '',
                        'media': '',
                        'category': f'section_{section_id}',
                        'crawled_at': datetime.now().isoformat()
                    }
                    news_list.append(news_data)
                    continue

            logger.info(f"헤드라인 뉴스 크롤링 완료: 총 {len(news_list)}개 수집")

        except Exception as e:
            logger.error(f"헤드라인 뉴스 크롤링 중 오류: {e}")

        return news_list

    def _get_news_content(self, url: str) -> Dict:
        """
        개별 뉴스 기사의 본문 내용 크롤링 - 개선된 버전

        Args:
            url: 뉴스 기사 URL

        Returns:
            Dict: 뉴스 본문 정보
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 정확한 네이버 뉴스 선택자 사용 (제공해주신 함수 참고)
            # 1. 제목 추출
            title = ''
            title_selector = "#title_area > span"
            try:
                title_elements = soup.select(title_selector)
                title_lst = [t.get_text(strip=True) for t in title_elements]
                title = "".join(title_lst)
            except:
                pass

            # 2. 발행일 추출
            publish_date = ''
            date_selector = "#ct > div.media_end_head.go_trans > div.media_end_head_info.nv_notrans > div.media_end_head_info_datestamp > div:nth-child(1) > span"
            try:
                date_elements = soup.select(date_selector)
                date_lst = [d.get_text(strip=True) for d in date_elements]
                publish_date = "".join(date_lst)
            except:
                # 대체 선택자들
                fallback_selectors = [
                    '.media_end_head_info_datestamp_time',
                    'span[data-date-time]',
                    '.author em'
                ]
                for selector in fallback_selectors:
                    try:
                        date_element = soup.select_one(selector)
                        if date_element:
                            publish_date = date_element.get_text(strip=True)
                            break
                    except:
                        continue

            # 3. 본문 내용 추출
            content = ''
            main_selector = "#dic_area"
            try:
                main_elements = soup.select(main_selector)
                main_lst = []
                for m in main_elements:
                    # 불필요한 요소 제거
                    for script in m(["script", "style", "iframe"]):
                        script.decompose()

                    # 네이버 뉴스 특화 불필요 요소 제거
                    unwanted_selectors = [
                        '.end_photo_org',
                        '.media_end_head_journalist',
                        '.media_end_summary',
                        'strong.media_end_summary'
                    ]
                    for unwanted_selector in unwanted_selectors:
                        for unwanted in m.select(unwanted_selector):
                            unwanted.decompose()

                    m_text = m.get_text(strip=True)
                    if m_text:
                        main_lst.append(m_text)

                content = " ".join(main_lst)

                # 텍스트 정리
                import re
                content = re.sub(r'\s+', ' ', content).strip()

                # 불필요한 문구 제거
                unwanted_phrases = [
                    "무단전재 및 재배포 금지",
                    "저작권자",
                    "ⓒ",
                    "Copyright"
                ]
                for phrase in unwanted_phrases:
                    if phrase in content:
                        content = content.split(phrase)[0].strip()

            except:
                # 대체 선택자들
                fallback_selectors = [
                    '#articleBodyContents',
                    '.go_trans._article_content',
                    '._article_body_contents'
                ]
                for selector in fallback_selectors:
                    try:
                        content_element = soup.select_one(selector)
                        if content_element:
                            for script in content_element(["script", "style"]):
                                script.decompose()
                            content = content_element.get_text(strip=True)
                            if len(content) > 50:
                                break
                    except:
                        continue

            # 4. 요약 생성
            summary = ''
            if content:
                sentences = content.split('.')
                if sentences:
                    summary = sentences[0][:200] + ('...' if len(sentences[0]) > 200 else '')

            # 5. 언론사 추출
            media = ''
            media_selectors = [
                '.media_end_head_top_logo img',
                '.press_logo img',
                '.media_end_head_top_logo_text'
            ]
            for selector in media_selectors:
                try:
                    media_element = soup.select_one(selector)
                    if media_element:
                        if media_element.name == 'img':
                            media = media_element.get('alt', '')
                        else:
                            media = media_element.get_text(strip=True)
                        if media:
                            break
                except:
                    continue

            return {
                'content': content,
                'summary': summary,
                'publish_date': publish_date,
                'media': media,
                'title': title
            }

        except Exception as e:
            logger.error(f"뉴스 본문 크롤링 실패 ({url}): {e}")
            return {
                'content': '',
                'summary': '',
                'publish_date': '',
                'media': '',
                'title': ''
            }

    def art_crawl(self, url: str) -> Dict:
        """
        제공해주신 art_crawl 함수 스타일로 구현한 기사 크롤링 함수

        Args:
            url: 뉴스 기사 URL

        Returns:
            dict: 기사제목, 날짜, 본문이 크롤링된 딕셔너리
        """
        art_dic = {}

        try:
            # 1. CSS 선택자 정의 (제공해주신 정확한 선택자 사용)
            title_selector = "#title_area > span"
            date_selector = "#ct > div.media_end_head.go_trans > div.media_end_head_info.nv_notrans > div.media_end_head_info_datestamp > div:nth-child(1) > span"
            main_selector = "#dic_area"

            # HTTP 요청
            html = self.session.get(url, timeout=15)
            html.raise_for_status()
            soup = BeautifulSoup(html.text, "lxml")

            # 2. 데이터 추출
            # 제목 수집
            title = soup.select(title_selector)
            title_lst = [t.text for t in title]
            title_str = "".join(title_lst)

            # 날짜 수집
            date = soup.select(date_selector)
            date_lst = [d.text for d in date]
            date_str = "".join(date_lst)

            # 본문 수집
            main = soup.select(main_selector)
            main_lst = []
            for m in main:
                # 불필요한 요소 제거
                for script in m(["script", "style", "iframe"]):
                    script.decompose()

                m_text = m.text
                m_text = m_text.strip()
                if m_text:
                    main_lst.append(m_text)
            main_str = "".join(main_lst)

            # 텍스트 정리
            import re
            main_str = re.sub(r'\s+', ' ', main_str).strip()

            # 3. 결과 딕셔너리 구성
            art_dic["title"] = title_str
            art_dic["date"] = date_str
            art_dic["main"] = main_str
            art_dic["url"] = url
            art_dic["crawled_at"] = datetime.now().isoformat()

            logger.info(f"art_crawl 완료 - 제목: '{title_str[:50]}...', 본문: {len(main_str)}자")

        except Exception as e:
            logger.error(f"art_crawl 실패 ({url}): {e}")
            art_dic = {
                "title": "",
                "date": "",
                "main": "",
                "url": url,
                "crawled_at": datetime.now().isoformat()
            }

        return art_dic

    def save_to_json(self, news_list: List[Dict], filename: str = None) -> str:
        """
        뉴스 데이터를 JSON 파일로 저장

        Args:
            news_list: 뉴스 데이터 리스트
            filename: 저장할 파일명 (None이면 ���동 생성)

        Returns:
            str: 저장된 파일 경로
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"naver_news_headlines_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'metadata': {
                        'total_count': len(news_list),
                        'crawled_at': datetime.now().isoformat(),
                        'source': 'naver_news_headlines'
                    },
                    'news': news_list
                }, f, ensure_ascii=False, indent=2)

            logger.info(f"뉴스 데이터 JSON 파일 저장 완료: {filename}")
            return filename

        except Exception as e:
            logger.error(f"JSON 파일 저장 실패: {e}")
            return None

