from llm_caller import *
from crawling import crawl_naver_news_by_keyword
import time
import csv
import os
import kis

def load_stock_codes():
    """
    stock_list.csv 파일에서 종목명:종목코드 딕셔너리를 생성
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, 'stock_list.csv')
    
    stock_dict = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('code'): # 헤더 스킵
                continue
            code, name = line.strip().split(',')
            stock_dict[name] = code
    return stock_dict

def llm_test(article: str = None, json_data: dict = None):
    """
    LLM 테스트 함수 - 기존 기사 분석 또는 JSON 데이터 분석
    """

    # JSON 데이터가 전달된 경우 (통합 뉴스 분석 모드)
    if json_data:
        print("=" * 60)
        print("🔄 통합 뉴스 JSON 데이터 분석 모드")
        print("=" * 60)

        # 종목코드 딕셔너리 로드
        stock_codes = load_stock_codes()
        buy_stocks = []  # 매수할 종목 리스트

        # 뉴스 데이터에서 기사들 추출
        news_items = json_data.get('news', {}).get('data', [])

        if not news_items:
            print("❌ 분석할 뉴스 데이터가 없습니다.")
            return

        print(f"📊 총 {len(news_items)}개 뉴스 기사 분석 시작...")

        # 각 뉴스 기사를 개별적으로 LLM 분석
        for i, news_item in enumerate(news_items[:10], 1):  # 최대 10개 기사만 분석
            title = news_item.get('title', '')
            content = news_item.get('content', '')

            if not content or len(content) < 50:  # 내용이 너무 짧으면 스킵
                print(f"📰 뉴스 {i}: 내용 부족으로 스킵 - {title[:30]}...")
                continue

            # 제목과 내용을 합쳐서 분석용 텍스트 생성
            article_text = f"{title}\n\n{content}"

            print(f"\n📰 뉴스 {i} 분석: {title[:50]}...")

            try:
                # LLM 분류 테스트
                category = classify_llm(article_text)
                print(f"   분류 결과: {category}")

                if category == "경제 기사":
                    company_result = company_llm(article_text)
                    # 경제기사에서 나온 기업들의 종목 코드 찾기
                    if isinstance(company_result, dict):
                        company_name = company_result.get('company')

                        # 미리 지정된 종목에 해당하면 종목 코드 출력
                        if company_name in stock_codes:
                            print(f"   ✅ 기업: {company_name}, 종목코드: {stock_codes[company_name]}")
                            print(f"   📈 이유: {company_result.get('reason', '')}")

                            # 중복 체크 후 매수 리스트에 추가
                            if stock_codes[company_name] not in buy_stocks:
                                buy_stocks.append(stock_codes[company_name])
                        else:
                            print(f"   ⚠️ 기업: {company_name}, 종목코드: 미상장")
                            print(f"   📄 이유: {company_result.get('reason', '')}")

                elif category == "정책 기사":
                    positives = policy_llm(article_text)

                    if positives:
                        print(f"   📊 긍정적 업종 {len(positives)}개 발견")

                        # 정책 기사에서 긍정적인 업종 추출 후 각 업종 심층 분석
                        for policy_category in positives[:2]:  # 최대 2개 업종만 분석
                            category_name = policy_category.get('category', '')
                            category_reason = policy_category.get('reason', '')

                            print(f"   🔍 {category_name} 업종 분석 중...")

                            try:
                                # 해당 업종 관련 뉴스 크롤링
                                sector_articles = crawl_naver_news_by_keyword(category_name, page=1, sort=1)
                                comp_result = competitive_llm(category_name, category_reason, sector_articles)

                                companies = comp_result.get('companies', [])
                                for company in companies:
                                    company_name = company.get('company')
                                    if company_name in stock_codes:
                                        print(f"   ✅ 업종: {category_name}, 기업: {company_name}")
                                        print(f"   📈 종목코드: {stock_codes[company_name]}")
                                        print(f"   📄 이유: {company.get('reason', '')}")

                                        # 중복 체크 후 매수 리스트에 추가
                                        if stock_codes[company_name] not in buy_stocks:
                                            buy_stocks.append(stock_codes[company_name])
                                    else:
                                        print(f"   ⚠️ 업종: {category_name}, 기업: {company_name}, 종목코드: 미상장")
                            except Exception as e:
                                print(f"   ❌ {category_name} 업종 분석 실패: {e}")
                    else:
                        print(f"   ℹ️ 긍정적 업종이 발견되지 않았습니다.")

                else:
                    print(f"   ℹ️ 분류 결과: {category} - 추가 분석하지 않음")

            except Exception as e:
                print(f"   ❌ 뉴스 분석 실패: {e}")
                continue

        # 매수 결정 요약
        print(f"\n💰 매수 결정 요약")
        print("=" * 60)

        if len(buy_stocks) > 0:
            print(f"📋 총 {len(buy_stocks)}개 종목 매수 후보:")
            for i, stock_code in enumerate(buy_stocks, 1):
                # 종목명 찾기
                stock_name = None
                for name, code in stock_codes.items():
                    if code == stock_code:
                        stock_name = name
                        break

                print(f"   {i}. {stock_name} ({stock_code})")

                # 실제 매수 실행
                try:
                    print(f"   💸 매수 실행 중...")
                    kis.buy_stock(stock_code, 1)  # 1주씩 매수
                    print(f"   ✅ 매수 완료!")
                except Exception as e:
                    print(f"   ❌ 매수 실패: {e}")
        else:
            print("📭 매수할 종목이 발견되지 않았습니다.")

        return

    # 기존 단일 기사 분석 모드
    if not article:
        print("❌ 분석할 기사 또는 JSON 데이터가 제공되지 않았습니다.")
        return

    print("🧪 단일 기사 분석 모드")
    print("=" * 60)

    # LLM 분류 테스트
    category = classify_llm(article)
    print(f"분류 결과: {category}")

    # 종목코드 딕셔너리 로드
    stock_codes = load_stock_codes()
    buy_stocks = []  # 매수할 종목 리스트

    if category == "경제 기사":
        company_result = company_llm(article)
        # 경제기사에서 나온 기업들의 종목 코드 찾기
        if isinstance(company_result, dict):
            company_name = company_result.get('company')

            # 미리 지정된 종목에 해당하면 종목 코드 출력
            # 종목 코드가 없는 경우 "미상장"으로 표시
            if company_name in stock_codes:
                print(f"기업: {company_name}, 종목코드: {stock_codes[company_name]}, 이유: {company_result.get('reason', '')}")
                buy_stocks.append(stock_codes[company_name])
            else:
                print(f"기업: {company_name}, 종목코드: 미상장, 이유: {company_result.get('reason', '')}")

    elif category == "정책 기사":
        positives = policy_llm(article)

        # 정책 기사에서 긍정적인 업종 추출 후 각 업종 심층 분석 -> �� 호재 업종 마다 competitive_llm 호출
        for category in positives:
            article = crawl_naver_news_by_keyword(category['category'], page=1, sort=1)
            comp_result = competitive_llm(category['category'], category['reason'], article)
            companies = comp_result.get('companies', [])
            for company in companies:
                company_name = company.get('company')
                if company_name in stock_codes:
                    print(f"업종: {category['category']}, 기업: {company_name}, 종목코드: {stock_codes[company_name]}, 이유: {company.get('reason', '')}")
                    buy_stocks.append(stock_codes[company_name])
                else:
                    print(f"업종: {category['category']}, 기업: {company_name}, 종목코드: 미상장, 이유: {company.get('reason', '')}")
    else:
        print("Invalid article type for LLM classification.")
        return

    if len(buy_stocks) > 0:
        for stock in buy_stocks:
            kis.buy_stock(stock)


if __name__ == "__main__":
    start = time.time()
    # 테스트용 기사
    test_article = """
