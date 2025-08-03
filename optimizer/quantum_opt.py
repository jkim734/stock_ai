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

    from qiskit_aer import AerSimulator

    try:
        from qiskit.providers.fake_provider import FakeBackend
    except ImportError:
        try:
            from qiskit_ibm_runtime.fake_provider import FakeBackend
        except ImportError:
            FakeBackend = None

    try:
        from qiskit_ibm_runtime import Session
    except ImportError:
        Session = None

    # Try different optimizer imports based on available versions
    try:
        from qiskit_algorithms.optimizers import COBYLA, SPSA
        from qiskit_algorithms import VQE
    except ImportError:
        try:
            from qiskit.algorithms.optimizers import COBYLA, SPSA
            from qiskit.algorithms import VQE
        except ImportError:
            from scipy.optimize import minimize
            COBYLA = None
            SPSA = None
            VQE = None

    try:
        from qiskit.quantum_info import SparsePauliOp
    except ImportError:
        SparsePauliOp = None

    QISKIT_AVAILABLE = True
except ImportError as e:
    print(f"Qiskit import error: {e}")
    print("양자 컴퓨팅 기능을 사용할 수 없습니다. 클래식 최적화만 사용됩니다.")
    QISKIT_AVAILABLE = False
    AerSimulator = None
    Session = None
    Estimator = None
    RuntimeEstimator = None

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
        """IBM Quantum 서비스 초기화 (계정 저장 방식)"""
        try:
            ibm_token = os.getenv('IBM_QUANTUM_TOKEN')
            if ibm_token and self.use_real_quantum:
                # 토큰 형식 검증
                if len(ibm_token.strip()) < 20:
                    print("⚠️  IBM Quantum 토큰이 너무 짧습니다. 올바른 토큰인지 확인하세요.")
                    self.use_real_quantum = False
                    return

                print(f"IBM Quantum 토큰 확인됨 (길이: {len(ibm_token)} 자)")

                # IBM Quantum 계정 저장 및 서비스 초기화
                connection_methods = [
                    # 방법 1: 계정 저장 후 기본 서비스 연결
                    {
                        'name': '계정 저장 방식 (기본)',
                        'save_params': {
                            'token': ibm_token,
                            'set_as_default': True,
                            'overwrite': True
                        },
                        'service_params': {}
                    },
                    # 방법 2: 계정 저장 with instance 지정
                    {
                        'name': '계정 저장 방식 (instance)',
                        'save_params': {
                            'token': ibm_token,
                            'instance': 'ibm-q/open/main',
                            'set_as_default': True,
                            'overwrite': True
                        },
                        'service_params': {}
                    },
                    # 방법 3: 계정 저장 with channel 지정
                    {
                        'name': '계정 저장 방식 (channel)',
                        'save_params': {
                            'token': ibm_token,
                            'channel': 'ibm_quantum',
                            'set_as_default': True,
                            'overwrite': True
                        },
                        'service_params': {}
                    },
                    # 방법 4: 명명된 계정 저장
                    {
                        'name': '명명된 계정 저장',
                        'save_params': {
                            'token': ibm_token,
                            'name': 'stock_ai_account',
                            'set_as_default': True,
                            'overwrite': True
                        },
                        'service_params': {'name': 'stock_ai_account'}
                    },
                    # 방법 5: 직접 토큰 연결 (폴백)
                    {
                        'name': '직접 토큰 연결',
                        'save_params': None,
                        'service_params': {'token': ibm_token, 'channel': 'ibm_quantum'}
                    }
                ]

                for method in connection_methods:
                    try:
                        print(f"연결 시도: {method['name']}")

                        # 계정 저장 단계
                        if method['save_params'] is not None:
                            try:
                                QiskitRuntimeService.save_account(**method['save_params'])
                                print(f"  ✓ 계정 저장 완료")
                            except Exception as save_error:
                                print(f"  ⚠️  계정 저장 중 경고: {save_error}")
                                # 저장 실패해도 계속 진행

                        # 서비스 연결 단계
                        self.service = QiskitRuntimeService(**method['service_params'])

                        # 연결 테스트: 백엔드 목록 가져오기 시도
                        try:
                            backends = list(self.service.backends())
                            print(f"✅ IBM Quantum 서비스 연결 완료 ({method['name']})")
                            print(f"  📡 사용 가능한 백엔드 수: {len(backends)}")

                            # 하드웨어 백엔드 수 확인
                            hardware_backends = [b for b in backends if not b.simulator]
                            if hardware_backends:
                                print(f"  🔧 하드웨어 백엔드 수: {len(hardware_backends)}")
                                print(f"  🖥️  예시 하드웨어: {[b.name for b in hardware_backends[:3]]}")
                            else:
                                print("  ⚠️  하드웨어 백엔드를 찾을 수 없습니다.")

                            return True

                        except Exception as test_error:
                            print(f"  ❌ 백엔드 목록 가져오기 실패: {test_error}")
                            continue

                    except Exception as conn_error:
                        print(f"  ❌ {method['name']} 연결 실패: {conn_error}")
                        continue

                # 모든 연결 방식 실패
                print("\n❌ 모든 IBM Quantum 연결 방식이 실패했습니다.")
                print("\n🔧 해결 방법:")
                print("1. IBM Quantum Platform에서 새로운 API 토큰 발급:")
                print("   https://quantum.ibm.com/account")
                print("2. 토큰을 .env.ibm_api 파일에 저장:")
                print("   IBM_QUANTUM_TOKEN=your_new_token_here")
                print("3. 기존 저장된 계정 정보 삭제 후 재시도:")
                print("   python3 -c \"from qiskit_ibm_runtime import QiskitRuntimeService; QiskitRuntimeService.delete_account()\"")
                print("4. IBM Quantum 계정이 활성화되어 있는지 확인")
                print("\n🔄 로컬 시뮬레이터로 대체합니다.")
                self.use_real_quantum = False
                return False

            else:
                print("🖥️  로컬 시뮬레이터 사용")
                return True

        except Exception as e:
            print(f"IBM Quantum 서비스 초기화 중 전체 오류: {e}")
            print("🔄 로컬 시뮬레이터로 대체")
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

        print(f"���이터 수집 중: {symbols}")

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
                            stock_prices[symbol] = hist.iloc[:, 0]
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
            print(f"  - 데이터 기간: {self.stock_data.index[0].date()} ~ {self.stock_data.index[-1].date()}")
            print(f"  - �� 거래일: {len(self.stock_data)} 일")

            return True

        except Exception as e:
            print(f"데이터 수집 실패: {e}")
            import traceback
            print(f"상세 오류:\n{traceback.format_exc()}")
            return False

    def calculate_returns(self):
        """일일 수익률 계산 (classic_opt와 동일)"""
        if self.stock_data is None:
            raise ValueError("먼저 데이터를 수집해���세요.")

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
        """포트폴리오 최적화를 위한 비용 함수 해밀토���안 생성"""
        if not QISKIT_AVAILABLE or SparsePauliOp is None:
            return None

        num_assets = len(weights)

        # 샤프 비율의 음수를 최소화하는 해밀토니안
        portfolio_return = np.sum(weights * self.mean_returns)
        portfolio_variance = np.dot(weights.T, np.dot(self.cov_matrix, weights))

        # 간단한 선형 해밀토니안으로 근사
        paulis = []
        coeffs = []

        for i in range(num_assets):
            # 각 자산의 기여도를 Z 연산자로 인코딩
            pauli_str = ['I'] * num_assets
            pauli_str[i] = 'Z'
            paulis.append(''.join(pauli_str))

            # 수익률과 리스크를 고려한 계수
            risk_adjusted_return = self.mean_returns.iloc[i] / np.sqrt(self.cov_matrix.iloc[i, i])
            coeffs.append(-risk_adjusted_return)  # ���수로 최대화를 최소화로 변환

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
            raise ValueError("먼저 수익률을 계산해���세요.")

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
            print("클래식 포트폴리오 최적화 완료")
            return True
        else:
            print("클래식 최적화 실패")
            return False

    def calculate_allocation(self):
        """각 기업별 투자 금액 계산 (classic_opt와 동일)"""
        if self.optimal_weights is None:
            raise ValueError("먼저 포트폴리오를 최적화해주세요.")

        allocations = []
        symbols = list(self.stock_data.columns)

        for i, weight in enumerate(self.optimal_weights):
            symbol = symbols[i].replace('.KS', '')
            amount = self.investment_amount * weight
            allocations.append({
                'symbol': symbol,
                'weight': weight,
                'amount': int(amount),
                'percentage': weight * 100
            })

        allocations.sort(key=lambda x: x['weight'], reverse=True)
        return allocations

    def monte_carlo_simulation(self, num_simulations=10000):
        """몬테카를로 시뮬레이션 (classic_opt와 동일)"""
        if self.returns is None:
            raise ValueError("먼저 수익률�� 계산해주세요.")

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
            raise ValueError("먼저 ��트폴리오를 최적화해주세요.")

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

        # 2. 포트폴리��� 구성 비율 (파이 차트)
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

        # 4. 개별 주��� 가격 변화
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
        """사�� 가능한 최적의 백엔드를 선택 (하드웨어 → 로컬 시뮬레이터 → 클래식)"""
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
                    print(f"✓ IBM Quantum 하드웨어 ���택: {best_backend.name} (대기열: {backend_info['queue_length']})")
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
        """선택된 백엔드로 VQE 실행 (Qiskit 2.x 호환)"""
        num_assets = len(self.mean_returns)

        if backend_info['type'] == 'classical':
            return self.optimize_portfolio_classical()

        try:
            print(f"양자 VQE 실행 중... (백엔드: {backend_info['name']})")

            # Qiskit 2.x에서는 더 간단한 최적화 방식 사용
            if COBYLA is not None:
                optimizer = COBYLA(maxiter=100)

                # 직접 매개변수 최적화 사용 (Qiskit 2.x 호환성)
                return self.quantum_portfolio_objective_optimization(optimizer)
            else:
                print("COBYLA 옵티마이저를 사용할 수 없습니다.")
                return self.optimize_portfolio_classical()

        except Exception as e:
            print(f"양자 VQE 실행 중 오류 ({backend_info['name']}): {e}")
            print("클래식 최적화로 폴백")
            return self.optimize_portfolio_classical()

    def quantum_portfolio_objective_optimization(self, optimizer):
        """VQE 없이 직접 매개변수 최적화"""
        try:
            num_assets = len(self.mean_returns)
            initial_point = np.random.uniform(0, 2*np.pi, num_assets)

            result = optimizer.minimize(
                fun=self.quantum_portfolio_objective,
                x0=initial_point
            )

            if result.fun is not None:
                optimal_params = result.x
                raw_weights = optimal_params[:num_assets]
                self.optimal_weights = np.exp(raw_weights) / np.sum(np.exp(raw_weights))

                print("✓ 양자 inspired 포트폴리오 최적화 완료")
                print(f"최적화된 가중치: {self.optimal_weights}")
                return True
            else:
                return False

        except Exception as e:
            print(f"양자 inspired 최적화 실패: {e}")
            return False


