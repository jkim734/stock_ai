from llm_caller import *
from crawling import crawl_naver_news_by_keyword
import time

def llm_test(article: str):
    """
    LLM 테스트 함수
    """
    
    # LLM 분류 테스트
    category = classify_llm(article)
    print(f"분류 결과: {category}")
    
    if category == "경제 기사":
        company_result = company_llm(article)
        
    elif category == "정책 기사":
        positives = policy_llm(article)
        
        # 정책 기사에서 긍정적인 업종 추출 후 각 업종 심층 분석 -> 각 호재 업종 마다 competitive_llm 호출
        for category in positives:
            article = crawl_naver_news_by_keyword(category['category'], page=1, sort=1)
            comp_result = competitive_llm(category['category'], category['reason'], article)
            companies = comp_result.get('companies', [])
            for company in companies:
                print(f"업종: {category['category']}, 기업: {company['company']}, 이유: {company['reason']}")
    else:
        print("Invalid article type for LLM classification.")

if __name__ == "__main__":
    start = time.time()
    # 테스트용 기사
    test_article = """
    
    """
    
    llm_test(test_article)  # LLM 테스트 실행
    
    end = time.time()
    print(f"Test completed in {end - start:.2f} seconds")
            