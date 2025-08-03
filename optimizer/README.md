# 포트폴리오 최적화 시스템

Modern Portfolio Theory (MPT)를 기반으로 한 포트폴리오 최적화 도구입니다. 기업 리스트를 입력하면 2년치 과거 데이터를 분석하여 최적의 투자 비율을 계산합니다.

## 주요 기능

- 📊 **MOPT 포트폴리오 최적화**: 샤프 비율을 최대화하는 최적 가중치 계산
- 📈 **2년치 과거 데이터 분석**: Yahoo Finance API를 통한 실시간 데이터 수집
- 💰 **투자 금액 배분**: 입력받은 투자금을 최적 비율로 분배
- 📊 **시각화**: 효율적 프론티어, 상관관계, 몬테카를로 시뮬레이션 차트
- 🎯 **다양한 입력 방식**: JSON 파일, 직접 입력, 대화형 모드 지원

## 설치 방법

```bash
# 필요한 패키지 설치
pip install -r requirements.txt
```

## 사용 방법

### 1. JSON 파일을 이용한 실행

```bash
python portfolio_runner.py --json sample_stocks.json --amount 10000000
```

JSON 파일 형식:
```json
{
  "description": "한국 대형주 포트폴리오",
  "stocks": [
    {"symbol": "005930", "name": "삼성전자"},
    {"symbol": "000660", "name": "SK하이닉스"},
    {"symbol": "035420", "name": "NAVER"}
  ]
}
```

### 2. 직접 주식 코드 입력

```bash
python portfolio_runner.py --stocks 005930,000660,035420,051910 --amount 10000000
```

### 3. 대화형 모드

```bash
python portfolio_runner.py --interactive
```

### 4. 샘플 JSON 파일 생성

```bash
python portfolio_runner.py --sample
```

## 출력 결과

### 콘솔 출력
- 각 기업별 투자 금액 및 비율
- 포트폴리오 예상 수익률, 변동성, 샤프 비율
- 최적화 진행 상황

### 시각화 파일 (PNG)
1. **효율적 프론티어**: 몬테카를로 시뮬레이션과 최적 포트폴리오 표시
2. **포트폴리오 구성**: 각 종목별 투자 비율 파이 차트
3. **상관관계 히트맵**: 종목 간 상관관계 분석
4. **가격 성과**: 정규화된 주가 변동 추이

## 코드 구조

```
optimizer/
├── classic_opt.py          # 메인 최적화 클래스
├── portfolio_runner.py     # 실행 스크립트
├── sample_stocks.json      # 샘플 데이터
├── requirements.txt        # 필요 패키지
└── README.md              # 사용 설명서
```

## 예시 실행

```bash
# 1천만원으로 한국 대형주 포트폴리오 최적화
python portfolio_runner.py --json sample_stocks.json --amount 10000000

# 출력 예시:
=== 포트폴리오 최적화 시작 ===
데이터 수집 중: ['005930.KS', '000660.KS', '035420.KS', ...]
데이터 수집 완료: (504, 8)
수익률 계산 완료
포트폴리오 최적화 완료
시각화 저장 완료: ./portfolio_analysis_20250803_161234.png

=== 최적화 결과 ===
예상 연간 수익률: 15.2%
예상 연간 변동성: 18.7%
샤프 비율: 0.813

총 투자 금액: 10,000,000원

=== 투자 배분 ===
005930: 3,420,000원 (34.2%)
000660: 2,180,000원 (21.8%)
035420: 1,890,000원 (18.9%)
068270: 1,320,000원 (13.2%)
051910: 1,190,000원 (11.9%)
```

## 주요 클래스 및 메서드

### PortfolioOptimizer 클래스

- `__init__(stock_list, investment_amount, period_years=2)`: 초기화
- `fetch_stock_data()`: 과거 주가 데이터 수집
- `calculate_returns()`: 수익률 및 공분산 매트릭스 계산
- `optimize_portfolio()`: 샤프 비율 최대화 최적화
- `monte_carlo_simulation()`: 몬테카를로 시뮬레이션
- `create_visualizations()`: 차트 생성
- `run_optimization()`: 전체 프로세스 실행

## 주의사항

- 한국 주식 코드는 6자리 숫자로 입력 (예: 005930)
- 최소 2개 이상의 종목이 필요합니다
- 과거 데이터가 충분하지 않은 종목은 자동으로 제외됩니다
- 네트워크 연결이 필요합니다 (Yahoo Finance API 사용)

## 의존성 패키지

- numpy: 수치 계산
- pandas: 데이터 처리
- matplotlib: 차트 생성
- seaborn: 고급 시각화
- yfinance: 주가 데이터 수집
- scipy: 최적화 알고리즘
