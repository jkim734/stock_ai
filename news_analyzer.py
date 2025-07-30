"""
뉴스 및 리서치 분석 모듈 - Gemini API 활용
"""

from typing import List, Dict
import json
import logging
from datetime import datetime
from _1st_stage_news_analysis_LLM import client, model_name, ask_question_to_gemini_cache, json_match, create_news_analysis_prompt, create_research_reports_analysis_prompt, create_individual_news_analysis_prompt

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    """뉴스 및 리서치 리포트 분석기"""

    def __init__(self):
        self.client = client
        self.model_name = model_name

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
        prompt = create_news_analysis_prompt(combined_text)

        try:
            response = ask_question_to_gemini_cache(prompt)

            parsed_result = json_match(response)

            if parsed_result:
                parsed_result['analyzed_at'] = datetime.now().isoformat()
                parsed_result['news_count'] = len(news_data)
                return parsed_result
            else:
                # JSON 파싱 실패 시 기본값 반환 (메시지 제거)
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
        prompt = create_research_reports_analysis_prompt(combined_text)

        try:
            response = ask_question_to_gemini_cache(prompt)

            parsed_result = json_match(response)

            if parsed_result:
                # 9개 필수 항목이 모두 포함되었는지 검증
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
                            parsed_result[field] = "분석 데이터가 ��족합니다."

                parsed_result['analyzed_at'] = datetime.now().isoformat()
                parsed_result['reports_count'] = len(reports_data)
                parsed_result['category_counts'] = {
                    cat: len(reports) for cat, reports in categorized_reports.items()
                }
                return parsed_result
            else:
                # JSON 파싱 실패 시 9개 항목을 모두 포함한 기본값 반환
                return {
                    "category_summary": {
                        "종목분석": "JSON 파싱 실패로 분석할 수 없습니다.",
                        "산업분석": "JSON 파싱 실패로 분석할 수 없습니다.",
                        "시황정보": "JSON 파싱 실패로 분석할 수 없��니다.",
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
            return {"error": f"분석 중 오류 발생: {str(e)}"}

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

                    if report.get('company'):
                        formatted_text += f"   종목: {report['company']}\n"

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

        # 개별 뉴스 분석 추가
        individual_news_analysis = self.analyze_all_individual_news(crawled_data.get('main_news', []))
        logger.info("개별 뉴스 분석 완료")

        reports_analysis = self.analyze_research_reports(crawled_data.get('research_reports', []))
        logger.info("리서치 리포트 분석 완료")

        # 카테고리별 심화 분석
        category_insights = self._generate_category_insights(crawled_data.get('research_reports', []))
        logger.info("카테고리별 심화 분석 완료")

        # 일일 종합 리포트 생성 (개선된 버전)
        daily_report = self.generate_enhanced_daily_report(news_analysis, reports_analysis, category_insights)
        logger.info("일일 종합 리포트 생성 완료")

        return {
            'news_analysis': news_analysis,
            'individual_news_analysis': individual_news_analysis,  # 개별 뉴스 분석 결과 추가
            'reports_analysis': reports_analysis,
            'category_insights': category_insights,
            'daily_report': daily_report,
            'meta': {
                'total_analyzed': len(crawled_data.get('main_news', [])) + len(crawled_data.get('research_reports', [])),
                'individual_news_analyzed': len(individual_news_analysis),
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

            if report.get('firm'):
                category_stats[category]['firms'].add(report['firm'])

            if report.get('stock_name'):
                category_stats[category]['stocks'].add(report['stock_name'])

            if report.get('title'):
                category_stats[category]['recent_titles'].append(report['title'])

        # 통계를 JSON 직렬화 가능한 형태로 변환
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
        prompt = f"""
다음 분석 결과들을 종합하여 오늘의 주식 시장 종합 리포트를 작성해주세요:

뉴스 분석:
{json.dumps(news_analysis, ensure_ascii=False, indent=2)}

리포트 분석:
{json.dumps(reports_analysis, ensure_ascii=False, indent=2)}

카테고리별 인사이트:
{json.dumps(category_insights, ensure_ascii=False, indent=2)}

다음 항목들을 JSON 형식으로 작성해주세요:
1. executive_summary: 경영진 요약 (3-4문장, 핵심만)
2. market_sentiment_score: 시장 감정 점수 (1-10, 숫자만)
3. key_trends: 주요 트렌드 (배열, 각 2-3단어)
4. sector_spotlight: 주목받는 섹터 (배열, 상위 3개)
5. stock_picks: 주목할 종목들 (배열, 상위 5개)
6. risk_watch: 주의깊게 봐야할 리스크 (배열, 상위 3개)
7. tomorrow_outlook: 내일 전망 (2-3문장)
8. action_items: 투자자 행동 지침 (배열, 각 한 문��)
9. confidence_level: 분석 신뢰도 (1-10, 숫자만)
10. data_quality_score: 데이터 품질 점수 (1-10, 숫자만)

응답은 반드시 JSON 형식으로만 해주세요.
"""

        try:
            response = ask_question_to_gemini_cache(prompt)

            try:
                enhanced_report = json.loads(response)
                enhanced_report['generated_at'] = datetime.now().isoformat()
                enhanced_report['based_on'] = {
                    'news_count': news_analysis.get('news_count', 0),
                    'reports_count': reports_analysis.get('reports_count', 0),
                    'categories_analyzed': category_insights.get('total_categories', 0)
                }
                return enhanced_report
            except json.JSONDecodeError:
                return {
                    "raw_response": response,
                    "generated_at": datetime.now().isoformat(),
                    "error": "JSON 파싱 실패"
                }

        except Exception as e:
            logger.error(f"개선된 일일 리포트 생성 중 오류: {e}")
            return {"error": f"리포트 생성 중 오류 발생: {str(e)}"}

    def analyze_individual_news(self, news_item: Dict) -> Dict:
        """
        개별 뉴스 분석

        Args:
            news_item: ��별 뉴스 데이터

        Returns:
            Dict: 개별 뉴스 분석 결과
        """
        if not news_item or not news_item.get('title'):
            return {"error": "분석할 뉴스 데이터가 없습니다."}

        # 개별 뉴스 분석 프롬프트 생성
        prompt = create_individual_news_analysis_prompt(news_item)

        try:
            response = ask_question_to_gemini_cache(prompt)
            parsed_result = json_match(response)

            if parsed_result:
                parsed_result['analyzed_at'] = datetime.now().isoformat()
                parsed_result['original_title'] = news_item.get('title', '')
                parsed_result['original_link'] = news_item.get('link', '')
                return parsed_result
            else:
                # JSON 파싱 실패 시 기본값 반환
                return {
                    "summary": "분석 실패",
                    "entities": "분석 불가",
                    "impact": "JSON 파싱 실패로 상세 분석을 제공할 수 없습니다.",
                    "type": "산업",
                    "reason": "분석 실패로 인한 기본 분류",
                    "analyzed_at": datetime.now().isoformat(),
                    "original_title": news_item.get('title', ''),
                    "original_link": news_item.get('link', ''),
                    "error": "JSON 파싱 실패"
                }

        except Exception as e:
            logger.error(f"개별 뉴스 분석 중 오류: {e}")
            return {"error": f"분석 중 오류 발생: {str(e)}"}

    def analyze_all_individual_news(self, news_data: List[Dict]) -> List[Dict]:
        """
        모든 뉴스를 개별적으로 분석

        Args:
            news_data: 뉴스 데이터 리스트

        Returns:
            List[Dict]: 각 뉴스의 개별 분석 결과 리스트
        """
        if not news_data:
            return []

        individual_analyses = []
        logger.info(f"개별 뉴스 분석 시작: {len(news_data)}개")

        for idx, news_item in enumerate(news_data, 1):
            try:
                logger.info(f"개별 뉴스 분석 ({idx}/{len(news_data)}): {news_item.get('title', '')[:50]}...")
                analysis = self.analyze_individual_news(news_item)
                individual_analyses.append(analysis)

                # API 부하 방지를 위한 딜레이
                if idx < len(news_data):  # 마지막이 아닌 경우에만
                    import time
                    time.sleep(1)

            except Exception as e:
                logger.error(f"개별 뉴스 분석 실패 ({idx}): {e}")
                # 실패한 경우에도 기본 구조 추가
                individual_analyses.append({
                    "summary": "분석 실패",
                    "entities": "분석 불가",
                    "impact": f"분석 중 오류 발생: {str(e)}",
                    "type": "산업",
                    "reason": "분석 오류로 인한 기본 분류",
                    "analyzed_at": datetime.now().isoformat(),
                    "original_title": news_item.get('title', ''),
                    "original_link": news_item.get('link', ''),
                    "error": str(e)
                })
                continue

        logger.info(f"개별 뉴스 분석 완료: {len(individual_analyses)}개")
        return individual_analyses
