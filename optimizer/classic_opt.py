import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import yfinance as yf
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

class PortfolioOptimizer:
    def __init__(self, stock_list, investment_amount, period_years=2):
        """
        포트폴리오 최적화 클래스

        Args:
            stock_list: 기업 리스트 (JSON 형태 또는 리스트)
            investment_amount: 총 투자 금액
            period_years: 과거 데이터 기간 (년)
        """
        self.stock_list = self._parse_stock_list(stock_list)
        self.investment_amount = investment_amount
        self.period_years = period_years
        self.stock_data = None
        self.returns = None
        self.mean_returns = None
        self.cov_matrix = None
        self.optimal_weights = None

    def _parse_stock_list(self, stock_list):
        """기업 리스트를 파싱"""
        if isinstance(stock_list, str):
            try:
                data = json.loads(stock_list)
                if isinstance(data, dict) and 'stocks' in data:
                    # JSON에서 stocks 배열 추출
                    stocks = data['stocks']
                    return [stock.get('symbol', stock.get('code', '')) if isinstance(stock, dict) else str(stock) for stock in stocks]
                elif isinstance(data, list):
                    return [stock.get('symbol', stock.get('code', '')) if isinstance(stock, dict) else str(stock) for stock in data]
                else:
                    return list(data.values()) if isinstance(data, dict) else [str(data)]
            except json.JSONDecodeError:
                return [stock_list]
        elif isinstance(stock_list, dict):
            # 딕셔너리 형태의 입력 처리
            if 'stocks' in stock_list:
                stocks = stock_list['stocks']
                return [stock.get('symbol', stock.get('code', '')) if isinstance(stock, dict) else str(stock) for stock in stocks]
            else:
                return list(stock_list.values())
        elif isinstance(stock_list, list):
            return [stock.get('symbol', stock.get('code', '')) if isinstance(stock, dict) else str(stock) for stock in stock_list]
        else:
            return [str(stock_list)]

    def fetch_stock_data(self):
        """2년치 과거 종가 데이터 수집"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.period_years * 365)

        # 한국 주식 코드 처리 (.KS 추가)
        symbols = []
        for stock in self.stock_list:
            if isinstance(stock, dict):
                symbol = stock.get('symbol', stock.get('code', ''))
            else:
                symbol = str(stock)

            # 빈 문자열 제거
            if not symbol or symbol.strip() == '':
                continue

            # 한국 주식인 경우 .KS 추가
            if symbol.isdigit() and len(symbol) == 6:
                symbol += '.KS'
            symbols.append(symbol)

        if not symbols:
            print("유효한 주식 코드가 없습니다.")
            return False

        print(f"데이터 수집 중: {symbols}")

        try:
            # 개별 주식별로 데이터 수집하여 안정성 확보
            stock_prices = {}

            for symbol in symbols:
                try:
                    print(f"  - {symbol} 데이터 수집 중...")
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(start=start_date, end=end_date)

                    if not hist.empty:
                        # Close 가격 사용 (Adj Close가 없을 수도 있음)
                        if 'Close' in hist.columns:
                            stock_prices[symbol] = hist['Close']
                        elif len(hist.columns) > 0:
                            stock_prices[symbol] = hist.iloc[:, 0]  # 첫 번째 컬럼 사용
                        print(f"    ✓ {symbol}: {len(hist)} 개 데이터 수집 완료")
                    else:
                        print(f"    ✗ {symbol}: 데이터 없음")

                except Exception as e:
                    print(f"    ✗ {symbol}: 수집 실패 - {e}")
                    continue

            if not stock_prices:
                raise ValueError("수집된 주식 데이터가 없습니다.")

            # DataFrame으로 변환
            self.stock_data = pd.DataFrame(stock_prices)

            # 결측치 처리 - 모든 주식에 대해 데이터가 있는 날짜만 사용
            self.stock_data = self.stock_data.dropna()

            if self.stock_data.empty:
                raise ValueError("결측치 제거 후 데이터가 없습니다.")

            print(f"\n데이터 수집 완료!")
            print(f"  - 최종 데이터 형태: {self.stock_data.shape}")
            print(f"  - 수집된 종목: {list(self.stock_data.columns)}")
            print(f"  - 데이터 기간: {self.stock_data.index[0].date()} ~ {self.stock_data.index[-1].date()}")
            print(f"  - 총 거래일: {len(self.stock_data)} 일")

            return True

        except Exception as e:
            print(f"데이터 수집 실패: {e}")
            import traceback
            print(f"상세 오류:\n{traceback.format_exc()}")
            return False

    def calculate_returns(self):
        """일일 수익률 계산"""
        if self.stock_data is None:
            raise ValueError("먼저 데이터를 수집해주세요.")

        self.returns = self.stock_data.pct_change().dropna()
        self.mean_returns = self.returns.mean() * 252  # 연간 수익률
        self.cov_matrix = self.returns.cov() * 252  # 연간 공분산

        print("수익률 계산 완료")
        print(f"연간 평균 수익률:\n{self.mean_returns}")

    def portfolio_stats(self, weights):
        """포트폴리오 통계 계산"""
        portfolio_return = np.sum(weights * self.mean_returns)
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
        sharpe_ratio = portfolio_return / portfolio_volatility
        return portfolio_return, portfolio_volatility, sharpe_ratio

    def negative_sharpe(self, weights):
        """샤프 비율의 음수 (최적화를 위해)"""
        return -self.portfolio_stats(weights)[2]

    def optimize_portfolio(self):
        """포트폴리오 최적화 (최대 샤프 ��율)"""
        if self.returns is None:
            raise ValueError("먼저 수익률을 계산해주세요.")

        num_assets = len(self.mean_returns)

        # 제약 조건
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(num_assets))

        # 초기 추정값 (균등 분배)
        initial_guess = num_assets * [1. / num_assets]

        # 최적화 실행
        result = minimize(
            self.negative_sharpe,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if result.success:
            self.optimal_weights = result.x
            print("포트폴리오 최적화 완료")
            return True
        else:
            print("최적화 실패")
            return False

    def get_stock_info(self, symbol):
        """주식 코드에서 회사명 추출"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            name = info.get('longName', info.get('shortName', symbol.replace('.KS', '')))
            return name
        except:
            # 한국 주요 기업 매핑
            korean_stocks = {
                '005930': '삼성전자',
                '000660': 'SK하이닉스',
                '035420': '네이버',
                '051910': 'LG화학',
                '068270': '셀트리온',
                '005380': '현대차',
                '006400': '삼성SDI',
                '035720': '카카오',
                '207940': '삼성바이오로직스',
                '006400': '삼성SDI',
                '028260': '삼성물산',
                '000270': '기아',
                '012330': '현대모비스',
                '066570': 'LG전자',
                '003550': 'LG',
                '096770': 'SK이노베이션',
                '034730': 'SK',
                '018260': '삼성에스디에스',
                '003670': '포스코홀딩스',
                '017670': 'SK텔레콤',
                '030200': 'KT',
                '033780': 'KT&G',
                '009150': '삼성전기',
                '010950': 'S-Oil',
                '011200': 'HMM',
                '015760': '한국전력',
                '090430': '아모레퍼시픽',
                '001570': '금양',
                '002380': 'KCC',
                '086790': '하나금융지주',
                '055550': '신한지주',
                '105560': 'KB금융',
                '316140': '우리금융지주'
            }
            
            base_symbol = symbol.replace('.KS', '')
            return korean_stocks.get(base_symbol, base_symbol)

    def calculate_allocation(self):
        """각 기업별 투자 금액 계산 (회사명 포함)"""
        if self.optimal_weights is None:
            raise ValueError("먼저 포트폴리오를 최적화해주세요.")

        allocations = []
        symbols = list(self.stock_data.columns)

        for i, weight in enumerate(self.optimal_weights):
            symbol = symbols[i].replace('.KS', '')
            name = self.get_stock_info(symbols[i])
            amount = self.investment_amount * weight
            allocations.append({
                'symbol': symbol,
                'name': name,
                'weight': weight,
                'amount': int(amount),
                'percentage': weight * 100
            })

        # 가중치 순으로 정렬
        allocations.sort(key=lambda x: x['weight'], reverse=True)
        return allocations

    def monte_carlo_simulation(self, num_simulations=10000):
        """몬테카를로 시뮬레이션"""
        if self.returns is None:
            raise ValueError("먼저 수익률을 계산해주세요.")

        num_assets = len(self.mean_returns)
        results = np.zeros((3, num_simulations))

        for i in range(num_simulations):
            # 랜덤 가중치 생성
            weights = np.random.random(num_assets)
            weights /= np.sum(weights)

            # 포트폴리오 성과 계산
            portfolio_return, portfolio_volatility, sharpe_ratio = self.portfolio_stats(weights)

            results[0, i] = portfolio_return
            results[1, i] = portfolio_volatility
            results[2, i] = sharpe_ratio

        return results

    def create_visualizations(self, output_dir='./'):
        """시각화 생성"""
        if self.optimal_weights is None:
            raise ValueError("먼저 포트폴리오를 최적화해주세요.")

        # 1. 효율적 프론티어와 몬테카를로 시뮬레이션
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # 몬테카를로 시뮬레이션
        mc_results = self.monte_carlo_simulation()

        # 효율적 프론티어 점 그래프
        scatter = ax1.scatter(mc_results[1], mc_results[0], c=mc_results[2],
                            cmap='viridis', alpha=0.5, s=1)

        # 최적 포트폴리오 표시
        opt_return, opt_volatility, opt_sharpe = self.portfolio_stats(self.optimal_weights)
        ax1.scatter(opt_volatility, opt_return, color='red', s=100, marker='*',
                   label=f'Optimal Portfolio (Sharpe: {opt_sharpe:.3f})')

        ax1.set_xlabel('Volatility (Risk)')
        ax1.set_ylabel('Expected Return')
        ax1.set_title('Efficient Frontier with Monte Carlo Simulation')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax1, label='Sharpe Ratio')

        # 2. 포트폴리오 구성 비율 (파이 차트)
        symbols = [col.replace('.KS', '') for col in self.stock_data.columns]
        significant_weights = [(symbols[i], weight) for i, weight in enumerate(self.optimal_weights) if weight > 0.01]

        if len(significant_weights) > 0:
            labels, weights = zip(*significant_weights)
            ax2.pie(weights, labels=labels, autopct='%1.1f%%', startangle=90)
            ax2.set_title('Optimal Portfolio Allocation')

        # 3. 상관관계 히트맵
        correlation_matrix = self.returns.corr()
        correlation_matrix.columns = [col.replace('.KS', '') for col in correlation_matrix.columns]
        correlation_matrix.index = [idx.replace('.KS', '') for idx in correlation_matrix.index]

        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                   square=True, ax=ax3, fmt='.2f')
        ax3.set_title('Stock Correlation Matrix')

        # 4. 개별 주식 가격 변화
        normalized_prices = self.stock_data / self.stock_data.iloc[0]
        for col in normalized_prices.columns:
            ax4.plot(normalized_prices.index, normalized_prices[col],
                    label=col.replace('.KS', ''), alpha=0.8)

        ax4.set_xlabel('Date')
        ax4.set_ylabel('Normalized Price')
        ax4.set_title('Stock Price Performance (Normalized)')
        ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        # 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/portfolio_analysis_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"시각화 저장 완료: {filename}")
        return filename

    def run_optimization(self):
        """전체 최적화 프로세스 실행"""
        print("=== 포트폴리오 최적화 시작 ===")

        try:
            # 1. 데이터 수집
            if not self.fetch_stock_data():
                print("데이터 수집 실패")
                return None

            # 2. 수익률 계산
            self.calculate_returns()

            # 3. 포트폴리오 최적화
            if not self.optimize_portfolio():
                print("포트폴리오 최적화 실패")
                return None

            # 4. 투자 금액 계산
            allocations = self.calculate_allocation()

            # 5. 시각화 생성
            chart_file = self.create_visualizations()

            # 6. 결과 출력
            print("\n=== 최적화 결과 ===")
            opt_return, opt_volatility, opt_sharpe = self.portfolio_stats(self.optimal_weights)
            print(f"예상 연간 수익률: {opt_return:.2%}")
            print(f"예상 연간 변동성: {opt_volatility:.2%}")
            print(f"샤프 비율: {opt_sharpe:.3f}")

            print(f"\n총 투자 금액: {self.investment_amount:,}원")
            print("\n=== 투자 배분 ===")
            for allocation in allocations:
                if allocation['weight'] > 0.001:  # 0.1% 이상만 표시
                    print(f"{allocation['symbol']}: {allocation['amount']:,}원 ({allocation['percentage']:.1f}%)")

            # GUI에서 기대하는 형식으로 결과 반환
            result = {
                'method': '클래식 최적화 (Mean-Variance)',
                'allocations': allocations,
                'performance': {
                    'expected_return': opt_return,
                    'volatility': opt_volatility,
                    'sharpe_ratio': opt_sharpe
                },
                'chart_file': chart_file
            }

            print("최적화 완료 - 결과 반환")
            return result

        except Exception as e:
            print(f"최적화 중 오류 발생: {e}")
            import traceback
            print(f"상세 오류:\n{traceback.format_exc()}")
            return None


def optimize_portfolio_from_json(json_file_path, investment_amount):
    """JSON 파일에서 기업 리스트를 읽어 포트폴리오 최적화 실행"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            stock_data = json.load(f)

        optimizer = PortfolioOptimizer(stock_data, investment_amount)
        return optimizer.run_optimization()

    except Exception as e:
        print(f"에러 발생: {e}")
        return None


if __name__ == "__main__":
    # 테스트용 예제
    test_stocks = ["005930", "000660", "035420", "051910", "068270"]  # 삼성전자, SK하��닉스, 네��버, LG화학, 셀트리온
    investment_amount = 10000000  # 1천만원

    optimizer = PortfolioOptimizer(test_stocks, investment_amount)
    result = optimizer.run_optimization()

    if result:
        print("\n포트폴리오 최적화 완료!")
        print(f"차트 파일: {result['chart_file']}")
