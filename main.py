"""
네이버 증권 뉴스 크롤링 및 AI 분석 시스템 메인 실행 파일
"""

import json
import logging
from datetime import datetime
from news_crawler import NaverStockNewsCrawler
from news_analyzer import NewsAnalyzer

# 로깅 설정 (간단한 진행 상황 표시)
logging.basicConfig(
    level=logging.INFO,  # WARNING에서 INFO로 복구
    format='%(message)s',  # 간단한 메시지만 출력
    handlers=[
        logging.StreamHandler()  # 콘솔 출력만
    ]
)

logger = logging.getLogger(__name__)

class StockNewsAnalysisSystem:
    """주식 뉴스 분석 시스템 메인 클래스"""

    def __init__(self):
        self.crawler = NaverStockNewsCrawler()
        self.analyzer = NewsAnalyzer()

    def run_daily_analysis(self, news_limit: int = 10, reports_limit: int = 10) -> dict:
        """
        일일 뉴스 분석 실행 (카테고리별 상세 분석 포함)

        Args:
            news_limit: 크롤링할 뉴스 개수
            reports_limit: 각 카테고리별로 크롤링할 리포트 개수

        Returns:
            Dict: 전체 분석 결과
        """
        logger.info("--- 일일 주식 뉴스 분석 시작 ---")

        try:
            # 1. 뉴스 및 리포트 크롤링
            logger.info("1단계: 뉴스 및 리포트 크롤링 시작")
            crawled_data = self.crawler.get_today_summary()

            if crawled_data['total_count'] == 0:
                logger.warning("크롤링된 데이터가 없습니다.")
                return {"error": "크롤링된 데이터가 없습니다."}

            # 크롤링 현황 출력
            logger.info(f"뉴스 크롤링: {len(crawled_data['main_news'])}개")
            logger.info(f"리포트 크롤링: {len(crawled_data['research_reports'])}개")

            # 카테고리별 통계 출력
            category_counts = {}
            for report in crawled_data['research_reports']:
                category = report.get('category_name', 'Unknown')
                category_counts[category] = category_counts.get(category, 0) + 1

            if category_counts:
                for category, count in category_counts.items():
                    logger.info(f"  {category}: {count}개")

            # 2. AI 분석 수행 (카테고리별 상세 분석 포함)
            logger.info("Gemini API 분석 시작")
            analysis_result = self.analyzer.analyze_comprehensive_with_categories(crawled_data)

            # 3. 결과 저장
            self._save_results(crawled_data, analysis_result)

            logger.info("분석 완료")

            return {
                'crawled_data': crawled_data,
                'analysis_result': analysis_result,
                'status': 'success'
            }

        except Exception as e:
            logger.error(f"분석 시스템 실행 중 오류: {e}")
            return {"error": f"시스템 실행 중 오류: {str(e)}"}

    def _save_results(self, crawled_data: dict, analysis_result: dict):
        """분석 결과를 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 크롤링 데이터 저장
        with open(f'crawled_data_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(crawled_data, f, ensure_ascii=False, indent=2)

        # 분석 결과 저장
        with open(f'analysis_result_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)

        logger.info(f"결과 파일 저장 완료: crawled_data_{timestamp}.json, analysis_result_{timestamp}.json")

    def print_summary(self, result: dict):
        """분��� 결과 요약 출력 (간소화된 버전)"""
        if 'error' in result:
            print(f"❌ 오류: {result['error']}")
            return

        analysis = result['analysis_result']

        print("\n" + "-"*50)
        print("<오늘의 주식 시장 분석 결과>")
        print("-"*50)

        # 뉴스 분석 요약
        if 'news_analysis' in analysis:
            news = analysis['news_analysis']
            print(f"\n📰 뉴스 분석 ({news.get('news_count', 0)}개)")
            print(f"   감정: {news.get('overall_sentiment', 'N/A')}")
            print(f"   점수: {news.get('sentiment_score', 'N/A')}/100")
            if 'summary' in news:
                print(f"   ���약: {news['summary']}")

        # 리포트 분석 요약 (카테고리별)
        if 'reports_analysis' in analysis:
            reports = analysis['reports_analysis']
            print(f"\n📋 리포트 분석 ({reports.get('reports_count', 0)}개)")
            print(f"   시장 전망: {reports.get('market_outlook', 'N/A')}")

            if 'top_mentioned_stocks' in reports:
                stocks = reports['top_mentioned_stocks'][:5]
                if stocks:
                    print(f"   주목 종목: {', '.join(stocks)}")

        # 일일 종합 분석
        if 'daily_report' in analysis:
            daily = analysis['daily_report']
            if 'error' not in daily:
                print(f"\n⭐ 종합 평가")
                print(f"   시장 감정 점수: {daily.get('market_sentiment_score', 'N/A')}/10")
                print(f"   신뢰도: {daily.get('confidence_level', 'N/A')}/10")

    def print_detailed_category_analysis(self, result: dict):
        """카테고리별 상세 분석 결과 출력 (간소화된 버전)"""
        if 'error' in result or 'category_insights' not in result['analysis_result']:
            return

        analysis = result['analysis_result']
        insights = analysis['category_insights']

        if 'category_statistics' in insights:
            print(f"\n" + "-"*50)
            print("<카테고리별 상세 분석>")

            stats = insights['category_statistics']
            for category, data in stats.items():
                print(f"\n📂 {category}")
                print(f"   리포트 수: {data.get('count', 0)}개")
                if data.get('mentioned_stocks'):
                    print(f"   언급된 종목: {', '.join(data['mentioned_stocks'][:3])}")

def main():
    """메인 실행 함수"""
    print("🚀 네이버 증권 AI 분석 시스템")

    # 시스템 초기화
    system = StockNewsAnalysisSystem()

    # 분석 실행
    result = system.run_daily_analysis(news_limit=20, reports_limit=5)

    # 기본 요약 결과 출력
    system.print_summary(result)

    # 카테고리별 상세 분석 출력 (리포트가 있을 때만)
    system.print_detailed_category_analysis(result)

    print(f"\n{'-'*50}")
    print("<분석 완료>")

if __name__ == "__main__":
    main()
