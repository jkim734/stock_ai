"""
뉴스 및 리서치 분석 모듈 - Gemini API 활용 (통합 크롤링 기능 포함)
"""

from typing import List, Dict
import json
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import re
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

from google import genai
from google.genai import types

# 로��� 설정
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class IntegratedNewsAnalyzer:
    """통합 뉴스 및 리서치 크롤링 & 분석기"""

    def __init__(self):
        self.model_name = "gemini-2.0-flash-001"
        self.client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def ask_question_to_gemini_cache(self, prompt, max_retries=5, retry_delay=5):
        """
        Gemini API를 사용하여 질문에 대한 답변을 얻습니다.
        뉴스 분석에 최적화된 버전입니다.
        """
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                # API 키 확인
                api_key = os.getenv("GOOGLE_AI_API_KEY")
                if not api_key:
                    raise Exception("GOOGLE_AI_API_KEY 환경 변수가 설정되지 않았습니다.")

                # Gemini API 호출
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=2048
                    )
                )

                return response.text

            except Exception as e:
                error_msg = str(e).lower()
                print(f"API 오류 (시도 {attempt + 1}/{max_retries}): {e}")

                if hasattr(e, 'code') and e.code == 503:
                    print(f"⏳ API 사용량 한도 초과 (시도 {attempt + 1}/{max_retries}). {retry_delay}초 후 재시도...")
                    time.sleep(retry_delay)
                    continue

                if attempt == max_retries - 1:
                    return f"API 호출 실패: {e}"

                time.sleep(retry_delay)

        return "모든 재시도 실패"

    def json_match(self, text):
        """
        텍스트에서 JSON 객체를 추출하는 함수
        """
        try:
            # 중괄호 패턴 매칭
            pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(pattern, text, re.DOTALL)

            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

            # 백틱으로 감싸진 JSON 찾기
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            matches = re.findall(json_pattern, text, re.DOTALL)

            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

            return None
        except Exception as e:
            print(f"JSON 파싱 오류: {e}")
            return None

    def create_news_analysis_prompt(self, news_text):
        """뉴스 분석용 프롬프트 생성"""
        return f"""
다음 뉴스들을 분석하여 JSON 형태로 결과를 제공해주세요:

{news_text}

분석 결과를 다음 JSON 형식으로 정확히 제공해주세요:

{{
  "overall_sentiment": "positive/negative/neutral",
  "sentiment_score": 0-100,
  "key_themes": ["주요 테마1", "주요 테마2"],
  "market_impact": "시장에 미치는 영향 분석",
  "summary": "전체 뉴스 요약",
  "investment_signals": "buy/sell/hold"
}}
"""

    def create_research_reports_analysis_prompt(self, reports_text):
        """리서치 리포트 분석용 프롬프트 생성"""
        return f"""
다음 리서치 리포트들을 분석하여 JSON 형태로 결과를 제공해주세요:

{reports_text}

분석 ���과를 다음 JSON 형식으로 정확히 제공해주세요:

{{
  "category_summary": {{
    "종목분석": "종목분석 요약",
    "산업분석": "산업분석 요약", 
    "시황정보": "시황정보 요약",
    "투자정보": "투자정보 요약"
  }},
  "top_mentioned_stocks": ["종목1", "종목2", "종목3"],
  "key_industries": ["업종1", "업종2", "업종3"],
  "investment_themes": ["투자테마1", "투자테마2"],
  "market_outlook": "positive/negative/neutral",
  "risk_factors": ["리스크1", "리스크2"],
  "opportunities": ["기회1", "기회2"],
  "analyst_consensus": "애널리스트 consensus",
  "summary": "전체 리포트 종합 ���약"
}}
"""

    def crawl_and_analyze_all(self, news_section_id: str = "101", news_limit: int = 20, reports_limit: int = 10) -> Dict:
        """
        뉴스와 리포트를 크롤링하고 분석하여 통합된 결과 반환

        Args:
            news_section_id: 네이버 뉴스 섹션 ID (101: 정치, 102: 경제, 103: 사회 등)
            news_limit: 크롤링할 뉴스 개수
            reports_limit: 크롤링할 리포트 개수 (카테고리별)

        Returns:
            Dict: 통합�� 크롤링 및 분석 결과
        """
        logger.info("=" * 60)
        logger.info("통합 뉴스 & 리서치 크롤��� 및 분석 시작")
        logger.info("=" * 60)

        # 1. 뉴스 크롤링
        logger.info("🔍 네이버 뉴스 헤드라인 크롤링 시작...")
        news_data = self._crawl_naver_news(news_section_id, news_limit)

        # 2. 리서치 리포트 크롤링
        logger.info("📊 네이버 증권 리서치 리포트 크롤링 시작...")
        reports_data = self._crawl_research_reports(reports_limit)

        # 3. 데이터 분석
        logger.info("🤖 AI 기반 데이터 분석 시작...")

        # 뉴스 분석
        news_analysis = {}
        if news_data:
            news_analysis = self.analyze_news_sentiment(news_data)

        # 리포트 분석
        reports_analysis = {}
        if reports_data:
            reports_analysis = self.analyze_research_reports(reports_data)

        # 4. 통합 결과 생성
        integrated_result = {
            'metadata': {
                'crawled_at': datetime.now().isoformat(),
                'news_section_id': news_section_id,
                'news_count': len(news_data),
                'reports_count': len(reports_data),
                'source': 'integrated_news_research_crawler'
            },
            'news': {
                'data': news_data,
                'analysis': news_analysis
            },
            'research_reports': {
                'data': reports_data,
                'analysis': reports_analysis
            },
            'summary': {
                'total_items': len(news_data) + len(reports_data),
                'successful_news_crawl': len([n for n in news_data if n.get('content') and len(n['content']) > 50]),
                'successful_reports_crawl': len([r for r in reports_data if r.get('summary') and len(r['summary']) > 50]),
                'news_sentiment': news_analysis.get('overall_sentiment', 'unknown'),
                'reports_outlook': reports_analysis.get('overall_outlook', 'unknown')
            }
        }

        # 5. JSON 파일 저장
        logger.info("💾 통합 결과 JSON 파일 저장 중...")
        filename = self._save_integrated_json(integrated_result)

        if filename:
            logger.info(f"✅ 통합 JSON 파일 저장 완료: {filename}")
            integrated_result['saved_file'] = filename

        logger.info("=" * 60)
        logger.info("통합 크롤링 및 분석 완료")
        logger.info("=" * 60)

        return integrated_result

    def _crawl_naver_news(self, section_id: str, limit: int) -> List[Dict]:
        """네이버 뉴스 헤드라인 크롤링 (test_headline_crawler.py 기능 통합)"""
        news_list = []

        try:
            url = f"https://news.naver.com/section/{section_id}"
            logger.info(f"📰 네이버 뉴스 섹션 크롤링: {url}")

            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 헤드라인 뉴스 링크 수집
            headline_selectors = [
                '.section_headline .sa_text_title',
                '.section_latest .sa_text_title',
                '.sa_text_title',
                'a[href*="/article/"]',
            ]

            news_links = []
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

            # 중복 제거
            seen_urls = set()
            unique_news = []
            for news in news_links:
                if news['url'] not in seen_urls:
                    seen_urls.add(news['url'])
                    unique_news.append(news)
                    if len(unique_news) >= limit:
                        break

            logger.info(f"📋 헤드라인 뉴스 {len(unique_news)}개 발견")

            # 각 뉴스의 본문 크롤링
            for idx, news_item in enumerate(unique_news):
                try:
                    logger.info(f"📖 뉴스 본문 크롤링... ({idx + 1}/{len(unique_news)})")

                    content_data = self._crawl_news_content(news_item['url'])

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
                    logger.info(f"✅ 뉴스 수집 완료 ({len(news_list)}/{limit}): '{news_item['title'][:50]}...'")

                    time.sleep(1)  # 서버 부하 방지

                except Exception as e:
                    logger.error(f"뉴스 본문 크롤링 실패: {e}")
                    # 기본 정보라도 저장
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

            logger.info(f"🎉 뉴스 크롤링 완료: 총 {len(news_list)}개 수집")

        except Exception as e:
            logger.error(f"뉴스 크롤링 중 오류: {e}")

        return news_list

    def _crawl_news_content(self, url: str) -> Dict:
        """개별 뉴스 기사 본문 크롤링 (art_crawl 방식)"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 정확한 네이버 뉴스 선택자 사용
            title_selector = "#title_area > span"
            date_selector = "#ct > div.media_end_head.go_trans > div.media_end_head_info.nv_notrans > div.media_end_head_info_datestamp > div:nth-child(1) > span"
            main_selector = "#dic_area"

            # 제목 추출
            title = ''
            try:
                title_elements = soup.select(title_selector)
                title_lst = [t.get_text(strip=True) for t in title_elements]
                title = "".join(title_lst)
            except:
                pass

            # 발행일 추출
            publish_date = ''
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

            # 본문 추출
            content = ''
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
                # ���체 선택자들
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

            # 요약 생성
            summary = ''
            if content:
                sentences = content.split('.')
                if sentences:
                    summary = sentences[0][:200] + ('...' if len(sentences[0]) > 200 else '')

            # 언론사 추출
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

    def _crawl_research_reports(self, limit: int) -> List[Dict]:
        """네이버 증권 리서치 리포트 크롤링"""
        all_reports = []

        # 네이버 금융 리서치 카테고리별 URL
        category_urls = {
            '종목분석': "https://finance.naver.com/research/company_list.naver",
            '산업분석': "https://finance.naver.com/research/industry_list.naver",
            '시황정보': "https://finance.naver.com/research/market_info_list.naver",
            '투자정보': "https://finance.naver.com/research/invest_list.naver"
        }

        logger.info(f"📈 네이버 금융 리서치에서 각 카테���리별 최신 리포트 {limit}개씩 수집")

        for category_name, category_url in category_urls.items():
            try:
                logger.info(f"📊 {category_name} 리포트 크롤링... ({category_url})")

                response = self.session.get(category_url, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # 리포트 테이블 찾기
                table_selectors = [
                    'table.type_1',
                    'table.type_2',
                    'table[summary*="리포트"]',
                    'div.box_type_m table',
                    'table'
                ]

                table = None
                for selector in table_selectors:
                    table = soup.select_one(selector)
                    if table and len(table.find_all('tr')) > 1:
                        logger.info(f"{category_name} 리포트 테이블 발견")
                        break

                if not table:
                    logger.warning(f"{category_name}: 리포트 테이블을 찾을 수 없습니다.")
                    continue

                rows = table.find_all('tr')
                data_rows = rows[1:] if rows[0].find('th') else rows

                count = 0
                for row in data_rows:
                    if count >= limit:
                        break

                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue

                    try:
                        # 제목과 링크 찾기
                        title = ""
                        link = ""

                        for cell in cells[:3]:
                            a_tag = cell.find('a')
                            if a_tag and a_tag.get('href'):
                                title = a_tag.get_text(strip=True)
                                link = a_tag.get('href')

                                if len(title) > 5 and not title.isdigit():
                                    break

                        if not title or not link:
                            continue

                        # URL 정리
                        if link.startswith('/'):
                            link = "https://finance.naver.com" + link
                        elif not link.startswith('http'):
                            link = f"https://finance.naver.com/research/{link}"

                        # 발행일 추출
                        publish_date = ""
                        for cell in reversed(cells):
                            cell_text = cell.get_text(strip=True)
                            if self._is_valid_date(cell_text):
                                publish_date = cell_text
                                break

                        # 증권사 정보 추출
                        provider = ""
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            if any(keyword in cell_text for keyword in ['증권', '투자', '자산', '캐피탈', 'Securities']):
                                provider = cell_text
                                break

                        # 리포트 상세 내용 크롤링 (간소화)
                        content = self._crawl_report_content(link)

                        report_data = {
                            'id': len(all_reports) + 1,
                            'title': title,
                            'link': link,
                            'summary': content if content else title,  # 본문을 summary로 저장
                            'provider': provider,
                            'publish_date': publish_date if publish_date else 'unknown',
                            'category_name': category_name,
                            'category_key': category_name.lower(),
                            'crawled_at': datetime.now().isoformat()
                        }

                        all_reports.append(report_data)
                        count += 1

                        logger.info(f"✅ {category_name}: '{title[:30]}...' 리포트 수집 완료 ({count}/{limit})")

                        time.sleep(1)  # 서버 부하 방지

                    except Exception as e:
                        logger.error(f"{category_name} 리포트 처리 중 오류: {e}")
                        continue

                logger.info(f"🎯 {category_name}: {count}개 리포트 수집 완료")
                time.sleep(2)  # 카테고리 간 딜레이

            except Exception as e:
                logger.error(f"{category_name} 카테고리 크롤링 중 오류: {e}")
                continue

        logger.info(f"📋 전체 리서치 리포트 크롤링 완료: 총 {len(all_reports)}개 수집")
        return all_reports

    def _crawl_report_content(self, link: str) -> str:
        """리포트 상세 내용 크롤링 (간소화)"""
        try:
            response = self.session.get(link, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            content_selectors = [
                'div.view_cnt',
                'td.view_cnt',
                'div.report_content',
                'div.content',
                'div[class*="content"]'
            ]

            for selector in content_selectors:
                try:
                    content_div = soup.select_one(selector)
                    if content_div:
                        # 불필요한 요소 제거
                        for unwanted in content_div.select('script, style, iframe, .ad, .advertisement'):
                            unwanted.decompose()

                        text = content_div.get_text(separator=' ', strip=True)

                        # 텍스트 정리
                        text = re.sub(r'\s+', ' ', text).strip()

                        if len(text) > 100:
                            return text[:500] + "..." if len(text) > 500 else text
                except:
                    continue

            return ""

        except Exception as e:
            logger.warning(f"리포트 본문 크롤링 실패 ({link}): {e}")
            return ""

    def _is_valid_date(self, text: str) -> bool:
        """날짜 형식 검증"""
        import re
        date_patterns = [
            r'\d{4}[-./]\d{1,2}[-./]\d{1,2}',
            r'\d{1,2}[-./]\d{1,2}[-./]\d{2,4}',
            r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일',
            r'\d{2}\.\d{2}\.\d{2}',
            r'\d{4}\.\d{2}\.\d{2}',
        ]

        for pattern in date_patterns:
            if re.search(pattern, text):
                return True
        return False

    def _save_integrated_json(self, data: Dict, filename: str = None) -> str:
        """통합 결과를 JSON 파일로 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"integrated_news_research_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"📁 통합 JSON 파일 저장 완료: {filename}")
            return filename

        except Exception as e:
            logger.error(f"JSON 파일 저장 실패: {e}")
            return None

    def analyze_news_sentiment(self, news_data: List[Dict]) -> Dict:
        """
        뉴스 감정 분석

        Args:
            news_data: 뉴스 데이터 리스트

        Returns:
            Dict: 감정 분석 결과
        """
        if not news_data:
            return {"error": "분석할 뉴스 데이터가 없습니다."}

        # 뉴스 제목과 내용을 하나의 텍스트로 결합
        combined_text = ""
        for idx, news in enumerate(news_data, 1):
            combined_text += f"\n\n--- 뉴스 {idx} ---\n"
            combined_text += f"제목: {news.get('title', '')}\n"
            # content가 비어있으면 제목만 사용
            content = news.get('content', '')
            if content.strip():
                combined_text += f"내용: {content[:500]}...\n"
            else:
                combined_text += f"내용: 제목 참조\n"

        # 통합된 프롬프트 생성 함수 사용
        prompt = self.create_news_analysis_prompt(combined_text)

        try:
            response = self.ask_question_to_gemini_cache(prompt)

            parsed_result = self.json_match(response)

            if parsed_result:
                parsed_result['analyzed_at'] = datetime.now().isoformat()
                parsed_result['news_count'] = len(news_data)
                return parsed_result
            else:
                # JSON 파싱 실패 시 기본값 반환
                return {
                    "overall_sentiment": "neutral",
                    "sentiment_score": 0,
                    "key_themes": ["분석 실패"],
                    "market_impact": "JSON 파싱 실패로 상세 분석을 제공할 수 없습니다.",
                    "summary": "뉴스 분석 중 오류가 발생했습니다.",
                    "investment_signals": "hold",
                    "analyzed_at": datetime.now().isoformat(),
                    "news_count": len(news_data),
                    "error": "JSON 파싱 실패"
                }

        except Exception as e:
            logger.error(f"뉴스 감정 분석 중 오류: {e}")
            return {"error": f"분석 중 오류 발생: {str(e)}"}

    def analyze_research_reports(self, reports_data: List[Dict]) -> Dict:
        """
        리서치 리포트 분석 (개선된 버전 - 카테고리별 분석 포괄)

        Args:
            reports_data: 리포트 데이터 리스트

        Returns:
            Dict: 리포트 분석 결과
        """
        if not reports_data:
            return {"error": "분석할 리포트 데이터가 없습니다."}

        # 카테고리별로 리포트 분류
        categorized_reports = {}
        for report in reports_data:
            category = report.get('category_name', 'unknown')
            if category not in categorized_reports:
                categorized_reports[category] = []
            categorized_reports[category].append(report)

        # 분석용 텍스트 생성
        combined_text = self._format_reports_for_analysis(categorized_reports)

        # 통합된 리서치 리포트 분석 프롬프트 사용
        prompt = self.create_research_reports_analysis_prompt(combined_text)

        try:
            response = self.ask_question_to_gemini_cache(prompt)

            parsed_result = self.json_match(response)

            if parsed_result:
                # 필수 항목이 모두 포함되었는지 검증
                required_fields = [
                    'category_summary', 'top_mentioned_stocks', 'key_industries',
                    'investment_themes', 'market_outlook', 'risk_factors',
                    'opportunities', 'analyst_consensus', 'summary'
                ]

                # 누락된 필드가 있으면 기본값으로 채우기
                for field in required_fields:
                    if field not in parsed_result:
                        if field == 'category_summary':
                            parsed_result[field] = {"종목분석": "분석 데이터 부족", "산업분석": "분석 데이터 부족", "시황정보": "분석 데이터 부족", "투자정보": "분석 데이터 부족"}
                        elif field in ['top_mentioned_stocks', 'key_industries', 'investment_themes', 'risk_factors', 'opportunities']:
                            parsed_result[field] = ["데이터 부족"]
                        elif field == 'market_outlook':
                            parsed_result[field] = "neutral"
                        elif field in ['analyst_consensus', 'summary']:
                            parsed_result[field] = "분석 데이터가 부족합니다."

                parsed_result['analyzed_at'] = datetime.now().isoformat()
                parsed_result['reports_count'] = len(reports_data)
                parsed_result['category_counts'] = {
                    cat: len(reports) for cat, reports in categorized_reports.items()
                }
                return parsed_result
            else:
                # JSON 파싱 실패 시 기본값 반환
                return {
                    "category_summary": {
                        "종목분석": "JSON 파싱 실패로 분석할 수 없습니다.",
                        "산업분석": "JSON 파싱 실패로 분석할 수 없습니다.",
                        "시황정보": "JSON 파싱 ���패로 분석할 수 없습니다.",
                        "투자정보": "JSON 파싱 실패로 분석할 수 없습니다."
                    },
                    "top_mentioned_stocks": ["분석 실패"],
                    "key_industries": ["분석 실패"],
                    "investment_themes": ["분석 실패"],
                    "market_outlook": "neutral",
                    "risk_factors": ["JSON 파싱 실패로 리스크 분석을 제공할 수 없습니다."],
                    "opportunities": ["JSON 파싱 실패로 기회 분석을 제공할 수 없습니다."],
                    "analyst_consensus": "리포트 분석 중 JSON 파싱 오류가 발생했습니다.",
                    "summary": "전체 리포트 분석 중 오류가 발생하여 상세 분석을 제공할 수 없습니다.",
                    "raw_response": response,
                    "analyzed_at": datetime.now().isoformat(),
                    "reports_count": len(reports_data),
                    "error": "JSON 파싱 실패"
                }

        except Exception as e:
            logger.error(f"리서치 리포트 분석 중 오류: {e}")
            return {"error": f"분석 중 오��� 발생: {str(e)}"}

    def _format_reports_for_analysis(self, categorized_reports: Dict) -> str:
        """
        카테고리별 리포트 데이터를 분석할 텍스트로 포맷팅
        """
        formatted_text = ""

        category_names = {
            'stock_analysis': '종목분석 리포트',
            'industry_analysis': '산업분석 리포트',
            'market_info': '시황정보 리포트',
            'investment_info': '투자정보 리포트',
            '종목분석': '종목분석 리포트',
            '산업분석': '산업분석 리포트',
            '시황정보': '시황정보 리포트',
            '투자정보': '투자정보 리포트'
        }

        for category, reports in categorized_reports.items():
            if reports:
                display_name = category_names.get(category, category)
                formatted_text += f"\n\n=== {display_name} ===\n"

                for idx, report in enumerate(reports, 1):
                    formatted_text += f"\n{idx}. 제목: {report.get('title', 'N/A')}\n"

                    if report.get('provider'):
                        formatted_text += f"   증권사: {report['provider']}\n"

                    # summary가 비어있으면 제목으로 대체
                    summary = report.get('summary', '')
                    if summary.strip() and summary != "요약 내용을 찾을 수 없습니다.":
                        formatted_text += f"   요약: {summary[:200]}...\n"
                    else:
                        formatted_text += f"   요약: 제목 참조\n"

                    if report.get('publish_date'):
                        formatted_text += f"   날짜: {report['publish_date']}\n"

        return formatted_text

    def analyze_comprehensive_with_categories(self, crawled_data: Dict) -> Dict:
        """
        카테고리별 상세 분석을 포함한 종합 분석

        Args:
            crawled_data: 크롤링된 전체 데이터

        Returns:
            Dict: 종합 분석 결과 (카테고리별 세부 분석 포함)
        """
        logger.info("카테고리별 상세 종합 분석 시작")

        # 전체 뉴스 감정 분석
        news_analysis = self.analyze_news_sentiment(crawled_data.get('main_news', []))
        logger.info("뉴스 감정 분석 완료")

        # 리서치 리포트 분석
        reports_analysis = self.analyze_research_reports(crawled_data.get('research_reports', []))
        logger.info("리서치 리포트 분석 완료")

        # 카테고리별 심화 분석
        category_insights = self._generate_category_insights(crawled_data.get('research_reports', []))
        logger.info("카테고리별 심화 분석 완료")

        # 일일 종합 리포트 생성
        daily_report = self.generate_enhanced_daily_report(news_analysis, reports_analysis, category_insights)
        logger.info("일일 종합 리포트 생성 완료")

        return {
            'news_analysis': news_analysis,
            'reports_analysis': reports_analysis,
            'category_insights': category_insights,
            'daily_report': daily_report,
            'meta': {
                'total_analyzed': len(crawled_data.get('main_news', [])) + len(crawled_data.get('research_reports', [])),
                'analysis_completed_at': datetime.now().isoformat()
            }
        }

    def _generate_category_insights(self, reports_data: List[Dict]) -> Dict:
        """
        카테고리별 심화 인사이트 생성
        """
        if not reports_data:
            return {"error": "분석할 리포트가 없습니다."}

        # 카테고리별 통계
        category_stats = {}
        for report in reports_data:
            category = report.get('category_name', 'Unknown')
            if category not in category_stats:
                category_stats[category] = {
                    'count': 0,
                    'firms': set(),
                    'stocks': set(),
                    'recent_titles': []
                }

            category_stats[category]['count'] += 1

            if report.get('provider'):
                category_stats[category]['firms'].add(report['provider'])

            if report.get('title'):
                category_stats[category]['recent_titles'].append(report['title'])

        # 통계를 JSON 직렬화 가능한 ���태로 변환
        formatted_stats = {}
        for category, stats in category_stats.items():
            formatted_stats[category] = {
                'count': stats['count'],
                'active_firms': list(stats['firms'])[:5],  # 최대 5개
                'mentioned_stocks': list(stats['stocks'])[:10],  # 최대 10개
                'sample_titles': stats['recent_titles'][:3]  # 최대 3개
            }

        return {
            'category_statistics': formatted_stats,
            'total_categories': len(category_stats),
            'most_active_category': max(category_stats.keys(), key=lambda k: category_stats[k]['count']) if category_stats else None,
            'generated_at': datetime.now().isoformat()
        }

    def generate_enhanced_daily_report(self, news_analysis: Dict, reports_analysis: Dict, category_insights: Dict) -> Dict:
        """
        카테고리 인사이트를 포함한 개선된 일일 리포트 생성
        """
        # 간단한 점수 계산
        try:
            sentiment_score = news_analysis.get('sentiment_score', 50)
            market_sentiment_score = max(1, min(10, int(sentiment_score / 10)))

            return {
                'market_sentiment_score': market_sentiment_score,
                'confidence_level': 7,  # 기본 신뢰도
                'summary': f"뉴스 {news_analysis.get('news_count', 0)}개, 리포트 {reports_analysis.get('reports_count', 0)}개 분석 완료",
                'recommendations': [
                    "시장 동향을 지속적으로 모니터링하세요",
                    "리스크 관리를 철저히 하세요"
                ],
                'generated_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"일일 리포트 생성 중 오류: {e}")
            return {"error": f"일일 리포트 생성 실패: {str(e)}"}
