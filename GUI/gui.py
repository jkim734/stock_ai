import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import sys
import os
from datetime import datetime
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.font_manager as fm

# optimizer 모듈 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'optimizer'))

try:
    from classic_opt import PortfolioOptimizer
    from quantum_opt import QuantumPortfolioOptimizer
    OPTIMIZER_AVAILABLE = True
except ImportError as e:
    print(f"Optimizer import error: {e}")
    OPTIMIZER_AVAILABLE = False

class StockAIGUI:
    def __init__(self, root):
        self.root = root
        self.setup_ui()
        self.result_data = None

    def setup_ui(self):
        """UI 구성 요소 설정"""
        self.root.title("Stock AI - Portfolio Optimizer")
        self.root.geometry("800x700")
        self.root.configure(bg='#f0f0f0')

        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 제목
        title_label = tk.Label(
            main_frame,
            text="Stock AI",
            font=("Arial", 32, "bold"),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))

        # 부제목
        subtitle_label = tk.Label(
            main_frame,
            text="It's the economy, stupid!",
            font=("Arial", 14, "italic"),
            bg='#f0f0f0',
            fg='#7f8c8d'
        )
        subtitle_label.grid(row=1, column=0, columnspan=2, pady=(0, 30))

        # 투자 금액 입력 섹션
        investment_frame = ttk.LabelFrame(main_frame, text="투자 설정", padding="15")
        investment_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))

        # 투자 금액 입력
        ttk.Label(investment_frame, text="투자 금액 (원):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.amount_var = tk.StringVar(value="10000000")
        amount_entry = ttk.Entry(investment_frame, textvariable=self.amount_var, font=("Arial", 12), width=20)
        amount_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))

        # 주식 선택 방법
        ttk.Label(investment_frame, text="주식 선택:").grid(row=1, column=0, sticky=tk.W, pady=5)

        self.stock_method_var = tk.StringVar(value="sample")
        method_frame = ttk.Frame(investment_frame)
        method_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))

        ttk.Radiobutton(method_frame, text="샘플 주식 사용", variable=self.stock_method_var, value="sample").grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(method_frame, text="직접 입력", variable=self.stock_method_var, value="manual").grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        ttk.Radiobutton(method_frame, text="JSON 파일", variable=self.stock_method_var, value="json").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))

        # 직접 입력 필드
        ttk.Label(investment_frame, text="주식 코드:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.stocks_var = tk.StringVar(value="005930,000660,035420,051910,068270")
        stocks_entry = ttk.Entry(investment_frame, textvariable=self.stocks_var, font=("Arial", 10), width=40)
        stocks_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))

        # JSON 파일 선택
        json_frame = ttk.Frame(investment_frame)
        json_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(json_frame, text="JSON 파일:").grid(row=0, column=0, sticky=tk.W)
        self.json_file_var = tk.StringVar()
        ttk.Entry(json_frame, textvariable=self.json_file_var, width=30, state="readonly").grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 5))
        ttk.Button(json_frame, text="파일 선택", command=self.select_json_file).grid(row=0, column=2)

        # 최적화 방법 선택
        optimizer_frame = ttk.LabelFrame(main_frame, text="최적화 방법", padding="15")
        optimizer_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))

        self.optimizer_var = tk.StringVar(value="classic")
        ttk.Radiobutton(optimizer_frame, text="클래식 최적화", variable=self.optimizer_var, value="classic").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Radiobutton(optimizer_frame, text="양자 최적화 (시뮬레이터)", variable=self.optimizer_var, value="quantum_sim").grid(row=0, column=1, sticky=tk.W, padx=(20, 0), pady=5)
        ttk.Radiobutton(optimizer_frame, text="양자 최적화 (IBM 하드웨어)", variable=self.optimizer_var, value="quantum_hw").grid(row=0, column=2, sticky=tk.W, padx=(20, 0), pady=5)

        # 최적화 실행 버튼
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)

        self.optimize_button = ttk.Button(
            button_frame,
            text="포트폴리오 최적화 실행",
            command=self.run_optimization,
            style="Accent.TButton"
        )
        self.optimize_button.grid(row=0, column=0, padx=10)

        ttk.Button(button_frame, text="결과 저장", command=self.save_results).grid(row=0, column=1, padx=10)
        ttk.Button(button_frame, text="차트 보기", command=self.show_chart).grid(row=0, column=2, padx=10)

        # 진행 상황 표시
        self.progress_var = tk.StringVar(value="대기 중...")
        progress_label = ttk.Label(main_frame, textvariable=self.progress_var, font=("Arial", 10))
        progress_label.grid(row=5, column=0, columnspan=2, pady=10)

        self.progress_bar = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress_bar.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))

        # 결과 표시 영역
        result_frame = ttk.LabelFrame(main_frame, text="최적화 결과", padding="15")
        result_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))

        # 결과 텍스트 위젯 (스크롤 가능)
        text_frame = ttk.Frame(result_frame)
        text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.result_text = tk.Text(text_frame, height=15, width=70, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)

        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)
        investment_frame.columnconfigure(1, weight=1)
        json_frame.columnconfigure(1, weight=1)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        # 초기 메시지 표시
        self.display_welcome_message()

    def display_welcome_message(self):
        """환영 메시지 표시"""
        welcome_msg = """
🚀 Stock AI 포트폴리오 최적화 시스템에 오신 것을 환영합니다!

📊 기능:
• 클래식 최적화: 전통적인 평균-분산 최적화
• 양자 최적화: 최신 양자 컴퓨팅 기술 활용
• 실시간 주식 데이터 수집 및 분석
• 포트폴리오 성과 시각화

📝 사용 방법:
1. 투자 금액을 입력하세요
2. 주식 선택 방법을 선택하세요
3. 최적화 방법을 선택하세요
4. '포트폴리오 최적화 실행' 버튼을 클릭하세요

💡 팁: 샘플 주식(삼성전자, SK하이닉스, 네이버, LG화학, 셀트리온)으로 먼저 테스트해보세요!
"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, welcome_msg)

    def select_json_file(self):
        """JSON 파일 선택"""
        filename = filedialog.askopenfilename(
            title="주식 리스트 JSON 파일 선택",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.json_file_var.set(filename)

    def get_stock_list(self):
        """선택된 방법에 따라 주식 리스트 반환"""
        method = self.stock_method_var.get()

        if method == "sample":
            return ["005930", "000660", "035420", "051910", "068270"]  # 샘플 주식
        elif method == "manual":
            stocks_str = self.stocks_var.get().strip()
            if not stocks_str:
                raise ValueError("주식 코드를 입력해주세요.")
            return [s.strip() for s in stocks_str.split(',')]
        elif method == "json":
            json_file = self.json_file_var.get().strip()
            if not json_file:
                raise ValueError("JSON 파일을 선택해주세요.")
            return json_file
        else:
            raise ValueError("올바른 주식 선택 방법을 선택해주세요.")

    def validate_inputs(self):
        """입력값 검증"""
        try:
            amount = int(self.amount_var.get().replace(',', ''))
            if amount <= 0:
                raise ValueError("투자 금액은 0보다 커야 합니다.")
        except ValueError:
            raise ValueError("올바른 투자 금액을 입력해주세요.")

        stock_list = self.get_stock_list()
        return amount, stock_list

    def run_optimization(self):
        """최적화 실행 (별도 스레드에서)"""
        try:
            # 입력값 검증
            amount, stock_list = self.validate_inputs()

            # UI 업데이트
            self.optimize_button.config(state="disabled")
            self.progress_bar.start()
            self.progress_var.set("최적화 진행 중...")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "🔄 포트폴리오 최적화를 시작합니다...\n\n")

            # 별도 스레드에서 최적화 실행
            threading.Thread(
                target=self.optimize_portfolio,
                args=(amount, stock_list),
                daemon=True
            ).start()

        except Exception as e:
            messagebox.showerror("입력 오류", str(e))

    def optimize_portfolio(self, amount, stock_list):
        """실제 최적화 실행"""
        try:
            if not OPTIMIZER_AVAILABLE:
                raise Exception("Optimizer 모듈을 찾을 수 없습니다.")

            optimizer_type = self.optimizer_var.get()

            # 진행 상황 업데이트
            self.root.after(0, lambda: self.update_progress("데이터 수집 중..."))

            print(f"최적화 시작 - 방법: {optimizer_type}, 금액: {amount}, 주식: {stock_list}")

            result = None
            if optimizer_type == "classic":
                # 클래식 최적화
                if isinstance(stock_list, str):  # JSON 파일인 경우
                    from classic_opt import optimize_portfolio_from_json
                    result = optimize_portfolio_from_json(stock_list, amount)
                else:
                    optimizer = PortfolioOptimizer(stock_list, amount)
                    result = optimizer.run_optimization()

            else:
                # 양자 최적화
                use_hardware = (optimizer_type == "quantum_hw")

                if isinstance(stock_list, str):  # JSON 파일인 경우
                    from quantum_opt import optimize_quantum_portfolio_from_json
                    result = optimize_quantum_portfolio_from_json(stock_list, amount, use_real_quantum=use_hardware)
                else:
                    optimizer = QuantumPortfolioOptimizer(stock_list, amount, use_real_quantum=use_hardware)
                    result = optimizer.run_optimization()

            # 결과 처리
            print(f"최적화 결과: {result is not None}")
            if result:
                print(f"결과 키들: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                # 스레드 안전한 방식으로 결과 업데이트
                self.result_data = result
                # GUI 업데이트는 메인 스레드에서 실행되도록 예약
                self.root.after(100, lambda: self.display_results_safe(result))
            else:
                print("결과가 None입니다.")
                self.root.after(100, lambda: self.show_error("최적화에 실패했습니다. 콘솔을 확인해주세요."))

        except Exception as e:
            print(f"최적화 중 예외 발생: {e}")
            import traceback
            print(f"상세 오류:\n{traceback.format_exc()}")
            self.root.after(100, lambda: self.show_error(f"오류 발생: {str(e)}"))
        finally:
            # UI 복원
            self.root.after(200, self.reset_ui)

    def update_progress(self, message):
        """진행 상황 업데이트"""
        self.progress_var.set(message)
        self.result_text.insert(tk.END, f"📍 {message}\n")
        self.result_text.see(tk.END)

    def display_results_safe(self, result):
        """스레드 안전한 결과 표시"""
        try:
            print("GUI에서 결과 표시 시작")
            self.display_results(result)
            print("GUI에서 결과 표시 완료")
        except Exception as e:
            print(f"결과 표시 중 오류: {e}")
            import traceback
            print(f"상세 오류:\n{traceback.format_exc()}")
            self.show_error(f"결과 표시 중 오류: {str(e)}")

    def display_results(self, result):
        """결과 표시"""
        print("display_results 호출됨")
        try:
            self.result_text.delete(1.0, tk.END)

            # 결과 데이터 검증
            if not isinstance(result, dict):
                raise ValueError("결과가 딕셔너리 형태가 아닙니다.")

            if 'performance' not in result:
                raise ValueError("성과 데이터가 없습니다.")

            if 'allocations' not in result:
                raise ValueError("배분 데이터가 없습니다.")

            # 성과 요약
            perf = result['performance']
            method = result.get('method', '알 수 없음')

            result_msg = f"""
