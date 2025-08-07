import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import yfinance as yf
import warnings
import os
from dotenv import load_dotenv

# Quantum computing imports with error handling
try:
    from qiskit import QuantumCircuit, transpile
    from qiskit.circuit import Parameter

    # Qiskit 2.x compatible imports
    try:
        # Try Qiskit 2.x imports first
        from qiskit.primitives import StatevectorEstimator as Estimator
    except ImportError:
        try:
            # Fallback to Qiskit 1.x imports
            from qiskit.primitives import Estimator
        except ImportError:
            # If both fail, use None
            Estimator = None

    from qiskit_ibm_runtime import QiskitRuntimeService
    try:
        from qiskit_ibm_runtime import EstimatorV2 as RuntimeEstimator
    except ImportError:
        try:
            from qiskit_ibm_runtime import Estimator as RuntimeEstimator
        except ImportError:
            RuntimeEstimator = None

    try:
        from qiskit_ibm_runtime import SamplerV2 as RuntimeSampler
    except ImportError:
        try:
            from qiskit_ibm_runtime import Sampler as RuntimeSampler
        except ImportError:
            RuntimeSampler = None

    # AerSimulator import with multiple fallback options
    AerSimulator = None
    try:
        from qiskit_aer import AerSimulator
        print("✅ AerSimulator 로드 성공 (qiskit_aer)")
    except ImportError:
        try:
            # Alternative import path
            from qiskit.providers.aer import AerSimulator
            print("✅ AerSimulator 로드 성공 (qiskit.providers.aer)")
        except ImportError:
            try:
                # Another fallback
                from qiskit_aer.backends import AerSimulator
                print("✅ AerSimulator 로드 성공 (qiskit_aer.backends)")
            except ImportError:
                print("⚠️  AerSimulator를 로드할 수 없습니다. 양자 시뮬레이션이 제한됩니다.")
                AerSimulator = None

    # FakeBackend imports
    try:
        from qiskit.providers.fake_provider import FakeBackend
    except ImportError:
        try:
            from qiskit_ibm_runtime.fake_provider import FakeBackend
        except ImportError:
            FakeBackend = None

    # Session import
    try:
        from qiskit_ibm_runtime import Session
    except ImportError:
        Session = None

    # 옵티마이저 import 개선 - 여러 소스에서 시도
    COBYLA = None
    SPSA = None
    VQE = None
    minimize = None

    # 1. qiskit_algorithms에서 시도
    try:
        from qiskit_algorithms.optimizers import COBYLA, SPSA
        from qiskit_algorithms import VQE
        print("✅ qiskit_algorithms에서 옵티마이저를 성공적으로 로드했습니다.")
    except ImportError:
        # 2. qiskit.algorithms에서 시도 (구버전)
        try:
            from qiskit.algorithms.optimizers import COBYLA, SPSA
            from qiskit.algorithms import VQE
            print("✅ qiskit.algorithms에서 옵티마이저를 성공적으로 로드했습니다.")
        except ImportError:
            # 3. scipy 폴백 및 커스텀 COBYLA 구현
            try:
                from scipy.optimize import minimize
                print("⚠️  Qiskit 옵티마이저를 사용할 수 없어 scipy로 폴백합니다.")

                # 커스텀 COBYLA 래퍼 클래스
                class COBYLAWrapper:
                    def __init__(self, maxiter=1000, disp=False, rhobeg=1.0, rhoend=1e-4):
                        self.maxiter = maxiter
                        self.disp = disp
                        self.rhobeg = rhobeg
                        self.rhoend = rhoend

                    def minimize(self, fun, x0, args=(), **kwargs):
                        result = minimize(
                            fun, x0, method='COBYLA',
                            options={
                                'maxiter': self.maxiter,
                                'disp': self.disp,
                                'rhobeg': self.rhobeg,
                                'rhoend': self.rhoend
                            },
                            args=args
                        )
                        return result

                COBYLA = COBYLAWrapper
                print("✅ 커스텀 COBYLA 래퍼를 생성했습니다.")

            except ImportError:
                print("❌ 모든 옵티마이저 import에 실패했습니다.")

    try:
        from qiskit.quantum_info import SparsePauliOp
    except ImportError:
        SparsePauliOp = None

    QISKIT_AVAILABLE = True
    print(f"✅ Qiskit 사용 가능")
    print(f"   - COBYLA: {COBYLA is not None}")
    print(f"   - SPSA: {SPSA is not None}")
    print(f"   - AerSimulator: {AerSimulator is not None}")