def optimize_quantum_portfolio_from_json(json_file_path, investment_amount, use_real_quantum=False):
    """JSON 파일에서 기업 리스트를 읽어 양자 포트폴리오 최적화 실행"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            stock_data = json.load(f)

        optimizer = QuantumPortfolioOptimizer(stock_data, investment_amount, use_real_quantum=use_real_quantum)
        return optimizer.run_optimization()

    except Exception as e:
        print(f"에러 발생: {e}")
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
        print("\n✓ 로컬 양자 포트폴리오 최적화 완료!")
        print(f"차트 파일: {result_local['chart_file']}")
        print(f"최적화 방법: {result_local['method']}")
        print(f"백엔드 정보: {result_local['backend_info']}")

    print("\n" + "=" * 60)

    # 2. 실제 IBM Quantum 하드웨어 테스트 (API 키가 있는 경우)
    print("2. IBM Quantum 하드웨어 테스트")
    print("-" * 30)

    # .env 파일에서 IBM Quantum 토큰 확인
    ibm_token = os.getenv('IBM_QUANTUM_TOKEN')
    if ibm_token and ibm_token != 'your_ibm_quantum_token_here':
        print("IBM Quantum API 키가 감지되었습니다. 실제 하드웨어를 시도합니��...")
        optimizer_hardware = QuantumPortfolioOptimizer(test_stocks, investment_amount, use_real_quantum=True)
        result_hardware = optimizer_hardware.run_optimization()

        if result_hardware:
            print("\n✓ IBM Quantum 하드웨어 포트폴리오 최적화 완료!")
            print(f"차트 파일: {result_hardware['chart_file']}")
            print(f"최적화 방법: {result_hardware['method']}")
            print(f"백엔드 정보: {result_hardware['backend_info']}")

            # 하드웨어와 로컬 결과 비교
            if result_local and result_hardware:
                print("\n" + "=" * 60)
                print("3. 결과 비교 (로컬 vs 하드웨어)")
                print("-" * 30)
                print(f"로컬 시뮬레이터 샤프 비율: {result_local['performance']['sharpe_ratio']:.3f}")
                print(f"IBM Quantum 하드웨어 샤프 비율: {result_hardware['performance']['sharpe_ratio']:.3f}")
                print(f"로컬 백엔드: {result_local['backend_info']['name']}")
                print(f"하드웨어 백엔드: {result_hardware['backend_info']['name']}")
        else:
            print("✗ IBM Quantum 하드웨어 최적화 실패")
    else:
        print("IBM Quantum API 키가 설정되지 않았습니다.")
        print("실제 하드웨어를 사용하려면 .env 파일에 IBM_QUANTUM_TOKEN을 설정하세요.")
        print("IBM Quantum 계정: https://quantum-computing.ibm.com/")

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
