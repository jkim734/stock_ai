#!/usr/bin/env python3
"""
통합 뉴스 & 리서치 크롤링 및 분석 실행 스크립트
"""

import sys
import os
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from news_analyzer import IntegratedNewsAnalyzer

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🚀 통합 뉴스 & 리서치 크롤링 및 분석 시스템")
    print("=" * 80)
    print(f"📅 실행 시간: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}")
    print()

    # 통합 분석기 인스턴스 생성
    analyzer = IntegratedNewsAnalyzer()

    print("🔧 시스템 설정:")
    print("   - 뉴스 섹션: 정치(101)")
    print("   - 뉴스 수집 개수: 20개")
    print("   - 리포트 수집 개수: 카테고리별 10개씩")
    print("   - AI 분석: Gemini API 활용")
    print()

    try:
        # 통합 크롤링 및 분석 실행
        print("🎯 통합 크롤링 및 분석 시작...")
        result = analyzer.crawl_and_analyze_all(
            news_section_id="101",  # 정치 섹션
            news_limit=20,          # 뉴스 20개
            reports_limit=10        # 카테고리별 리포트 10개씩
        )

        # 결과 요약 출력
        if result and 'metadata' in result:
            print("\n" + "=" * 80)
            print("📊 크롤링 및 분석 결과 요약")
            print("=" * 80)

            metadata = result['metadata']
            summary = result.get('summary', {})

            print(f"📰 뉴스 크롤링:")
            print(f"   - 총 수집 뉴스: {metadata.get('news_count', 0)}개")
            print(f"   - 본문 크롤링 성공: {summary.get('successful_news_crawl', 0)}개")

            print(f"\n📈 리서치 리포트 크롤링:")
            print(f"   - 총 수집 리포트: {metadata.get('reports_count', 0)}개")
            print(f"   - 본문 크롤링 성공: {summary.get('successful_reports_crawl', 0)}개")

            print(f"\n🤖 AI 분석 결과:")
            news_analysis = result.get('news', {}).get('analysis', {})
            reports_analysis = result.get('research_reports', {}).get('analysis', {})

            if news_analysis and not news_analysis.get('error'):
                print(f"   - 뉴스 감정: {news_analysis.get('overall_sentiment', '알 수 없음')}")
                print(f"   - 감정 점수: {news_analysis.get('sentiment_score', '알 수 없음')}")
                print(f"   - 핵심 테마: {', '.join(news_analysis.get('key_themes', [])[:3])}")
                print(f"   - 투자 신호: {news_analysis.get('investment_signals', '알 수 없음')}")
            else:
                print(f"   - 뉴스 분석: 실패 ({news_analysis.get('error', '알 수 없는 오류')})")

            if reports_analysis and not reports_analysis.get('error'):
                print(f"   - 시장 전망: {reports_analysis.get('market_outlook', '알 수 없음')}")
                print(f"   - 주요 종목: {', '.join(reports_analysis.get('top_mentioned_stocks', [])[:3])}")
                print(f"   - 핵심 산업: {', '.join(reports_analysis.get('key_industries', [])[:3])}")
            else:
                print(f"   - 리포트 분석: 실패 ({reports_analysis.get('error', '알 수 없는 오류')})")

            # 저장된 파일 정보
            if 'saved_file' in result:
                print(f"\n💾 결과 파일:")
                print(f"   - JSON 파일: {result['saved_file']}")

                # 파일 크기 계산
                try:
                    file_size = os.path.getsize(result['saved_file']) / 1024  # KB
                    print(f"   - 파일 크기: {file_size:.1f} KB")
                except:
                    pass

            print(f"\n⏰ 완료 시간: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}")

            # 상세 결과 미리보기
            print("\n" + "=" * 80)
            print("📋 상세 결과 미리보기")
            print("=" * 80)

            # 뉴스 미리보기
            news_data = result.get('news', {}).get('data', [])
            if news_data:
                print("📰 수집된 뉴스 (처음 3개):")
                for i, news in enumerate(news_data[:3], 1):
                    print(f"\n{i}. {news.get('title', '제목 없음')}")
                    print(f"   📅 발행일: {news.get('publish_date', '알 수 없음')}")
                    print(f"   📺 언론사: {news.get('media', '알 수 없음')}")
                    print(f"   📝 본문 길이: {len(news.get('content', ''))}자")

                    if news.get('content'):
                        preview = news['content'][:100] + "..." if len(news['content']) > 100 else news['content']
                        print(f"   📖 본문 미리보기: {preview}")

                if len(news_data) > 3:
                    print(f"\n   ... 및 {len(news_data) - 3}개 더")

            # 리포트 미리보기
            reports_data = result.get('research_reports', {}).get('data', [])
            if reports_data:
                print(f"\n📈 수집된 리서치 리포트 (처음 3개):")
                for i, report in enumerate(reports_data[:3], 1):
                    print(f"\n{i}. {report.get('title', '제목 없음')}")
                    print(f"   🏢 증권사: {report.get('provider', '알 수 없음')}")
                    print(f"   📂 카테고리: {report.get('category_name', '알 수 없음')}")
                    print(f"   📅 발행일: {report.get('publish_date', '알 수 없음')}")
                    print(f"   📝 요약 길이: {len(report.get('summary', ''))}자")

                if len(reports_data) > 3:
                    print(f"\n   ... 및 {len(reports_data) - 3}개 더")

            # 성공률 통계
            print(f"\n📊 크롤링 성공률:")
            if news_data:
                news_success_rate = (summary.get('successful_news_crawl', 0) / len(news_data)) * 100
                print(f"   - 뉴스 본문 크롤링: {news_success_rate:.1f}%")

            if reports_data:
                reports_success_rate = (summary.get('successful_reports_crawl', 0) / len(reports_data)) * 100
                print(f"   - 리포트 본문 크롤링: {reports_success_rate:.1f}%")

        else:
            print("❌ 크롤링 또는 분석에 실패했습니다.")
            print("네트워크 연결이나 웹사이트 구조 변경을 확인해주세요.")

    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
        import traceback
        print("\n상세 오류 정보:")
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("🏁 통합 뉴스 & 리서치 분석 완료")
    print("=" * 80)

if __name__ == "__main__":
    main()
