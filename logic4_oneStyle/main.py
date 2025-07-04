"""
SKU 분배 최적화 메인 실행 파일
"""

import sys
import os
import time

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules import (
    DataLoader, StoreTierSystem, SKUClassifier, 
    ResultAnalyzer, ResultVisualizer, ExperimentManager
)
from modules.three_step_optimizer import ThreeStepOptimizer
from config import EXPERIMENT_SCENARIOS, DEFAULT_TARGET_STYLE, DEFAULT_SCENARIO
from modules.objective_analyzer import ObjectiveAnalyzer


def run_optimization(target_style=DEFAULT_TARGET_STYLE, scenario=DEFAULT_SCENARIO, 
                    show_detailed_output=False, create_visualizations=True):
    """
    SKU 분배 최적화 실행
    
    Args:
        target_style: 대상 스타일 코드
        scenario: 실험 시나리오 이름
        show_detailed_output: 상세 출력 여부
        create_visualizations: 시각화 생성 여부
    """
    
    start_time = time.time()
    
    print("🚀 SKU 분배 최적화 시작")
    print(f"   대상 스타일: {target_style}")
    print(f"   시나리오: {scenario}")
    print("="*50)
    
    try:
        # 1. 데이터 로드 및 전처리
        print("\n📊 1단계: 데이터 로드 및 전처리")
        data_loader = DataLoader()
        data_loader.load_data()
        data_loader.filter_by_style(target_style)
        data = data_loader.get_basic_data_structures()
        
        # 2. 매장 Tier 시스템 설정
        print("\n🏆 2단계: 매장 Tier 시스템 설정")
        tier_system = StoreTierSystem()
        target_stores = tier_system.get_target_stores(data['stores'], target_style)
        store_allocation_limits = tier_system.create_store_allocation_limits(target_stores)
        
        # 3. SKU 분류
        print("\n🔍 3단계: SKU 분류 (희소/충분)")
        sku_classifier = SKUClassifier(data_loader.df_sku_filtered)
        scarce_skus, abundant_skus = sku_classifier.classify_skus(data['A'], target_stores)
        
        if show_detailed_output:
            sku_classifier.print_detailed_summary(data['A'], show_details=True)
        
        # 4. 3-Step 최적화 (Step1: 커버리지 + Step2: 1개씩 배분 + Step3: 잔여 배분)
        print("\n🎯 4단계: 3-Step 최적화")
        three_step_optimizer = ThreeStepOptimizer(target_style)
        
        # 시나리오 파라미터 가져오기
        scenario_params = EXPERIMENT_SCENARIOS[scenario].copy()
        
        optimization_result = three_step_optimizer.optimize_three_step(
            data, scarce_skus, abundant_skus, target_stores,
            store_allocation_limits, data_loader.df_sku_filtered,
            tier_system, scenario_params
        )
        
        if optimization_result['status'] != 'success':
            print("❌ 3-Step 최적화 실패")
            return None
        
        final_allocation = optimization_result['final_allocation']
        allocation_summary = optimization_result  # 결과 요약을 그대로 사용
        
        # 5. 결과 분석
        print("\n📊 5단계: 결과 분석")
        analyzer = ResultAnalyzer(target_style)
        analysis_results = analyzer.analyze_results(
            final_allocation, data, scarce_skus, abundant_skus,
            target_stores, data_loader.df_sku_filtered, data['QSUM'], tier_system
        )
        
        # 6. 결과 DataFrame 생성
        df_results = analyzer.create_result_dataframes(
            final_allocation, data, scarce_skus, target_stores,
            data_loader.df_sku_filtered, tier_system, {}  # b_hat 대신 빈 딕셔너리
        )
        
        # 7. 실험 결과 저장
        print("\n💾 7단계: 실험 결과 저장")
        experiment_manager = ExperimentManager()
        
        # 시나리오 파라미터 준비
        scenario_params = EXPERIMENT_SCENARIOS[scenario].copy()
        scenario_params['target_style'] = target_style
        
        # 시나리오 이름 생성 (스타일 포함)
        scenario_name = f"{scenario}_{target_style}"
        
        # 출력 경로 생성
        experiment_path, file_paths = experiment_manager.create_experiment_output_path(scenario_name)
        
        # 결과 저장
        experiment_manager.save_experiment_results(
            file_paths, df_results, analysis_results, scenario_params,
            scenario_name, allocation_summary
        )
        
        # 8. 시각화 (옵션)
        if create_visualizations:
            print("\n📈 8단계: 시각화 생성")
            visualizer = ResultVisualizer()
            
            try:
                # PNG 저장 경로 생성
                import os
                visualization_dir = experiment_path

                comprehensive_chart_path = os.path.join(visualization_dir, f"{scenario_name}_comprehensive_analysis.png")
                summary_chart_path = os.path.join(visualization_dir, f"{scenario_name}_summary_chart.png")

                # Step별 allocation matrix 경로 (Step1/Step2/Step3)
                matrix_step1_path = os.path.join(visualization_dir, f"{scenario_name}_step1_allocation_matrix.png")
                matrix_step2_path = os.path.join(visualization_dir, f"{scenario_name}_step2_allocation_matrix.png")
                matrix_step3_path = os.path.join(visualization_dir, f"{scenario_name}_step3_allocation_matrix.png")
                
                # 종합 시각화 (PNG로 저장)
                visualizer.create_comprehensive_visualization(
                    analysis_results, target_style, save_path=comprehensive_chart_path
                )
                
                # 간단 요약 차트 (PNG로 저장)  
                visualizer.create_simple_summary_chart(
                    analysis_results, save_path=summary_chart_path
                )
                
                # 배분 매트릭스 히트맵 (Step1, Step2, Step3) - 100개 매장 모두 표시

                # Step1
                if hasattr(three_step_optimizer, 'step1_allocation') and three_step_optimizer.step1_allocation:
                    visualizer.create_allocation_matrix_heatmap(
                        three_step_optimizer.step1_allocation,
                        target_stores, data['SKUs'], data['QSUM'],
                        data_loader.df_sku_filtered, data['A'], tier_system,
                        save_path=matrix_step1_path, max_stores=100, max_skus=8,
                        fixed_max=3
                    )

                # Step2
                if hasattr(three_step_optimizer, 'allocation_after_step2') and three_step_optimizer.allocation_after_step2:
                    visualizer.create_allocation_matrix_heatmap(
                        three_step_optimizer.allocation_after_step2,
                        target_stores, data['SKUs'], data['QSUM'],
                        data_loader.df_sku_filtered, data['A'], tier_system,
                        save_path=matrix_step2_path, max_stores=100, max_skus=8,
                        fixed_max=3
                    )

                # Step3 (최종)
                visualizer.create_allocation_matrix_heatmap(
                    final_allocation, target_stores, data['SKUs'],
                    data['QSUM'], data_loader.df_sku_filtered, data['A'], tier_system,
                    save_path=matrix_step3_path, max_stores=100, max_skus=8,
                    fixed_max=3
                )
                
            except Exception as e:
                print(f"⚠️ 시각화 생성 중 오류: {str(e)}")
                print("   (시각화 오류는 전체 프로세스에 영향을 주지 않습니다)")
        
        # ✅ 3-Step 분해 분석 추가
        if optimization_result['status'] == 'success':
            try:
                # 3-Step 분해 정보 추출
                step_analysis = three_step_optimizer.get_step_analysis()
                
                print(f"📊 3-Step 분해 결과:")
                print(f"   🎯 Step1 - 커버리지 최적화:")
                print(f"       커버리지 점수: {step_analysis['step1']['objective']:.1f}")
                print(f"       선택된 SKU-매장 조합: {step_analysis['step1']['combinations']}개")
                print(f"       소요 시간: {step_analysis['step1']['time']:.2f}초")
                print(f"   📦 Step2 - 1개씩 추가 배분:")
                print(f"       추가 배분량: {step_analysis['step2']['additional_allocation']}개")
                print(f"       소요 시간: {step_analysis['step2']['time']:.2f}초")
                print(f"   📦 Step3 - 잔여 수량 추가 배분:")
                print(f"       추가 배분량: {step_analysis['step3']['additional_allocation']}개")
                print(f"       소요 시간: {step_analysis['step3']['time']:.2f}초")
                print(f"   🎲 Step2 우선순위: {scenario_params.get('allocation_priority_step2', scenario_params.get('allocation_priority', 'balanced'))}")
                print(f"   🎲 Step3 우선순위: {scenario_params.get('allocation_priority_step3', scenario_params.get('allocation_priority', 'balanced'))}")
                print(f"   ⏱️ 총 소요시간: {step_analysis['total_time']:.2f}초")
                
                # 배분 우선순위 설명
                from config import ALLOCATION_PRIORITY_OPTIONS
                allocation_priority = scenario_params.get('allocation_priority', 'sequential')
                if allocation_priority in ALLOCATION_PRIORITY_OPTIONS:
                    priority_info = ALLOCATION_PRIORITY_OPTIONS[allocation_priority]
                    print(f"       └ {priority_info['name']}: {priority_info['description']}")
                
                # 3-Step 분해 정보를 결과에 추가
                optimization_result['step_analysis'] = step_analysis
                
            except Exception as e:
                print(f"⚠️ 3-Step 분해 분석 실패: {e}")
                optimization_result['step_analysis'] = {}
        
        # 9. 최종 요약 출력
        print("\n" + "="*50)
        print("         🎉 3-Step 최적화 완료!")
        print("="*50)
        
        overall_eval = analysis_results['overall_evaluation']
        print(f"📊 최종 결과:")
        print(f"   🎯 대상 스타일: {target_style}")
        print(f"   🚀 3-Step 사용")
        print(f"   📈 종합 등급: {overall_eval['grade']}")
        print(f"   📊 종합 점수: {overall_eval['total_score']:.3f}")
        print(f"   📁 결과 저장: {experiment_path}")
        print(f"   📄 총 생성 파일: {len(file_paths)}개")
        
        print(f"✅ 총 소요시간: {time.time() - start_time:.2f}초")
        return {
            'status': 'success',
            'target_style': target_style,
            'scenario': scenario,
            'analysis_results': analysis_results,
            'df_results': df_results,
            'experiment_path': experiment_path,
            'file_paths': file_paths,
            'step_analysis': optimization_result.get('step_analysis', {})
        }
        
    except Exception as e:
        print(f"\n❌ 최적화 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def run_batch_experiments(target_styles=None, scenarios=None, create_visualizations=False):
    """
    배치 실험 실행
    
    Args:
        target_styles: 실험할 스타일 리스트 (None이면 기본 스타일만)
        scenarios: 실험할 시나리오 리스트 (None이면 모든 시나리오)
        create_visualizations: 시각화 생성 여부 (기본값: False, 시간 절약)
    """
    
    if target_styles is None:
        target_styles = [DEFAULT_TARGET_STYLE]
    
    if scenarios is None:
        scenarios = list(EXPERIMENT_SCENARIOS.keys())
    
    print(f"🔬 배치 실험 시작:")
    print(f"   대상 스타일: {target_styles}")
    print(f"   시나리오: {scenarios}")
    print(f"   총 실험 수: {len(target_styles) * len(scenarios)}개")
    
    results = []
    objective_data = []  # 목적함수 분석용 데이터
    
    for target_style in target_styles:
        for scenario in scenarios:
            print(f"\n{'='*60}")
            print(f"실험: {target_style} - {scenario}")
            print(f"{'='*60}")
            
            result = run_optimization(
                target_style=target_style,
                scenario=scenario,
                show_detailed_output=False,
                create_visualizations=create_visualizations  # 파라미터로 제어
            )
            
            if result:
                results.append(result)
                print(f"✅ 완료: {target_style} - {scenario}")
                
                # 목적함수 분석용 데이터 준비
                step_analysis = result.get('step_analysis', {})
                if step_analysis:
                    # 시나리오 파라미터 추출
                    scenario_config = EXPERIMENT_SCENARIOS.get(scenario, {})
                    
                    objective_data.append({
                        'scenario': f"{scenario}_{target_style}",
                        'objective': step_analysis['step1']['objective'],  # Step1 커버리지만 사용
                        'breakdown': step_analysis,
                        'coverage_weight': scenario_config.get('coverage_weight', 1.0),
                        'balance_penalty_weight': scenario_config.get('balance_penalty', 0.1),
                        'experiment_result': result
                    })
                
                print(f"   ✅ 실험 완료 - Step1 커버리지: {step_analysis['step1']['objective']:.1f}, Step2 추가배분: {step_analysis['step2']['additional_allocation']}개")
            else:
                print(f"❌ 실패: {target_style} - {scenario}")
    
    print(f"\n🎉 배치 실험 완료!")
    print(f"   성공한 실험: {len(results)}개")
    print(f"   실패한 실험: {len(target_styles) * len(scenarios) - len(results)}개")
    
    # 개선된 목적함수 분석 수행
    if len(objective_data) >= 2:
        analyzer = ObjectiveAnalyzer()
        analysis_results = analyzer.analyze_experiments(objective_data)
        
        if analysis_results:
            print(f"\n🎉 개선된 목적함수 분석 완료!")
            print(f"   📈 분해 분석 차트: {analysis_results['decomposition_chart']}")
            print(f"   🔄 정규화 비교 차트: {analysis_results['normalized_chart']}")
            if analysis_results['sensitivity_heatmap']:
                print(f"   🔥 민감도 히트맵: {analysis_results['sensitivity_heatmap']}")
            print(f"   📋 개선된 분석 리포트: {analysis_results['analysis_report']}")
    else:
        print(f"⚠️ 목적함수 분석을 위해서는 최소 2개의 성공한 실험이 필요합니다.")
    
    return results


def list_saved_experiments():
    """저장된 실험 목록 출력"""
    experiment_manager = ExperimentManager()
    experiments = experiment_manager.list_experiments()
    
    if not experiments:
        print("저장된 실험이 없습니다.")
        return
    
    print(f"💾 저장된 실험 목록 ({len(experiments)}개):")
    print("-" * 80)
    
    for i, exp in enumerate(experiments[:10], 1):  # 최신 10개만 표시
        print(f"{i:2d}. {exp['folder_name']}")
        print(f"     스타일: {exp.get('target_style', 'Unknown')}")
        print(f"     시나리오: {exp.get('scenario_name', 'Unknown')}")
        print(f"     생성시간: {exp['created_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    if len(experiments) > 10:
        print(f"... 외 {len(experiments) - 10}개 실험")


if __name__ == "__main__":
    """메인 실행부"""
    
    print("🔧 SKU 분배 최적화 시스템")
    print("="*50)
    
    # 기본 설정으로 단일 실험 실행
    """
    시나리오 종류
    baseline: 상위 매장 순차적 배분 (QTY_SUM 높은 순서)
        - Step2 우선순위: sequential
        - Step3 우선순위: sequential
    balanced: 균형 배분 (상위 매장 우선 * 중간 매장도 기회 제공)
        - Step2 우선순위: balanced
        - Step3 우선순위: balanced
    random: 완전 랜덤 배분 (모든 매장 동일 확률)
        - Step2 우선순위: random
        - Step3 우선순위: random
    three_step_fair: 공평: 미배분 매장 우선
        - Step2 우선순위: balanced_unfilled
        - Step3 우선순위: balanced_unfilled
    my_custom: 커스텀 3-Step: Step2는 랜덤으로 미배분 매장 우선, Step3는 순차적 배분
        - Step2 우선순위: random_unfilled
        - Step3 우선순위: sequential


    2. 우선순위 옵션
    sequential: 순차적 배분 (QTY_SUM 높은 순서)
    random: 랜덤 배분
    balanced: 균형 배분
    
    sequential_unfilled: 순차적 배분 (미배분 매장 우선)
    random_unfilled: 랜덤 배분 (미배분 매장 우선)
    balanced_unfilled: 균형 배분 (미배분 매장 우선)
    """
    result = run_optimization(target_style='DWLG42044', 
                              scenario='my_custom')
    
    # result = run_batch_experiments(['DWLG42044'], 
    #                                ['baseline', 'balanced', 'random'])
    
    # 실험 목록 출력
    # print("\n" + "="*50)
    # list_saved_experiments()
    
    # 사용법 안내
    print("\n💡 사용법:")
    print("   단일 실험: run_optimization(target_style='DWLG42044', scenario='baseline')")
    print("   배치 실험: run_batch_experiments(['DWLG42044'], ['baseline', 'balanced', 'random'])")
    print("   실험 목록: list_saved_experiments()")
    print("   다른 스타일: config.py에서 설정 변경 가능")
    print("   사용 가능한 시나리오: baseline, balanced, random, high_coverage, my_custom, three_step_fair, three_step_performance")
    print("   커버리지 비교 시나리오: original_coverage, normalized_coverage")
    print("   커버리지 방식 비교: python compare_coverage_methods.py (스타일별 색상/사이즈 개수 반영)") 