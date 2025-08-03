#!/usr/bin/env python3
"""
포트폴리오 최적화 실행 스크립트

사용법:
1. JSON 파일로 실행 (클래식):
   python portfolio_runner.py --json stocks.json --amount 10000000

2. JSON 파일로 실행 (양자):
   python portfolio_runner.py --json stocks.json --amount 10000000 --quantum

3. 직접 주식 코드 입력 (클래식):
   python portfolio_runner.py --stocks 005930,000660,035420 --amount 10000000

4. 직접 주식 코드 입력 (양자):
   python portfolio_runner.py --stocks 005930,000660,035420 --amount 10000000 --quantum --hardware

5. 대화형 모드:
   python portfolio_runner.py --interactive
"""

import argparse
import json
import sys
import os
from classic_opt import PortfolioOptimizer, optimize_portfolio_from_json

# 양자 최적화 import (실패 시 None)
try:
    from quantum_opt import QuantumPortfolioOptimizer, optimize_quantum_portfolio_from_json
    QUANTUM_AVAILABLE = True
except ImportError:
    QUANTUM_AVAILABLE = False
    print("양자 최적화 모듈을 찾을 수 없습니다. 클래식 최적화만 사용 가능합니다.")

def create_sample_json():
    """샘플 JSON 파일 생성"""
    sample_data = {
        "description": "한국 대형주 포트폴리오",
        "stocks": [
            {"symbol": "005930", "name": "삼성전자"},
            {"symbol": "000660", "name": "SK하이닉스"},
            {"symbol": "035420", "name": "NAVER"},
            {"symbol": "051910", "name": "LG화학"},
            {"symbol": "068270", "name": "셀트리온"},
            {"symbol": "207940", "name": "삼성바이오로직스"},
            {"symbol": "006400", "name": "삼성SDI"},
            {"symbol": "028260", "name": "삼성물산"}
        ]
    }

    with open('sample_stocks.json', 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)

    print("샘플 JSON 파일 'sample_stocks.json'이 생성되었습니다.")
    return 'sample_stocks.json'