✅ 포트폴리오 최적화 완료!

🔬 최적화 방법: {method}
📊 성과 요약:
  • 예상 연간 수익률: {perf['expected_return']:.2%}
  • 예상 연간 변동성: {perf['volatility']:.2%}
  • 샤프 비율: {perf['sharpe_ratio']:.3f}

💰 투자 배분:
"""

            # 배분 정보 추가
            allocations = result['allocations']
            print(f"배분 데이터 개수: {len(allocations)}")

            for i, allocation in enumerate(allocations[:10]):  # 상위 10개만 표시
                if allocation.get('weight', 0) > 0.001:  # 0.1% 이상만 표시
                    symbol = allocation.get('symbol', 'Unknown')
                    amount = allocation.get('amount', 0)
                    percentage = allocation.get('percentage', 0)
                    result_msg += f"  {i+1:2d}. {symbol}: {amount:,}원 ({percentage:.1f}%)\n"

            if 'chart_file' in result:
                result_msg += f"\n📈 차트 파일: {result['chart_file']}"

            if 'backend_info' in result:
                backend = result['backend_info']
                result_msg += f"\n🖥️ 백엔드: {backend['name']} ({backend['type']})"

            result_msg += f"\n\n⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            # 텍스트 위젯에 결과 표시
            self.result_text.insert(tk.END, result_msg)
            self.result_text.see(tk.END)  # 마지막으로 스크롤

            # 상태 업데이트
            self.progress_var.set("최적화 완료!")

            print("결과 표시 완료")

        except Exception as e:
            print(f"결과 표시 중 내부 오류: {e}")
            import traceback
            print(f"상세 오류:\n{traceback.format_exc()}")
            self.show_error(f"결과 표시 오류: {str(e)}")

    def show_error(self, error_msg):
        """오류 메시지 표시"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"❌ {error_msg}")
        self.progress_var.set("오류 발생")
        messagebox.showerror("오류", error_msg)

    def reset_ui(self):
        """UI 상태 복원"""
        self.optimize_button.config(state="normal")
        self.progress_bar.stop()
        if not hasattr(self, 'result_data') or self.result_data is None:
            self.progress_var.set("대기 중...")

    def save_results(self):
        """결과 저장"""
        if not hasattr(self, 'result_data') or self.result_data is None:
            messagebox.showwarning("경고", "저장할 결과가 없습니다.")
            return

        try:
            filename = filedialog.asksaveasfilename(
                title="결과 저장",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )

            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.result_text.get(1.0, tk.END))
                messagebox.showinfo("성공", f"결과가 저장되었습니다: {filename}")
        except Exception as e:
            messagebox.showerror("오류", f"저장 중 오류 발생: {str(e)}")

    def show_chart(self):
        """차트 및 상세 결과 창 표시"""
        if not hasattr(self, 'result_data') or self.result_data is None:
            messagebox.showwarning("경고", "표시할 차트가 없습니다.")
            return

        # 새 창 생성
        chart_window = tk.Toplevel(self.root)
        chart_window.title("포트폴리오 분석 결과")
        chart_window.geometry("1200x800")
        chart_window.configure(bg='#f0f0f0')

        # 메인 프레임
        main_frame = ttk.Frame(chart_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 창 크기 조절 가능하도록 설정
        chart_window.columnconfigure(0, weight=1)
        chart_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # 제목
        title_label = tk.Label(
            main_frame,
            text="�� 포트폴리오 분석 결과",
            font=("Arial", 18, "bold"),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        title_label.grid(row=0, column=0, pady=(0, 20))

        # 노트북 (탭) 위젯 생성
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 탭 1: 차트 이미지
        chart_frame = ttk.Frame(notebook, padding="10")
        notebook.add(chart_frame, text="📈 포트폴리오 차트")

        # 탭 2: 상세 결과
        details_frame = ttk.Frame(notebook, padding="10")
        notebook.add(details_frame, text="📋 상세 분석")

        # 탭 3: 투자 배분
        allocation_frame = ttk.Frame(notebook, padding="10")
        notebook.add(allocation_frame, text="💰 투자 배분")

        # 차트 이미지 표시
        self.display_chart_image(chart_frame)

        # 상세 결과 표시
        self.display_detailed_results(details_frame)

        # 투자 배분 표시
        self.display_allocation_table(allocation_frame)

    def display_chart_image(self, parent_frame):
        """차트 이미지 표시"""
        chart_file = self.result_data.get('chart_file')

        if chart_file and os.path.exists(chart_file):
            try:
                # 이미지 로드 및 크기 조정
                image = Image.open(chart_file)

                # 창 크기에 맞게 이미지 크기 조정
                display_size = (1000, 600)
                image.thumbnail(display_size, Image.Resampling.LANCZOS)

                photo = ImageTk.PhotoImage(image)

                # 스크롤 가능한 프레임 생성
                canvas = tk.Canvas(parent_frame, bg='white')
                scrollbar_v = ttk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
                scrollbar_h = ttk.Scrollbar(parent_frame, orient="horizontal", command=canvas.xview)

                canvas.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)

                # 이미지 표시
                image_label = tk.Label(canvas, image=photo, bg='white')
                image_label.image = photo  # 참조 유지

                canvas.create_window(0, 0, anchor="nw", window=image_label)
                canvas.update_idletasks()
                canvas.configure(scrollregion=canvas.bbox("all"))

                # 그리드 배치
                canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
                scrollbar_v.grid(row=0, column=1, sticky=(tk.N, tk.S))
                scrollbar_h.grid(row=1, column=0, sticky=(tk.W, tk.E))

                # 그리드 가중치
                parent_frame.columnconfigure(0, weight=1)
                parent_frame.rowconfigure(0, weight=1)

            except Exception as e:
                error_label = tk.Label(
                    parent_frame,
                    text=f"❌ 차트 이미지를 로드할 수 없습니다:\n{str(e)}",
                    font=("Arial", 12),
                    fg='red',
                    justify=tk.CENTER
                )
                error_label.grid(row=0, column=0, padx=20, pady=20)
        else:
            no_chart_label = tk.Label(
                parent_frame,
                text="📊 차트 파일을 찾을 수 없습니다.",
                font=("Arial", 14),
                fg='gray',
                justify=tk.CENTER
            )
            no_chart_label.grid(row=0, column=0, padx=20, pady=20)

    def display_detailed_results(self, parent_frame):
        """상세 결과 표시"""
        # 스크롤 가능한 텍스트 위젯
        text_frame = ttk.Frame(parent_frame)
        text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        text_widget = tk.Text(text_frame, font=("Consolas", 11), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        # 상세 정보 텍스트 생성
        perf = self.result_data['performance']
        method = self.result_data.get('method', '알 수 없음')

        detailed_text = f"""
📊 포트폴리오 최적화 상세 결과
{'=' * 50}

🔬 최적화 방법: {method}

📈 포트폴리오 성과 지표:
  • 예상 연간 수익률: {perf['expected_return']:.4%}
  • 예상 연간 변동성: {perf['volatility']:.4%}
  • 샤프 비율: {perf['sharpe_ratio']:.6f}
  • 위험 대비 수익률: {perf['expected_return']/perf['volatility']:.4f}

💰 투자 총액: {sum(allocation['amount'] for allocation in self.result_data['allocations']):,}원

📋 전체 종목별 투자 배분:
{'=' * 50}
"""

        # 모든 배분 정보 추가
        for i, allocation in enumerate(self.result_data['allocations'], 1):
            if allocation['weight'] > 0.0001:  # 0.01% 이상만 표시
                detailed_text += f"{i:3d}. {allocation['symbol']:8s} | "
                detailed_text += f"{allocation['name'][:20]:20s} | "
                detailed_text += f"{allocation['amount']:>12,}원 | "
                detailed_text += f"{allocation['percentage']:>6.2f}% | "
                detailed_text += f"가중치: {allocation['weight']:.4f}\n"

        # 백엔드 정보 추가
        if 'backend_info' in self.result_data:
            backend = self.result_data['backend_info']
            detailed_text += f"""

🖥️ 백엔드 정보:
{'=' * 50}
  • 백엔드 이름: {backend['name']}
  • 백엔드 타입: {backend['type']}
"""

        # 차트 파일 정보 추가
        if 'chart_file' in self.result_data:
            detailed_text += f"""

📈 차트 파일:
{'=' * 50}
  • 파일 경로: {self.result_data['chart_file']}
  • 파일 존재: {'✅' if os.path.exists(self.result_data['chart_file']) else '❌'}
"""

        detailed_text += f"""

⏰ 분석 완료 시간: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}

📌 참고사항:
  • 이 결과는 과거 데이터를 기반으로 한 예측이며, 실제 수익을 보장하지 않습니다.
  • 투자 결정 시 충분한 검토와 전문가 상담을 권장합니다.
  • 포트폴리오는 정기적으로 재조정하는 것이 좋습니다.
"""

        # 텍스트 삽입
        text_widget.insert(tk.END, detailed_text)
        text_widget.config(state=tk.DISABLED)  # 읽기 전용으로 설정

        # 위젯 배치
        text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 그리드 가중치 설정
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

    def display_allocation_table(self, parent_frame):
        """투자 배분 테이블 표시"""
        # 테이블 프레임
        table_frame = ttk.Frame(parent_frame)
        table_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 트리뷰 위젯 생성 (테이블)
        columns = ('순위', '종목코드', '종목명', '투자금액', '비중(%)', '가중치')
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)

        # 헤더 설정
        tree.heading('순위', text='순위')
        tree.heading('종목코드', text='종목코드')
        tree.heading('종목명', text='종목명')
        tree.heading('투자금액', text='투자금액(원)')
        tree.heading('비중(%)', text='비중(%)')
        tree.heading('가중치', text='가중치')

        # 컬럼 너비 설정
        tree.column('순위', width=50, anchor='center')
        tree.column('종목코드', width=80, anchor='center')
        tree.column('종목명', width=200, anchor='w')
        tree.column('투자금액', width=120, anchor='e')
        tree.column('비중(%)', width=80, anchor='e')
        tree.column('가중치', width=100, anchor='e')

        # 스크롤바 추가
        scrollbar_table = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar_table.set)

        # 데이터 삽입
        for i, allocation in enumerate(self.result_data['allocations'], 1):
            if allocation['weight'] > 0.0001:  # 0.01% 이상만 표시
                tree.insert('', 'end', values=(
                    i,
                    allocation['symbol'],
                    allocation['name'][:25],  # 이름 길이 제한
                    f"{allocation['amount']:,}",
                    f"{allocation['percentage']:.2f}",
                    f"{allocation['weight']:.4f}"
                ))

        # 위젯 배치
        tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_table.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 요약 정보 프레임
        summary_frame = ttk.LabelFrame(parent_frame, text="포트폴리오 요약", padding="10")
        summary_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # 요약 정보 레이블들
        perf = self.result_data['performance']
        total_amount = sum(allocation['amount'] for allocation in self.result_data['allocations'])
        active_stocks = len([a for a in self.result_data['allocations'] if a['weight'] > 0.0001])

        summary_info = [
            f"📊 총 투자 금액: {total_amount:,}원",
            f"📈 활성 종목 수: {active_stocks}개",
            f"🎯 예상 연간 수익률: {perf['expected_return']:.2%}",
            f"📉 예상 연간 변동성: {perf['volatility']:.2%}",
            f"⚡ 샤프 비율: {perf['sharpe_ratio']:.3f}"
        ]

        for i, info in enumerate(summary_info):
            label = ttk.Label(summary_frame, text=info, font=("Arial", 10))
            label.grid(row=i//2, column=i%2, sticky=tk.W, padx=10, pady=2)

        # 그리드 가중치 설정
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.columnconfigure(1, weight=1)


def main():
    """메인 함수"""
    root = tk.Tk()
    app = StockAIGUI(root)

    # 스타일 설정
    style = ttk.Style()
    style.theme_use('clam')

    # 애플리케이션 실행
    root.mainloop()


if __name__ == "__main__":
    main()