이 이용자는 머스크가 지난 27일 올린 “삼성은 테슬라가 제조 효율성을 극대화하는 데 도움을 주기로 합의했다”는 글을 공유하면서 “삼성은 그들이 무엇에 사인했는지 전혀 모른다”고 주장했다.

이에 머스크는 “그들은 안다”며 “나는 실제 파트너십이 어떤 것일지 논의하기 위해 삼성의 회장 및 고위 경영진과 화상 통화를 했다”고 밝혔다.

머스크는 “훌륭한 성과를 거두기 위해 양사의 강점을 이용할 것”이라고 강조했다.

이후 또 다른 이용자가 “삼성전자는 칩 제조 기술에서 TSMC보다 뒤처져 있다”는 내용의 글을 올리자 머스크는 “TSMC와 삼성 둘 다 훌륭한 회사들”이라며 “그들과 함께 일하는 것은 영광”이라고 옹호했다.


앞서 머스크는 앞서 머스크는 삼성전자의 대규모 파운드리 계약 발표가 나온 뒤 삼성전자의 계약 상대가 테슬라임을 밝힌 바 있다.

머스크는 “삼성의 텍사스 대형 신공장은 테슬라 차세대 AI6 칩 생산에 전념하게 될 것”이라며 “이 전략적 중요성은 아무리 강조해도 지나치지 않다”고 했다.

이어 “165억달러 수치는 단지 최소액”이라며 “실제 생산량은 몇 배 더 높을 것 같다”고 덧붙였다.

이재용 삼성전자 회장이 29일 강서구 서울김포비즈니스항공센터(SGBAC)를 통해 워싱턴으로 출국하고 있다. [사진 = 연합뉴스]사진 확대
이재용 삼성전자 회장이 29일 강서구 서울김포비즈니스항공센터(SGBAC)를 통해 워싱턴으로 출국하고 있다. [사진 = 연합뉴스]
한편 이재용 삼성전자 회장은 미국 워싱턴DC로 출국했다. 이 회장은 주요 파트너사와 글로벌 비즈니스 협력 방안을 논의하고 신사업 기회를 모색할 예정인 것으로 알려졌다. 재계에서는 이 회장이 미국 상호관세 발효를 앞두고 관세 협상 측면 지원에 나설 것이라는 관측이 나왔다.
    """

    llm_test(test_article)  # LLM 테스트 실행

    end = time.time()
    print(f"Test completed in {end - start:.2f} seconds")

