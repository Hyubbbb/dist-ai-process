"""
커버리지 계산 방식 비교 실험
"""

import sys
import os
import time
from main import run_optimization

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def compare_coverage_methods():
    """2가지 커버리지 계산 방식 비교 (고급 방식 제거)"""
    
    print("🔍 커버리지 계산 방식 비교 실험")
    print("="*60)
    
    # 비교할 시나리오들 (고급 방식 제거)
    coverage_scenarios = [
        "original_coverage",    # 원래 방식
        "normalized_coverage"   # 정규화 방식 (스타일별 색상/사이즈 개수 반영)
    ]
    
    results = {}
    
    for scenario in coverage_scenarios:
        print(f"\n{'='*70}")
        print(f"🧪 시나리오: {scenario}")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        result = run_optimization(
            target_style='DWLG42044',
            scenario=scenario,
            show_detailed_output=False,
            create_visualizations=False  # 속도를 위해 비활성화
        )
        
        total_time = time.time() - start_time
        
        if result:
            step_analysis = result.get('step_analysis', {})
            overall_eval = result['analysis_results']['overall_evaluation']
            
            results[scenario] = {
                'step1_objective': step_analysis.get('step1', {}).get('objective', 0),
                'step1_combinations': step_analysis.get('step1', {}).get('combinations', 0),
                'step2_additional': step_analysis.get('step2', {}).get('additional_allocation', 0),
                'step3_additional': step_analysis.get('step3', {}).get('additional_allocation', 0),
                'total_time': total_time,
                'color_coverage': overall_eval.get('overall_color_coverage', 0),
                'size_coverage': overall_eval.get('overall_size_coverage', 0),
                'total_score': overall_eval.get('total_score', 0),
                'grade': overall_eval.get('grade', 'N/A')
            }
            
            print(f"✅ {scenario} 완료")
        else:
            print(f"❌ {scenario} 실패")
            results[scenario] = None
    
    # 결과 비교 출력
    print_comparison_results(results)

def print_comparison_results(results):
    """비교 결과 상세 출력 (고급 방식 제거)"""
    
    print(f"\n🏆 커버리지 계산 방식 비교 결과")
    print("="*80)
    
    # 헤더
    print(f"{'방식':25} | {'Step1점수':10} | {'조합수':8} | {'색상커버':8} | {'사이즈커버':8} | {'총점':8} | {'등급':10}")
    print("-" * 80)
    
    # 각 방식별 결과
    method_names = {
        'original_coverage': '원래 방식 (불균등 가중치)',
        'normalized_coverage': '정규화 방식 (스타일별 반영)'
    }
    
    for scenario, data in results.items():
        if data:
            name = method_names.get(scenario, scenario)
            print(f"{name:25} | {data['step1_objective']:10.1f} | {data['step1_combinations']:8d} | "
                  f"{data['color_coverage']:8.3f} | {data['size_coverage']:8.3f} | "
                  f"{data['total_score']:8.3f} | {data['grade']:10}")
    
    # 분석 및 권장사항
    print(f"\n📊 상세 분석:")
    print("-" * 50)
    
    if 'original_coverage' in results and 'normalized_coverage' in results:
        orig = results['original_coverage']
        norm = results['normalized_coverage'] 
        
        if orig and norm:
            print(f"\n🔍 원래 방식 vs 정규화 방식:")
            print(f"   Step1 점수: {orig['step1_objective']:.1f} → {norm['step1_objective']:.1f} "
                  f"({norm['step1_objective'] - orig['step1_objective']:+.1f})")
            print(f"   색상 커버리지: {orig['color_coverage']:.3f} → {norm['color_coverage']:.3f} "
                  f"({norm['color_coverage'] - orig['color_coverage']:+.3f})")
            print(f"   사이즈 커버리지: {orig['size_coverage']:.3f} → {norm['size_coverage']:.3f} "
                  f"({norm['size_coverage'] - orig['size_coverage']:+.3f})")
    
    print(f"\n💡 권장사항:")
    print("   📈 스타일별 공정한 평가: '정규화 방식' 사용")
    print("   📋 기존 호환성 유지: '원래 방식' 사용")

def explain_coverage_calculation():
    """커버리지 계산 방식 설명 (고급 방식 제거)"""
    
    print(f"\n📚 커버리지 계산 방식 설명")
    print("="*60)
    
    print(f"\n🎯 스타일별 구성이 다름:")
    print(f"   DWLG42044: 색상 2개, 사이즈 4개 → 총 8개 SKU")
    print(f"   다른 스타일: 색상 3개, 사이즈 5개 → 총 15개 SKU")
    print(f"   ⚠️ 스타일마다 색상/사이즈 개수가 다르므로 정규화 필요!")
    
    print(f"\n📊 매장별 최대 커버리지:")
    print(f"   색상 커버리지: 0~N점 (N = 해당 스타일의 색상 개수)")
    print(f"   사이즈 커버리지: 0~M점 (M = 해당 스타일의 사이즈 개수)")
    
    print(f"\n🔄 각 방식별 계산법:")
    
    print(f"\n1️⃣ 원래 방식 (불균등 가중치):")
    print(f"   목적함수: ∑(색상커버리지 + 사이즈커버리지)")
    print(f"   문제점: 스타일별 색상/사이즈 개수 차이 미반영")
    print(f"   예시 DWLG42044: 매장A(색상2, 사이즈4) = 6점")
    print(f"   예시 다른스타일: 매장B(색상3, 사이즈5) = 8점 → 스타일 간 비교 불가능")
    
    print(f"\n2️⃣ 정규화 방식 (스타일별 개수 반영):")
    print(f"   목적함수: ∑(색상가중치×색상커버리지 + 사이즈가중치×사이즈커버리지)")
    print(f"   개선점: 스타일별 색상/사이즈 개수를 반영한 정규화")
    print(f"   DWLG42044: 색상가중치=1/2=0.5, 사이즈가중치=1/4=0.25")
    print(f"   다른스타일: 색상가중치=1/3=0.333, 사이즈가중치=1/5=0.2")
    print(f"   예시 DWLG42044: 매장A(0.5×2 + 0.25×4) = 2.0점")
    print(f"   예시 다른스타일: 매장B(0.333×3 + 0.2×5) = 2.0점 → 스타일 간 공정 비교")

if __name__ == "__main__":
    print("🧪 커버리지 계산 방식 비교 도구")
    print("="*50)
    
    # 설명 출력
    explain_coverage_calculation()
    
    # 사용자 확인
    print(f"\n❓ 비교 실험을 실행하시겠습니까? (약 3분 소요)")
    response = input("Enter를 누르면 실행, 'n'을 입력하면 종료: ")
    
    if response.lower() != 'n':
        # 비교 실험 실행
        compare_coverage_methods()
    else:
        print("실험을 취소했습니다.") 