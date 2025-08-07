#!/usr/bin/env python3
"""
통합 뉴스 & 리서치 크롤링 및 분석 실행 스크립트
"""

import sys
import os
from datetime import datetime
import json

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from news_analyzer import IntegratedNewsAnalyzer

def call_llm_test_with_json(json_file_path):
    """
    생성된 JSON 파일을 llm_core의 test.py에 전달하여 실행
    """
    try:
        # llm_core 모듈 경로 추가
        llm_core_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'llm_core')

        # 기존 sys.path에 llm_core 경로가 없으면 추가
        if llm_core_path not in sys.path:
            sys.path.insert(0, llm_core_path)  # 맨 앞에 추가하여 우선순위 높임

        # JSON 파일 로드
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        print(f"\n🔄 llm_core test.py 자동 실행...")
        print("=" * 60)

        # llm_core의 test.py를 직접 실행하는 방식으로 변경
        import importlib.util

        test_py_path = os.path.join(llm_core_path, 'test.py')
        spec = importlib.util.spec_from_file_location("llm_test_module", test_py_path)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)

        # JSON 데이터를 llm_test 함수에 전달
        test_module.llm_test(json_data=json_data)

        print("\n✅ llm_core 분석 완료!")

    except Exception as e:
        print(f"❌ llm_core test.py 실행 중 오류: {e}")
        print(f"💡 JSON 파일 경로: {json_file_path}")

        # 상세 오류 정보 출력
        import traceback
        print("상세 오류 정보:")
        traceback.print_exc()

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
    print("   - 뉴스 섹션: 경제(101)")  # 경제 섹션을 101로 수정
    print("   - 뉴스 수집 개수: 20개")
    print("   - 리포트 수집 개수: 카테고리별 10개씩")
    print("   - AI 분석: Gemini API 활용")
    print()

    try:
        # 통합 크롤링 및 분석 실행
        print("🎯 통합 크롤링 및 분석 시작...")
        result = analyzer.crawl_and_analyze_all(
            news_section_id="101",  # 경제 섹��을 101로 수정
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
                print(f"   - 감정 점수: {news_analysis.get('sentiment_score', '알 수 ��음')}")
                print(f"   - 핵심 테마: {', '.join(news_analysis.get('key_themes', [])[:3])}")
                print(f"   - 투자 신호: {news_analysis.get('investment_signals', '알 수 없음')}")
            else:
                print(f"   - 뉴스 분석: 실패 ({news_analysis.get('error', '알 수 없는 오류')})")

            if reports_analysis and not reports_analysis.get('error'):
                print(f"   - 시장 전망: {reports_analysis.get('market_outlook', '알 수 없음')}")
                print(f"   - 주요 ��목: {', '.join(reports_analysis.get('top_mentioned_stocks', [])[:3])}")
                print(f"   - 핵심 산업: {', '.join(reports_analysis.get('key_industries', [])[:3])}")
            else:
                print(f"   - 리포트 분석: 실패 ({reports_analysis.get('error', '알 수 없는 오류')})")

            # 저장된 파일 정보
            if 'saved_file' in result:
                json_file_path = result['saved_file']
                print(f"\n💾 결과 파일:")
                print(f"   - JSON 파일: {json_file_path}")

                # 파일 크기 계산
                try:
                    file_size = os.path.getsize(json_file_path) / 1024  # KB
                    print(f"   - 파일 크기: {file_size:.1f} KB")
                except:
                    pass

                # llm_core/test.py 자동 실행
                call_llm_test_with_json(json_file_path)

            print(f"\n⏰ 완료 시간: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}")

        else:
            print("❌ 크롤링 또는 분석 실패")
            return

    except Exception as e:
        print(f"❌ 시스템 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
