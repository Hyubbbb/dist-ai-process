"""
다양한 실험 예시 스크립트
"""

from main import run_optimization, run_batch_experiments

def example_1_single_experiment():
    """예시 1: 단일 실험 (다른 스타일 + 다른 시나리오)"""
    print("🧪 예시 1: 단일 실험")
    
    result = run_optimization(
        target_style="DWLG42044",      # 스타일 코드
        scenario="balance_focused",     # 균형 중심 시나리오
        show_detailed_output=True,      # 상세 출력
        create_visualizations=True      # 시각화 생성
    )
    
    if result:
        print(f"✅ 실험 완료! 결과 저장 위치: {result['experiment_path']}")
        print(f"📊 종합 등급: {result['analysis_results']['overall_evaluation']['grade']}")
    
    return result

def example_2_compare_scenarios():
    """예시 2: 동일 스타일로 다른 시나리오들 비교"""
    print("\n🧪 예시 2: 시나리오 비교")
    
    target_style = "DWLG42044"
    scenarios_to_test = ["baseline", "coverage_focused", "balance_focused", "hybrid"]
    
    results = []
    for scenario in scenarios_to_test:
        print(f"\n🔄 {scenario} 시나리오 실행 중...")
        result = run_optimization(
            target_style=target_style,
            scenario=scenario,
            show_detailed_output=False,  # 배치 실험이므로 상세 출력 끄기
            create_visualizations=True
        )
        
        if result:
            results.append({
                'scenario': scenario,
                'grade': result['analysis_results']['overall_evaluation']['grade'],
                'score': result['analysis_results']['overall_evaluation']['total_score'],
                'path': result['experiment_path']
            })
    
    # 결과 비교
    print(f"\n📊 시나리오 비교 결과 (스타일: {target_style}):")
    print("-" * 60)
    for r in results:
        print(f"  {r['scenario']:15} | 등급: {r['grade']:8} | 점수: {r['score']:.3f}")
    
    return results

def example_3_batch_experiments():
    """예시 3: 배치 실험 (여러 스타일 × 여러 시나리오)"""
    print("\n🧪 예시 3: 배치 실험")
    
    # 여러 스타일이 있다고 가정 (실제 데이터에 따라 조정)
    target_styles = [
                     "DWLG42044",
                    #  "DWDJ68046",
                    #  "DMDJ85046",
                    #  "DWDJ8P046",
                    #  "DXDJ8C046",
                    #  "DXMT33044",
                    #  "DWLG42044",
                     ]  # 현재 사용 가능한 스타일
    scenarios = [
                # "baseline", 
                #  "coverage_focused", 
                #  "balance_focused",
                 "hybrid",
                #  "extreme_coverage"
                 ]
    
    results = run_batch_experiments(
        target_styles=target_styles,
        scenarios=scenarios,
        create_visualizations=True  # 시각화 활성화
    )
    
    print(f"\n📊 배치 실험 완료! 총 {len(results)}개 실험 성공")
    
    return results

def example_4_custom_scenario():
    """예시 4: 사용자 정의 실험 (config 수정 없이)"""
    print("\n🧪 예시 4: 사용자 정의 실험")
    
    # 기존 시나리오 중에서 선택
    print("🎯 사용 가능한 시나리오:")
    from config import EXPERIMENT_SCENARIOS
    
    for i, (scenario, config) in enumerate(EXPERIMENT_SCENARIOS.items(), 1):
        print(f"  {i}. {scenario}: {config['description']}")
    
    # 특정 시나리오 선택
    chosen_scenario = "extreme_coverage"
    
    result = run_optimization(
        target_style="DWLG42044", 
        scenario=chosen_scenario,
        show_detailed_output=False,
        create_visualizations=True
    )
    
    if result:
        print(f"✅ {chosen_scenario} 실험 완료!")
        eval_result = result['analysis_results']['overall_evaluation']
        print(f"   등급: {eval_result['grade']}")
        print(f"   점수: {eval_result['total_score']:.3f}")
        print(f"   색상 커버리지: {eval_result['overall_color_coverage']:.3f}")
        print(f"   사이즈 커버리지: {eval_result['overall_size_coverage']:.3f}")
    
    return result

def run_custom_experiment(style_code, scenario_name):
    """사용자 정의 실험 함수"""
    print(f"🚀 사용자 정의 실험: {style_code} - {scenario_name}")
    
    result = run_optimization(
        target_style=style_code,
        scenario=scenario_name,
        show_detailed_output=True,
        create_visualizations=True
    )
    
    return result

if __name__ == "__main__":
    """실행 예시"""
    print("🎬 실험 예시 스크립트 실행")
    print("="*50)
    
    # 실행할 예시 선택 (주석 해제하여 실행)
    
    # 예시 1: 단일 실험
    # example_1_single_experiment()
    
    # 예시 2: 시나리오 비교 (시간이 오래 걸림)
    # example_2_compare_scenarios()
    
    # 예시 3: 배치 실험 (시간이 매우 오래 걸림)
    example_3_batch_experiments()
    
    # 예시 4: 사용자 정의 실험
    # example_4_custom_scenario()
    
    # 직접 실험 실행
    # run_custom_experiment("DWLG42044", "coverage_focused")
    
    print("\n🎉 예시 스크립트 완료!")
    print("💡 원하는 예시의 주석을 해제하고 실행해보세요!") 