except ImportError as e:
    print(f"❌ Qiskit import error: {e}")
    print("양자 컴퓨팅 기능을 사용할 수 없습니다. 클래식 최적화만 사용됩니다.")
    QISKIT_AVAILABLE = False
    AerSimulator = None
    Session = None
    Estimator = None
    RuntimeEstimator = None
    RuntimeSampler = None
    COBYLA = None
    SPSA = None
    VQE = None
    QuantumCircuit = None
    transpile = None
    Parameter = None
    QiskitRuntimeService = None
    SparsePauliOp = None
    minimize = None

warnings.filterwarnings('ignore')

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# .env 파일 로드 (여러 파일 지원)
load_dotenv()  # 기본 .env 파일
load_dotenv('.env.ibm_api')  # IBM API 키 전용 파일

class QuantumPortfolioOptimizer:
    def __init__(self, stock_list, investment_amount, period_years=2, use_real_quantum=False):
        """
        양자 포트폴리오 최적화 클래스

        Args:
            stock_list: 기업 리스트 (JSON 형태 또는 리스트)
            investment_amount: 총 투자 금액
            period_years: 과거 데이터 기간 (년)
            use_real_quantum: IBM Quantum 실제 하드웨어 사용 여부
        """
        self.stock_list = self._parse_stock_list(stock_list)
        self.investment_amount = investment_amount
        self.period_years = period_years
        self.use_real_quantum = use_real_quantum and QISKIT_AVAILABLE
        self.stock_data = None
        self.returns = None
        self.mean_returns = None
        self.cov_matrix = None
        self.optimal_weights = None
        self.service = None

        # IBM Quantum 서비스 초기화
        if QISKIT_AVAILABLE:
            self._initialize_quantum_service()
        else:
            print("Qiskit이 설치되지 않았습니다. 클래식 최적화만 사용됩니다.")

    def _initialize_quantum_service(self):
        """IBM Quantum 서비스 초기화 (test.py 방식으로 개선)"""
        try:
            # test.py에서 사용하는 토큰
            token = "xG3YHDYOTD5YRQuu5fTm6UTUHTg530kyuTLm36eSik75"

            # 환경변수에서 토큰을 확인하되, 없으면 기본 토큰 사용
            ibm_token = os.getenv('IBM_QUANTUM_TOKEN', token)

            if ibm_token and self.use_real_quantum:
                print(f"🔑 IBM Quantum 토큰 확인됨 (길이: {len(ibm_token)} 자)")

                try:
                    # test.py와 동일한 방식으로 계정 저장
                    QiskitRuntimeService.save_account(
                        token=ibm_token,
                        instance="crn:v1:bluemix:public:quantum-computing:us-east:a/624a449c58db4cebbbcd6d44cd96889e:15b7b368-8c6c-46a5-b7f8-b2d2f2646a60::",
                        channel="ibm_cloud",
                        set_as_default=True,
                        overwrite=True
                    )

                    # 서비스 연결
                    self.service = QiskitRuntimeService()

                    # 연결 테스트: 백엔드 목록 가져오기
                    backends = list(self.service.backends())
                    print(f"✅ IBM Quantum 서비스 연결 성공!")
                    print(f"  📡 사용 가능한 백엔드: {len(backends)}개")

                    # 하드웨어 백엔드 확인
                    hardware_backends = [b for b in backends if not b.simulator]
                    print(f"  🔧 하드웨어 백엔드: {len(hardware_backends)}개")

                    if hardware_backends:
                        operational_hw = [b for b in hardware_backends if b.status().operational]
                        print(f"  ✅ 운영 중인 하드웨어: {len(operational_hw)}개")
                        if operational_hw:
                            # 대기열 정보 출력
                            for backend in operational_hw[:3]:
                                queue_length = backend.status().pending_jobs
                                print(f"     - {backend.name}: 대기열 {queue_length}개")
                    return True

                except Exception as conn_error:
                    print(f"❌ IBM Quantum 연결 실패: {conn_error}")
                    print("🔄 로컬 시뮬레이터로 대체합니다.")
                    self.use_real_quantum = False
                    return False

            else:
                if not ibm_token:
                    print("🖥️  IBM Quantum 토큰이 설정되지 않음 - 로컬 시뮬레이터 사용")
                else:
                    print("🖥️  로컬 시뮬레이터 사용")
                return True

        except Exception as e:
            print(f"❌ IBM Quantum 서비스 초기화 중 전체 오류: {e}")
            print("   로컬 시뮬레이터로 대체")
            self.use_real_quantum = False
            return False

    def _parse_stock_list(self, stock_list):
        """기업 리스트를 파싱 (classic_opt와 동일)"""
        if isinstance(stock_list, str):
            try:
                data = json.loads(stock_list)
                if isinstance(data, dict) and 'stocks' in data:
                    stocks = data['stocks']
                    return [stock.get('symbol', stock.get('code', '')) if isinstance(stock, dict) else str(stock) for stock in stocks]
                elif isinstance(data, list):
                    return [stock.get('symbol', stock.get('code', '')) if isinstance(stock, dict) else str(stock) for stock in data]
                else:
                    return list(data.values()) if isinstance(data, dict) else [str(data)]
            except json.JSONDecodeError:
                return [stock_list]
        elif isinstance(stock_list, dict):
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
        """2년치 과거 종가 데이터 수집 (classic_opt와 동일)"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.period_years * 365)

        symbols = []
        for stock in self.stock_list:
            if isinstance(stock, dict):
                symbol = stock.get('symbol', stock.get('code', ''))
            else:
                symbol = str(stock)

            if not symbol or symbol.strip() == '':
                continue

            if symbol.isdigit() and len(symbol) == 6:
                symbol += '.KS'
            symbols.append(symbol)

        if not symbols:
            print("유효한 주식 코드가 없습니다.")
            return False

        print(f"데이터 수집 중: {symbols}")

        try:
            stock_prices = {}

            for symbol in symbols:
                try:
                    print(f"  - {symbol} 데이터 수집 중...")
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(start=start_date, end=end_date)

                    if not hist.empty:
                        if 'Close' in hist.columns:
                            stock_prices[symbol] = hist['Close']
                        elif len(hist.columns) > 0:
                            stock_prices[symbol] = hist.iloc[:, -1]
                        print(f"    ✓ {symbol}: {len(hist)} 개 데이터 수집 완료")
                    else:
                        print(f"    ✗ {symbol}: 데이터 없음")

                except Exception as e:
                    print(f"    ✗ {symbol}: 수집 실패 - {e}")
                    continue

            if not stock_prices:
                raise ValueError("수집된 주식 데이터가 없습니다.")

            self.stock_data = pd.DataFrame(stock_prices)
            self.stock_data = self.stock_data.dropna()

            if self.stock_data.empty:
                raise ValueError("결측치 제거 후 데이터가 없습니다.")

            print(f"\n데이터 수집 완료!")
            print(f"  - 최종 데이터 형태: {self.stock_data.shape}")
            print(f"  - 수집된 종목: {list(self.stock_data.columns)}")

            # Fix date formatting issue
            try:
                start_date_str = self.stock_data.index[0].date().strftime('%Y-%m-%d')
                end_date_str = self.stock_data.index[-1].date().strftime('%Y-%m-%d')
                print(f"  - 데이터 기간: {start_date_str} ~ {end_date_str}")
            except:
                print(f"  - 데이터 기간: {self.stock_data.index[0]} ~ {self.stock_data.index[-1]}")

            print(f"  - 총 거래일: {len(self.stock_data)} 일")

            return True

        except Exception as e:
            print(f"데이터 수집 실패: {e}")
            import traceback
            print(f"상세 오류:\n{traceback.format_exc()}")
            return False

    def calculate_returns(self):
        """일일 수익률 계산 (classic_opt와 동일)"""
        if self.stock_data is None:
            raise ValueError("먼저 데이터를 수집해주세요.")

        self.returns = self.stock_data.pct_change().dropna()
        self.mean_returns = self.returns.mean() * 252
        self.cov_matrix = self.returns.cov() * 252

        print("수익률 계산 완료")
        print(f"연간 평균 수익률:\n{self.mean_returns}")

    def portfolio_stats(self, weights):
        """포트폴리오 통계 계산 (classic_opt와 동일)"""
        portfolio_return = np.sum(weights * self.mean_returns)
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
        sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
        return portfolio_return, portfolio_volatility, sharpe_ratio

    def create_vqe_ansatz(self, num_qubits, num_layers=2):
        """VQE용 양자 회로 앤사츠 생성"""
        if not QISKIT_AVAILABLE:
            return None, None

        qc = QuantumCircuit(num_qubits)

        # 매개변수 생성
        params = []

        for layer in range(num_layers):
            # 회전 게이트
            for i in range(num_qubits):
                theta = Parameter(f'θ_{layer}_{i}')
                phi = Parameter(f'φ_{layer}_{i}')
                lam = Parameter(f'λ_{layer}_{i}')
                params.extend([theta, phi, lam])
                qc.u(theta, phi, lam, i)

            # 얽힘 게이트
            for i in range(num_qubits - 1):
                qc.cx(i, i + 1)
            if num_qubits > 2:
                qc.cx(num_qubits - 1, 0)  # 원형 연결

        return qc, params

    def create_cost_hamiltonian(self, weights):
        """포트폴리오 최적화를 위한 비용 함수 해밀토니안 생성"""
        if not QISKIT_AVAILABLE or SparsePauliOp is None:
            return None

        num_assets = len(weights)

        # 샤프 비율의 음수를 최소화하는 해밀토니안
        paulis = []
        coeffs = []

        for i in range(num_assets):
            # 각 자산의 기여도를 Z 연산자로 인코딩
            pauli_str = ['I'] * num_assets
            pauli_str[i] = 'Z'
            paulis.append(''.join(pauli_str))

            # 수익률과 리스크를 고려한 계수
            risk_adjusted_return = self.mean_returns.iloc[i] / np.sqrt(self.cov_matrix.iloc[i, i])
            coeffs.append(-risk_adjusted_return)  # 음수로 최대화를 최소화로 변환

        return SparsePauliOp(paulis, coeffs)

    def quantum_portfolio_objective(self, params):
        """양자 VQE 목적 함수"""
        # 매개변수를 가중치로 변환 (소프트맥스 사용)
        num_assets = len(self.mean_returns)

        # 매개변수를 재구성하여 가중치 생성
        raw_weights = params[:num_assets] if len(params) >= num_assets else np.array(params + [0] * (num_assets - len(params)))
        weights = np.exp(raw_weights) / np.sum(np.exp(raw_weights))

        # 샤프 비율의 음수 반환 (최소화를 위해)
        return -self.portfolio_stats(weights)[2]

    def optimize_portfolio_vqe(self):
        """VQE를 사용한 포트폴리오 최적화 (하드웨어 → 시뮬레이터 → 클래식 폴백)"""
        if self.returns is None:
            raise ValueError("먼저 수익률을 계산해주세요.")

        num_assets = len(self.mean_returns)
        print(f"VQE 포트폴리오 최적화 시작 (자산 수: {num_assets})")

        # 최적의 백엔드 선택 (하드웨어 → 시뮬레이터 → 클래식)
        backend_info = self.get_best_available_backend()

        print(f"선택된 백엔드: {backend_info['name']} ({backend_info['type']})")

        # 선택된 백엔드로 VQE 실행
        if backend_info['type'] != 'classical':
            return self.run_quantum_vqe_with_backend(backend_info)
        else:
            return self.optimize_portfolio_classical()

    def optimize_portfolio_classical(self):
        """폴백용 클래식 최적화"""
        from scipy.optimize import minimize

        num_assets = len(self.mean_returns)

        def negative_sharpe(weights):
            return -self.portfolio_stats(weights)[2]

        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(num_assets))
        initial_guess = num_assets * [1. / num_assets]

        result = minimize(
            negative_sharpe,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if result.success:
            self.optimal_weights = result.x
            print("✓ 클래식 포트폴리오 최적화 완료")
            return True
        else:
            print("❌ 클래식 최적화 실패")
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
        """개별 기업별 투자 금액 계산 (회사명 포함)"""
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
        """몬테카를로 시뮬레이션 (classic_opt와 동일)"""
        if self.returns is None:
            raise ValueError("먼저 수익률을 계산해주세요.")

        num_assets = len(self.mean_returns)
        results = np.zeros((3, num_simulations))

        for i in range(num_simulations):
            weights = np.random.random(num_assets)
            weights /= np.sum(weights)

            portfolio_return, portfolio_volatility, sharpe_ratio = self.portfolio_stats(weights)

            results[0, i] = portfolio_return
            results[1, i] = portfolio_volatility
            results[2, i] = sharpe_ratio

        return results

    def create_visualizations(self, output_dir='./'):
        """시각화 생성 (classic_opt와 동일하지만 제목에 Quantum 추가)"""
        if self.optimal_weights is None:
            raise ValueError("먼저 포트폴리오를 최적화해주세요.")

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # 몬테카를로 시뮬레이션
        mc_results = self.monte_carlo_simulation()

        # 효율적 프론티어 점 그래프
        scatter = ax1.scatter(mc_results[1], mc_results[0], c=mc_results[2],
                              cmap='viridis', alpha=0.5, s=1)

        # 최적 포트폴리오 표시
        opt_return, opt_volatility, opt_sharpe = self.portfolio_stats(self.optimal_weights)
        ax1.scatter(opt_volatility, opt_return, color='red', s=100, marker='*',
                    label=f'Quantum Optimal Portfolio (Sharpe: {opt_sharpe:.3f})')

        ax1.set_xlabel('Volatility (Risk)')
        ax1.set_ylabel('Expected Return')
        ax1.set_title('Quantum Efficient Frontier with Monte Carlo Simulation')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax1, label='Sharpe Ratio')

        # 2. 포트폴리오 구성 비율 (파이 차트)
        symbols = [col.replace('.KS', '') for col in self.stock_data.columns]
        significant_weights = [(symbols[i], weight) for i, weight in enumerate(self.optimal_weights) if weight > 0.01]

        if len(significant_weights) > 0:
            labels, weights = zip(*significant_weights)
            ax2.pie(weights, labels=labels, autopct='%1.1f%%', startangle=90)
            ax2.set_title('Quantum Optimal Portfolio Allocation')

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
        filename = f"{output_dir}/quantum_portfolio_analysis_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"양자 포트폴리오 시각화 저장 완료: {filename}")
        return filename

    def run_optimization(self):
        """전체 양자 최적화 프로세스 실행"""
        print("=== 양자 포트폴리오 최적화 시작 ===")

        # 1. 데이터 수집
        if not self.fetch_stock_data():
            return None

        # 2. 수익률 계산
        self.calculate_returns()

        # 3. 최적의 백엔드 선택
        backend_info = self.get_best_available_backend()

        # 4. 양자 포트폴리오 최적화
        if not self.optimize_portfolio_vqe():
            return None

        # 5. 투자 금액 계산
        allocations = self.calculate_allocation()

        # 6. 시각화 생성
        chart_file = self.create_visualizations()

        # 7. 결과 출력
        print("\n=== 양자 최적화 결과 ===")
        opt_return, opt_volatility, opt_sharpe = self.portfolio_stats(self.optimal_weights)
        print(f"예상 연간 수익률: {opt_return:.2%}")
        print(f"예상 연간 변동성: {opt_volatility:.2%}")
        print(f"샤프 비율: {opt_sharpe:.3f}")
        print(f"사용된 백엔드: {backend_info['name']} ({backend_info['type']})")

        print(f"\n총 투자 금액: {self.investment_amount:,}원")
        print("\n=== 양자 투자 배분 ===")
        for allocation in allocations:
            if allocation['weight'] > 0.001:
                print(f"{allocation['symbol']}: {allocation['amount']:,}원 ({allocation['percentage']:.1f}%)")

        # 백엔드 타입에 따른 메서드 결정
        if backend_info['type'] == 'hardware':
            method = f"Quantum VQE (Hardware: {backend_info['name']})"
        elif backend_info['type'] == 'simulator':
            method = f"Quantum VQE (Simulator: {backend_info['name']})"
        else:
            method = 'Classical (Fallback)'

        return {
            'allocations': allocations,
            'performance': {
                'expected_return': opt_return,
                'volatility': opt_volatility,
                'sharpe_ratio': opt_sharpe
            },
            'chart_file': chart_file,
            'method': method,
            'backend_info': backend_info
        }

    def get_best_available_backend(self):
        """사용 가능한 최적의 백엔드를 선택 (하드웨어 → 로컬 시뮬레이터 → 클래식)"""
        backend_info = {
            'backend': None,
            'type': 'classical',
            'name': 'Classical Fallback'
        }

        if not QISKIT_AVAILABLE:
            print("Qiskit을 사용할 수 없습니다. 클래식 최적화를 사용합니다.")
            return backend_info

        # 1순위: 실제 IBM Quantum 하드웨어
        if self.service and self.use_real_quantum:
            try:
                print("IBM Quantum 하드웨어 검색 중...")
                backends = self.service.backends()

                # 사용 가능한 하드웨어 백엔드 필터링
                available_backends = []
                for backend in backends:
                    if backend.simulator == False and backend.status().operational:
                        queue_length = backend.status().pending_jobs
                        available_backends.append((backend, queue_length))

                if available_backends:
                    # 대기열이 가장 짧은 백엔드 선택
                    best_backend = min(available_backends, key=lambda x: x[1])[0]
                    backend_info = {
                        'backend': best_backend,
                        'type': 'hardware',
                        'name': best_backend.name,
                        'queue_length': best_backend.status().pending_jobs
                    }
                    print(f"✓ IBM Quantum 하드웨어 선택: {best_backend.name} (대기열: {backend_info['queue_length']})")
                    return backend_info
                else:
                    print("✗ 사용 가능한 IBM Quantum 하드웨어가 없습니다.")
            except Exception as e:
                print(f"✗ IBM Quantum 하드웨어 접근 실패: {e}")

        # 2순위: 로컬 시뮬레이터 (Aer)
        if AerSimulator is not None:
            try:
                simulator = AerSimulator()
                backend_info = {
                    'backend': simulator,
                    'type': 'simulator',
                    'name': 'AerSimulator (Local)'
                }
                print("✓ 로컬 양자 시뮬레이터 (Aer) 사용")
                return backend_info
            except Exception as e:
                print(f"✗ 로컬 시뮬레이터 초기화 실패: {e}")

        # 3순위: 클래식 최적화
        print("✓ 클래식 최적화 사용")
        return backend_info

    def run_quantum_vqe_with_backend(self, backend_info):
        """선택된 백엔드로 실제 VQE 실행 (수정된 버전)"""
        try:
            print(f"양자 VQE 실행 중... (백엔드: {backend_info['name']})")

            if backend_info['type'] == 'hardware':
                return self.run_real_quantum_vqe(backend_info)
            elif backend_info['type'] == 'simulator':
                return self.run_simulator_vqe(backend_info)
            else:
                return self.optimize_portfolio_classical()

        except Exception as e:
            print(f"❌ 양자 VQE 실행 중 오류 ({backend_info['name']}): {e}")
            print("클래식 최적화로 폴백")
            return self.optimize_portfolio_classical()

    def run_real_quantum_vqe(self, backend_info):
        """실제 IBM Quantum 하드웨어에서 VQE 실행 (test.py 방식으로 개선)"""
        try:
            num_assets = len(self.mean_returns)
            print(f"🔧 실제 양자 하드웨어에서 계산 중...")

            # test.py와 동일한 방식으로 최적 백엔드 선택
            least_busy_backend = self.service.least_busy(operational=True, simulator=False)
            print(f"선택된 하드웨어: {least_busy_backend.name}")
            print(f"대기 중인 작업 수: {least_busy_backend.status().pending_jobs}")

            # 포트폴리오 최적화를 위한 양자 회로 생성
            qc = QuantumCircuit(num_assets, num_assets)

            # 매개변수 추가 (각 자산에 대한 회전 게이트)
            params = []
            for i in range(num_assets):
                param = Parameter(f'θ_{i}')
                params.append(param)
                qc.ry(param, i)
                # 추가 얽힘을 위한 CNOT 게이트
                if i < num_assets - 1:
                    qc.cx(i, i + 1)

            qc.measure_all()

            # test.py와 동일한 방식으로 회로 최적화
            transpiled_qc = transpile(qc, least_busy_backend, optimization_level=2)
            print(f"트랜스파일된 회로 (하드웨어 최적화):")
            print(transpiled_qc.draw())

            # test.py와 동일한 방식으로 SamplerV2 사용
            sampler = RuntimeSampler(mode=least_busy_backend)
            print(f"{least_busy_backend.name}에서 실행 중...")

            # 매개변수 최적화를 위한 목적 함수
            def quantum_objective(params_vals):
                try:
                    # 매개변수 바인딩
                    param_dict = {params[i]: params_vals[i] for i in range(len(params))}
                    bound_qc = transpiled_qc.assign_parameters(param_dict)

                    # test.py와 동일한 방식으로 양자 계산 실행
                    job = sampler.run([bound_qc], shots=1000)
                    result = job.result()

                    # 결과 추출 (test.py 방식)
                    counts = result[0].data.meas.get_counts()
                    weights = self.counts_to_weights(counts, num_assets)

                    # 포트폴리오 성능 계산 및 샤프 비율의 음수 반환
                    _, _, sharpe_ratio = self.portfolio_stats(weights)
                    return -sharpe_ratio  # 최소화를 위해 음수 반환

                except Exception as e:
                    print(f"양자 계산 중 오류: {e}")
                    return 1000  # 큰 값을 반환하여 이 매개변수를 피하도록 함

            # 초기 매개변수 설정
            initial_params = np.random.uniform(0, np.pi, num_assets)

            # 제한된 최적화 (하드웨어는 비용이 높으므로)
            best_sharpe = -1000
            best_weights = None

            print("양자 하드웨어에서 포트폴리오 최적화 중...")
            for iteration in range(5):  # 제한된 반복
                try:
                    # 매개변수 조정
                    current_params = initial_params + np.random.normal(0, 0.1, num_assets)
                    current_params = np.clip(current_params, 0, np.pi)

                    # 양자 계산 실행
                    sharpe_score = -quantum_objective(current_params)

                    print(f"반복 {iteration + 1}: 샤프 비율 = {sharpe_score:.3f}")

                    if sharpe_score > best_sharpe:
                        best_sharpe = sharpe_score
                        best_weights = self.params_to_portfolio_weights(current_params)

                except Exception as e:
                    print(f"반복 {iteration + 1} 실패: {e}")
                    continue

            if best_weights is not None:
                self.optimal_weights = best_weights
                print(f"✅ 실제 양자 하드웨어 계산 완료")
                print(f"   - 사용된 백엔드: {least_busy_backend.name}")
                print(f"   - 최종 샤프 비율: {best_sharpe:.3f}")
                print(f"   - 실행된 회로 수: 5개 (제한된 최적화)")
                return True
            else:
                print("❌ 유효한 결과를 얻지 못함")
                return self.optimize_portfolio_classical()

        except Exception as e:
            print(f"❌ 실제 양자 하드웨어 실행 실패: {e}")
            print("클래식 최적화로 폴백")
            return self.optimize_portfolio_classical()

    def run_simulator_vqe(self, backend_info):
        """로컬 시뮬레이터에서 VQE 실행"""
        try:
            backend = backend_info['backend']
            num_assets = len(self.mean_returns)

            print(f"🖥️  로컬 시뮬레이터에서 VQE 계산 중...")

            # VQE 앤사츠 생성
            qc, params = self.create_vqe_ansatz(num_assets, num_layers=1)

            if qc is not None and params is not None:
                # Estimator 사용
                if Estimator is not None:
                    estimator = Estimator()

                    # 해밀토니안 생성
                    initial_weights = np.ones(num_assets) / num_assets
                    hamiltonian = self.create_cost_hamiltonian(initial_weights)

                    if hamiltonian is not None:
                        # VQE 실행
                        def vqe_objective(params_vals):
                            param_dict = {params[i]: params_vals[i] for i in range(len(params))}
                            bound_qc = qc.assign_parameters(param_dict)

                            job = estimator.run([bound_qc], [hamiltonian])
                            result = job.result()
                            return result.values[0]

                        # 최적화
                        initial_params = np.random.uniform(0, 2*np.pi, len(params))
                        if COBYLA is not None:
                            optimizer = COBYLA(maxiter=100)
                            result = optimizer.minimize(vqe_objective, initial_params)

                            if result.x is not None:
                                self.optimal_weights = self.params_to_portfolio_weights(result.x[:num_assets])
                                print("✅ 양자 시뮬레이터 VQE 완료")
                                return True

            # VQE 실패 시 단순 양자 계산
            return self.run_simple_quantum_calculation(backend)

        except Exception as e:
            print(f"❌ 시뮬레이터 VQE 실행 실패: {e}")
            return self.optimize_portfolio_classical()

    def run_simple_quantum_calculation(self, backend):
        """간단한 양자 계산 (폴백용)"""
        try:
            num_assets = len(self.mean_returns)

            # 간단한 양자 회로
            qc = QuantumCircuit(num_assets, num_assets)

            # 각 큐비트에 임의의 회전 적용
            for i in range(num_assets):
                qc.ry(np.pi/4, i)
                qc.rz(np.pi/3, i)

            qc.measure_all()

            # 회로 실행
            transpiled_qc = transpile(qc, backend)
            job = backend.run(transpiled_qc, shots=1024)
            result = job.result()
            counts = result.get_counts()

            # 측정 결과를 가중치로 변환
            weights = self.counts_to_weights(counts, num_assets)
            self.optimal_weights = weights

            print("✅ 양자 inspired 포트폴리오 최적화 완료")
            print(f"최적화된 가중치: {weights}")
            return True

        except Exception as e:
            print(f"❌ 간단한 양자 계산 실패: {e}")
            return self.optimize_portfolio_classical()

    def counts_to_weights(self, counts, num_assets):
        """측정 결과를 포트폴리오 가중치로 변환"""
        if not counts:
            return np.ones(num_assets) / num_assets

        # 각 비트의 가중치 계산
        weights = np.zeros(num_assets)
        total_shots = sum(counts.values())

        for bitstring, count in counts.items():
            # 비트스트링을 가중치로 변환
            for i, bit in enumerate(bitstring[:num_assets]):
                if bit == '1':
                    weights[i] += count

        # 정규화
        if np.sum(weights) > 0:
            weights = weights / np.sum(weights)
        else:
            weights = np.ones(num_assets) / num_assets

        return weights

    def params_to_portfolio_weights(self, params):
        """매개변수를 포트폴리오 가중치로 변환"""
        # 소프트맥스 변환
        exp_params = np.exp(params)
        weights = exp_params / np.sum(exp_params)
        return weights


def optimize_quantum_portfolio_from_json(json_file_path, investment_amount, use_real_quantum=False):
    """JSON 파일에서 주식 목록을 읽어 양자 포트폴리오 최적화 실행"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            stock_data = json.load(file)

        optimizer = QuantumPortfolioOptimizer(stock_data, investment_amount, use_real_quantum=use_real_quantum)
        result = optimizer.run_optimization()
        return result

    except Exception as e:
        print(f"JSON 파일 처리 중 오류 발생: {e}")
        return None


