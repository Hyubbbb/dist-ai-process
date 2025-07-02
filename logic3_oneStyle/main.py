"""
SKU 분배 최적화 메인 실행 파일
"""

import sys
import os

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules import (
    DataLoader, StoreTierSystem, SKUClassifier, 
    CoverageOptimizer, GreedyAllocator, ResultAnalyzer,
    ResultVisualizer, ExperimentManager
)
from config import EXPERIMENT_SCENARIOS, DEFAULT_TARGET_STYLE, DEFAULT_SCENARIO


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
        
        # 4. Step1: Coverage 최적화
        print("\n🎯 4단계: Step1 - Coverage 최적화")
        coverage_optimizer = CoverageOptimizer(target_style)
        optimization_result = coverage_optimizer.optimize_coverage(
            data, scarce_skus, target_stores, store_allocation_limits, data_loader.df_sku_filtered
        )
        
        if optimization_result['status'] != 'success':
            print("❌ Coverage 최적화 실패")
            return None
        
        b_hat = optimization_result['b_hat']
        
        # 5. Step2: 결정론적 추가 배분
        print("\n⚙️ 5단계: Step2 - 결정론적 추가 배분")
        greedy_allocator = GreedyAllocator(tier_system)
        allocation_summary = greedy_allocator.allocate(
            data, b_hat, scarce_skus, abundant_skus, target_stores,
            store_allocation_limits, data['QSUM']
        )
        
        # 6. 결과 분석
        print("\n📊 6단계: 결과 분석")
        analyzer = ResultAnalyzer(target_style)
        analysis_results = analyzer.analyze_results(
            greedy_allocator.final_allocation, data, scarce_skus, abundant_skus,
            target_stores, data_loader.df_sku_filtered, data['QSUM'], tier_system
        )
        
        # 7. 결과 DataFrame 생성
        df_results = analyzer.create_result_dataframes(
            greedy_allocator.final_allocation, data, scarce_skus, target_stores,
            data_loader.df_sku_filtered, tier_system, b_hat
        )
        
        # 8. 실험 결과 저장
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
        
        # 9. 시각화 (옵션)
        if create_visualizations:
            print("\n📈 8단계: 시각화 생성")
            visualizer = ResultVisualizer()
            
            try:
                # PNG 저장 경로 생성
                import os
                visualization_dir = experiment_path
                comprehensive_chart_path = os.path.join(visualization_dir, f"{scenario_name}_comprehensive_analysis.png")
                summary_chart_path = os.path.join(visualization_dir, f"{scenario_name}_summary_chart.png")
                matrix_heatmap_path = os.path.join(visualization_dir, f"{scenario_name}_allocation_matrix.png")
                
                # 종합 시각화 (PNG로 저장)
                visualizer.create_comprehensive_visualization(
                    analysis_results, target_style, save_path=comprehensive_chart_path
                )
                
                # 간단 요약 차트 (PNG로 저장)  
                visualizer.create_simple_summary_chart(
                    analysis_results, save_path=summary_chart_path
                )
                
                # 배분 매트릭스 히트맵 (PNG로 저장) - 100개 매장 모두 표시
                visualizer.create_allocation_matrix_heatmap(
                    greedy_allocator.final_allocation, target_stores, data['SKUs'], 
                    data['QSUM'], data_loader.df_sku_filtered, 
                    save_path=matrix_heatmap_path, max_stores=100, max_skus=8
                )
                
            except Exception as e:
                print(f"⚠️ 시각화 생성 중 오류: {str(e)}")
                print("   (시각화 오류는 전체 프로세스에 영향을 주지 않습니다)")
        
        # 10. 최종 요약 출력
        print("\n" + "="*50)
        print("           🎉 최적화 완료!")
        print("="*50)
        
        overall_eval = analysis_results['overall_evaluation']
        print(f"📊 최종 결과:")
        print(f"   🎯 대상 스타일: {target_style}")
        print(f"   📈 종합 등급: {overall_eval['grade']}")
        print(f"   📊 종합 점수: {overall_eval['total_score']:.3f}")
        print(f"   📁 결과 저장: {experiment_path}")
        print(f"   📄 총 생성 파일: {len(file_paths)}개")
        
        return {
            'status': 'success',
            'target_style': target_style,
            'scenario': scenario,
            'analysis_results': analysis_results,
            'df_results': df_results,
            'experiment_path': experiment_path,
            'file_paths': file_paths
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
            else:
                print(f"❌ 실패: {target_style} - {scenario}")
    
    print(f"\n🎉 배치 실험 완료!")
    print(f"   성공한 실험: {len(results)}개")
    print(f"   실패한 실험: {len(target_styles) * len(scenarios) - len(results)}개")
    
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
    result = run_optimization()
    
    # 실험 목록 출력
    print("\n" + "="*50)
    list_saved_experiments()
    
    # 사용법 안내
    print("\n💡 사용법:")
    print("   단일 실험: run_optimization(target_style='DWLG42044', scenario='extreme_coverage')")
    print("   배치 실험: run_batch_experiments(['DWLG42044'], ['baseline', 'extreme_coverage'])")
    print("   실험 목록: list_saved_experiments()")
    print("   다른 스타일: config.py에서 설정 변경 가능") 