def interactive_mode():
    """대화형 모드"""
    print("=== 포트폴리오 최적화 대화형 모드 ===")

    # 투자 금액 입력
    while True:
        try:
            amount_str = input("투자 금액을 입력하세요 (예: 10000000): ")
            investment_amount = int(amount_str.replace(',', ''))
            break
        except ValueError:
            print("올바른 숫자를 입력해주세요.")

    # 최적화 방법 선택
    optimization_method = 'classic'
    use_real_quantum = False

    if QUANTUM_AVAILABLE:
        print("\n최적화 방법을 선택하세요:")
        print("1. 클래식 최적화 (기본)")
        print("2. 양자 최적화 (로컬 시뮬레이터)")
        print("3. 양자 최적화 (IBM Quantum 하드웨어)")

        while True:
            opt_choice = input("선택 (1/2/3): ").strip()
            if opt_choice in ['1', '2', '3']:
                break
            print("1, 2, 또는 3을 입력해주세요.")

        if opt_choice == '2':
            optimization_method = 'quantum'
            use_real_quantum = False
        elif opt_choice == '3':
            optimization_method = 'quantum'
            use_real_quantum = True
            print("⚠️  IBM Quantum 하드웨어 사용을 위해 .env 파일에 IBM_QUANTUM_TOKEN이 설정되어 있는지 확인하세요.")
    else:
        print("\n양자 최적화가 사용 불가능합니다. 클래식 최적화를 사용합니다.")

    # 주식 코드 입력 방식 선택
    print("\n주식 입력 방식을 선택하세요:")
    print("1. 직접 입력")
    print("2. JSON 파일 사용")
    print("3. 샘플 데이터 사용")

    while True:
        choice = input("선택 (1/2/3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("1, 2, 또는 3을 입력해주세요.")

    if choice == '1':
        # 직접 입력
        stocks_str = input("주식 코드를 쉼표로 구분하여 입력하세요 (예: 005930,000660,035420): ")
        stocks = [s.strip() for s in stocks_str.split(',')]

        if optimization_method == 'quantum' and QUANTUM_AVAILABLE:
            optimizer = QuantumPortfolioOptimizer(stocks, investment_amount, use_real_quantum=use_real_quantum)
        else:
            optimizer = PortfolioOptimizer(stocks, investment_amount)
        return optimizer.run_optimization()

    elif choice == '2':
        # JSON 파일
        json_path = input("JSON 파일 경로를 입력하세요: ").strip()
        if not os.path.exists(json_path):
            print(f"파일을 찾을 수 없습니다: {json_path}")
            return None

        if optimization_method == 'quantum' and QUANTUM_AVAILABLE:
            return optimize_quantum_portfolio_from_json(json_path, investment_amount, use_real_quantum=use_real_quantum)
        else:
            return optimize_portfolio_from_json(json_path, investment_amount)

    else:
        # 샘플 데이터
        print("샘플 데이터를 사용합니다.")
        sample_file = create_sample_json()

        if optimization_method == 'quantum' and QUANTUM_AVAILABLE:
            return optimize_quantum_portfolio_from_json(sample_file, investment_amount, use_real_quantum=use_real_quantum)
        else:
            return optimize_portfolio_from_json(sample_file, investment_amount)

def main():
    parser = argparse.ArgumentParser(description='포트폴리오 최적화 도구')
    parser.add_argument('--json', type=str, help='주식 리스트 JSON 파일 경로')
    parser.add_argument('--stocks', type=str, help='주식 코드 (쉼표로 구분)')
    parser.add_argument('--amount', type=int, help='투자 금액')
    parser.add_argument('--interactive', action='store_true', help='대화형 모드')
    parser.add_argument('--sample', action='store_true', help='샘플 JSON 파일 생성')
    parser.add_argument('--output', type=str, default='./', help='출력 디렉토리')
    parser.add_argument('--quantum', action='store_true', help='양자 최���화 사용')
    parser.add_argument('--hardware', action='store_true', help='양자 하드웨어 사용')

    args = parser.parse_args()

    # 샘플 파일 생성
    if args.sample:
        create_sample_json()
        return

    # 대화형 모드
    if args.interactive:
        result = interactive_mode()
        if result:
            print("\n✅ 포트폴리오 최적화가 완료되었습니다!")
        else:
            print("\n❌ 최적화 중 오류가 발생했습니다.")
        return

    # 일반 모드
    if not args.amount:
        print("투자 금액을 지정해주세요. --amount 옵션을 사용하세요.")
        parser.print_help()
        return

    # 양자 최적화 옵션 검증
    if args.quantum and not QUANTUM_AVAILABLE:
        print("⚠️  양자 최적화가 요청되었지만 사용할 수 없습니다. 클래식 최적화를 사용합니다.")
        args.quantum = False

    if args.hardware and not args.quantum:
        print("⚠️  --hardware 옵션은 --quantum 옵션과 함께 사용해야 합니다.")
        return

    # 양자 최적화 설정
    use_real_quantum = args.quantum and args.hardware

    if args.json:
        # JSON 파일 모드
        if not os.path.exists(args.json):
            print(f"JSON 파일을 찾을 수 없습니다: {args.json}")
            return

        print(f"JSON 파일에서 주식 리스트를 읽어옵니다: {args.json}")

        if args.quantum and QUANTUM_AVAILABLE:
            print(f"양자 최적화 사용 (하드웨어: {'Yes' if use_real_quantum else 'No'})")
            result = optimize_quantum_portfolio_from_json(args.json, args.amount, use_real_quantum=use_real_quantum)
        else:
            print("클래식 최적화 사용")
            result = optimize_portfolio_from_json(args.json, args.amount)

    elif args.stocks:
        # 직접 입력 모드
        stocks = [s.strip() for s in args.stocks.split(',')]
        print(f"입력된 주식 코드: {stocks}")

        if args.quantum and QUANTUM_AVAILABLE:
            print(f"양자 최적화 사용 (하드웨어: {'Yes' if use_real_quantum else 'No'})")
            optimizer = QuantumPortfolioOptimizer(stocks, args.amount, use_real_quantum=use_real_quantum)
        else:
            print("클래식 최적화 사용")
            optimizer = PortfolioOptimizer(stocks, args.amount)

        result = optimizer.run_optimization()

    else:
        print("주식 리스트를 지정해주세요. --json 또는 --stocks 옵션을 사용하세요.")
        parser.print_help()
        return

    if result:
        print("\n✅ 포트폴리오 최적화가 완료되었습니다!")
        print(f"📊 분석 차트: {result['chart_file']}")

        # 사용된 방법 출력
        if 'method' in result:
            print(f"🔬 최적화 방법: {result['method']}")
        if 'backend_info' in result:
            backend_info = result['backend_info']
            print(f"🖥️  백엔드: {backend_info['name']} ({backend_info['type']})")

        # 간단한 요약 출력
        print(f"\n📈 포트폴리오 성과 요약:")
        print(f"  - 예상 연간 수익률: {result['performance']['expected_return']:.1%}")
        print(f"  - 예상 연간 변동성: {result['performance']['volatility']:.1%}")
        print(f"  - 샤프 비율: {result['performance']['sharpe_ratio']:.3f}")

        print(f"\n💰 상위 3개 투자 종목:")
        for i, allocation in enumerate(result['allocations'][:3]):
            if allocation['weight'] > 0.001:
                print(f"  {i+1}. {allocation['symbol']}: {allocation['amount']:,}원 ({allocation['percentage']:.1f}%)")
    else:
        print("\n❌ 최적화 중 오류가 발생했습니다.")

if __name__ == "__main__":
    main()