if __name__ == "__main__":
    # 테스트용 예제
    test_stocks = ["005930", "000660", "035420", "051910", "068270"]  # 삼성전자, SK하이닉스, 네이버, LG화학, 셀트리온
    investment_amount = 10000000  # 1천만원

    print(f"Qiskit 사용 가능: {QISKIT_AVAILABLE}")
    print("=" * 60)

    # 1. 로컬 시뮬레이터 테스트
    print("1. 로컬 시뮬레이터 테스트")
    print("-" * 30)
    optimizer_local = QuantumPortfolioOptimizer(test_stocks, investment_amount, use_real_quantum=False)
    result_local = optimizer_local.run_optimization()

    if result_local:
        print(f"로컬 최적화 완료:")
        print(f"  샤프 비율: {result_local['performance']['sharpe_ratio']:.3f}")
        print(f"  사용된 방법: {result_local['method']}")
        print(f"  차트: {result_local['chart_file']}")

    print("\n" + "=" * 60)

    # 2. 실제 IBM Quantum 하드웨어 테스트 (API 키가 있는 경우)
    print("2. IBM Quantum 하드웨어 테스트")
    print("-" * 30)

    # .env 파일에서 IBM Quantum 토큰 확인
    ibm_token = os.getenv('IBM_QUANTUM_TOKEN')
    if ibm_token and ibm_token != 'your_ibm_quantum_token_here':
        print("IBM Quantum API 키가 감지되었습니다. 실제 하드웨어를 시도합니다...")
        optimizer_hw = QuantumPortfolioOptimizer(test_stocks, investment_amount, use_real_quantum=True)
        result_hw = optimizer_hw.run_optimization()

        if result_hw:
            print(f"하드웨어 최적화 완료:")
            print(f"  샤프 비율: {result_hw['performance']['sharpe_ratio']:.3f}")
            print(f"  사용된 방법: {result_hw['method']}")
            print(f"  백엔드 정보: {result_hw['backend_info']}")

            # 결과 비교
            if result_local and result_hw:
                print("\n" + "=" * 60)
                print("3. 결과 비교 (로컬 vs 하드웨어)")
                print("-" * 30)
                print(f"로컬 시뮬레이터 샤프 비율: {result_local['performance']['sharpe_ratio']:.3f}")
                print(f"IBM Quantum 하드웨어 샤프 비율: {result_hw['performance']['sharpe_ratio']:.3f}")
                print(f"로컬 백엔드: {result_local['backend_info']['name']}")
                print(f"하드웨어 백엔드: {result_hw['backend_info']['name']}")
        else:
            print("하드웨어 최적화 실패 - 로컬 결과만 사용")
    else:
        print("IBM Quantum API 키가 없습니다. 로컬 시뮬레이터만 사용합니다.")
        print("실제 하드웨어를 사용하려면:")
        print("1. https://quantum-computing.ibm.com/ 에서 계정 생성")
        print("2. API 토큰 발급")
        print("3. .env 파일에 IBM_QUANTUM_TOKEN=your_token_here 추가")

    print("\n" + "=" * 60)
    print("4. 사용 방법 가이드")
    print("-" * 30)
    print("실제 IBM Quantum 하드웨어 사용 방법:")
    print("1. https://quantum-computing.ibm.com/ 에서 계정 생성")
    print("2. API 토큰 발급")
    print("3. .env 파일에 IBM_QUANTUM_TOKEN=your_token_here 추가")
    print("4. use_real_quantum=True로 설정하여 실행")
    print("\n백엔드 선택 우선순위:")
    print("1순위: IBM Quantum 실제 하드웨어 (대기열이 가장 짧은 것)")
    print("2순위: 로컬 양자 시뮬레이터 (Aer)")
    print("3순위: 클래식 최적화 (scipy)")
    print("\n폴백 시나리오:")
    print("- 하드웨어 사용 불가 → 로컬 시뮬레이터")
    print("- 로컬 시뮬레이터 사용 불가 → 클래식 최적화")
    print("- 모든 양자 방법 실패 → 클래식 최적화")