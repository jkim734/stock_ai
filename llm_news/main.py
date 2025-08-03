import sys
import os
from datetime import datetime
import json
import importlib.util

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
        test_py_path = os.path.join(llm_core_path, 'test.py')
        spec = importlib.util.spec_from_file_location("llm_test_module", test_py_path)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)

        # JSON 데이터를 llm_test 함수에 ��달
        buy_candidates = test_module.llm_test(json_data=json_data)

        print("\n✅ llm_core 분석 완료!")
        return buy_candidates

    except Exception as e:
        print(f"❌ llm_core test.py 실행 중 오류: {e}")
        print(f"💡 JSON 파일 경로: {json_file_path}")
        return None

def main():
    """
    메인 실행 함수
    """
    print("=" * 80)
    print("🚀 통합 뉴스 분석 & 자동 매매 시스템 시작")
    print("=" * 80)

    try:
        # 1. 통합 뉴스 분���기 초기화
        analyzer = IntegratedNewsAnalyzer()

        # 2. 뉴스 크롤링 및 분석 실행
        print("\n📰 뉴스 크롤링 및 분석 시작...")

        # 경제 섹션 (sid=101) 크롤링 - crawl_and_analyze_all 메서드 사용
        # 파라미터: news_section_id="101", news_limit=20, reports_limit=10
        results = analyzer.crawl_and_analyze_all(news_section_id="101", news_limit=20, reports_limit=10)

        if not results:
            print("❌ 뉴스 분석 결과가 없습니다.")
            return

        # 3. JSON 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"integrated_news_research_{timestamp}.json"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_filepath = os.path.join(current_dir, json_filename)

        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"💾 분석 결과 저장 완료: {json_filename}")

        # 4. llm_core의 test.py 자동 실행
        buy_candidates = call_llm_test_with_json(json_filepath)

        if buy_candidates:
            print(f"\n🎯 최종 매수 후보: {len(buy_candidates)}개 종목")
            for i, candidate in enumerate(buy_candidates, 1):
                print(f"   {i}. {candidate['company_name']} ({candidate['stock_code']})")
        else:
            print("\n📋 매수 후보 종목이 없습니다.")

        print("\n✅ 전체 프로���스 완료!")

    except Exception as e:
        print(f"❌ 메인 프로세스 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
