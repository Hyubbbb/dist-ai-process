"""
2-Step vs 통합 MILP 방식 실제 성능 비교 실험
"""

import sys
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules import (
    DataLoader, StoreTierSystem, SKUClassifier, 
    IntegratedOptimizer, ResultAnalyzer,
    ResultVisualizer, ExperimentManager
)
from modules.two_step_optimizer import TwoStepOptimizer
from config import EXPERIMENT_SCENARIOS


class MethodComparisonExperiment:
    """두 가지 배분 방식의 실제 성능 비교 실험"""
    
    def __init__(self, target_style='DWLG42044'):
        self.target_style = target_style
        self.comparison_results = {}
        
    def setup_experiment_data(self):
        """실험용 데이터 준비"""
        print("📊 실험용 데이터 준비 중...")
        
        # 1. 데이터 로드
        data_loader = DataLoader()
        data_loader.load_data()
        data_loader.filter_by_style(self.target_style)
        data = data_loader.get_basic_data_structures()
        
        # 2. 매장 Tier 시스템 설정
        tier_system = StoreTierSystem()
        target_stores = tier_system.get_target_stores(data['stores'], self.target_style)
        store_allocation_limits = tier_system.create_store_allocation_limits(target_stores)
        
        # 3. SKU 분류
        sku_classifier = SKUClassifier(data_loader.df_sku_filtered)
        scarce_skus, abundant_skus = sku_classifier.classify_skus(data['A'], target_stores)
        
        return {
            'data': data,
            'data_loader': data_loader,
            'tier_system': tier_system,
            'target_stores': target_stores,
            'store_allocation_limits': store_allocation_limits,
            'scarce_skus': scarce_skus,
            'abundant_skus': abundant_skus
        }
    
    def run_integrated_milp_method(self, experiment_data, scenario_params):
        """통합 MILP 방식 실행"""
        print(f"\n🔧 통합 MILP 방식 실행 중...")
        
        start_time = time.time()
        
        # 통합 MILP 최적화
        integrated_optimizer = IntegratedOptimizer(self.target_style)
        
        optimization_result = integrated_optimizer.optimize_integrated(
            experiment_data['data'], 
            experiment_data['scarce_skus'], 
            experiment_data['abundant_skus'], 
            experiment_data['target_stores'],
            experiment_data['store_allocation_limits'], 
            experiment_data['data_loader'].df_sku_filtered,
            experiment_data['tier_system'], 
            scenario_params
        )
        
        total_time = time.time() - start_time
        
        if optimization_result['status'] == 'success':
            # 목적함수 분해 분석
            objective_breakdown = integrated_optimizer.get_objective_breakdown()
            
            return {
                'method': 'integrated_milp',
                'status': 'success',
                'total_time': total_time,
                'optimization_result': optimization_result,
                'objective_breakdown': objective_breakdown,
                'final_allocation': optimization_result['final_allocation']
            }
        else:
            return {
                'method': 'integrated_milp',
                'status': 'failed',
                'total_time': total_time,
                'error': optimization_result.get('problem_status', 'unknown')
            }
    
    def run_two_step_method(self, experiment_data, scenario_params):
        """2-Step 방식 실행"""
        print(f"\n📊 2-Step 방식 실행 중...")
        
        start_time = time.time()
        
        # 2-Step 최적화
        two_step_optimizer = TwoStepOptimizer(self.target_style)
        
        optimization_result = two_step_optimizer.optimize_two_step(
            experiment_data['data'], 
            experiment_data['scarce_skus'], 
            experiment_data['abundant_skus'], 
            experiment_data['target_stores'],
            experiment_data['store_allocation_limits'], 
            experiment_data['data_loader'].df_sku_filtered,
            experiment_data['tier_system'], 
            scenario_params
        )
        
        total_time = time.time() - start_time
        
        if optimization_result['status'] == 'success':
            # 단계별 분석
            step_analysis = two_step_optimizer.get_step_analysis()
            
            return {
                'method': '2_step',
                'status': 'success',
                'total_time': total_time,
                'optimization_result': optimization_result,
                'step_analysis': step_analysis,
                'final_allocation': optimization_result['final_allocation']
            }
        else:
            return {
                'method': '2_step',
                'status': 'failed',
                'total_time': total_time,
                'error': optimization_result.get('step', 'unknown')
            }
    
    def analyze_allocation_results(self, method_result, experiment_data):
        """배분 결과 분석"""
        if method_result['status'] != 'success':
            return None
        
        final_allocation = method_result['final_allocation']
        
        # ResultAnalyzer를 사용한 상세 분석
        analyzer = ResultAnalyzer(self.target_style)
        analysis_results = analyzer.analyze_results(
            final_allocation, 
            experiment_data['data'], 
            experiment_data['scarce_skus'], 
            experiment_data['abundant_skus'],
            experiment_data['target_stores'], 
            experiment_data['data_loader'].df_sku_filtered, 
            experiment_data['data']['QSUM'], 
            experiment_data['tier_system']
        )
        
        return analysis_results
    
    def compare_methods(self, scenario_name='baseline'):
        """두 방식 직접 비교"""
        print(f"🏆 방식별 성능 비교 실험 시작")
        print(f"   대상 스타일: {self.target_style}")
        print(f"   시나리오: {scenario_name}")
        print("="*60)
        
        # 1. 실험 데이터 준비
        experiment_data = self.setup_experiment_data()
        scenario_params = EXPERIMENT_SCENARIOS[scenario_name].copy()
        
        # 2. 통합 MILP 방식 실행
        integrated_result = self.run_integrated_milp_method(experiment_data, scenario_params)
        integrated_analysis = self.analyze_allocation_results(integrated_result, experiment_data)
        
        # 3. 2-Step 방식 실행
        two_step_result = self.run_two_step_method(experiment_data, scenario_params)
        two_step_analysis = self.analyze_allocation_results(two_step_result, experiment_data)
        
        # 4. 결과 비교 분석
        comparison = self._create_detailed_comparison(
            integrated_result, integrated_analysis,
            two_step_result, two_step_analysis,
            scenario_params
        )
        
        # 5. 결과 출력
        self._print_comparison_results(comparison)
        
        return comparison
    
    def _create_detailed_comparison(self, integrated_result, integrated_analysis,
                                  two_step_result, two_step_analysis, scenario_params):
        """상세 비교 분석 생성"""
        
        comparison = {
            'scenario': scenario_params,
            'timestamp': datetime.now(),
            'methods': {
                'integrated_milp': {
                    'result': integrated_result,
                    'analysis': integrated_analysis
                },
                '2_step': {
                    'result': two_step_result,
                    'analysis': two_step_analysis
                }
            }
        }
        
        # 성공한 방식들만 비교
        if integrated_result['status'] == 'success' and two_step_result['status'] == 'success':
            
            # 1. 성능 메트릭 비교
            comparison['performance_metrics'] = self._compare_performance_metrics(
                integrated_result, integrated_analysis,
                two_step_result, two_step_analysis
            )
            
            # 2. 계산 효율성 비교
            comparison['computational_efficiency'] = self._compare_computational_efficiency(
                integrated_result, two_step_result
            )
            
            # 3. 커버리지 비교
            comparison['coverage_comparison'] = self._compare_coverage(
                integrated_analysis, two_step_analysis
            )
            
            # 4. 배분 효율성 비교
            comparison['allocation_efficiency'] = self._compare_allocation_efficiency(
                integrated_result, two_step_result
            )
            
            # 5. 종합 평가
            comparison['overall_assessment'] = self._create_overall_assessment(comparison)
        
        return comparison
    
    def _compare_performance_metrics(self, integrated_result, integrated_analysis,
                                   two_step_result, two_step_analysis):
        """성능 메트릭 비교"""
        
        int_eval = integrated_analysis['overall_evaluation']
        ts_eval = two_step_analysis['overall_evaluation']
        
        return {
            'color_coverage': {
                'integrated_milp': int_eval['overall_color_coverage'],
                '2_step': ts_eval['overall_color_coverage'],
                'winner': 'integrated_milp' if int_eval['overall_color_coverage'] > ts_eval['overall_color_coverage'] else '2_step',
                'difference': abs(int_eval['overall_color_coverage'] - ts_eval['overall_color_coverage'])
            },
            'size_coverage': {
                'integrated_milp': int_eval['overall_size_coverage'],
                '2_step': ts_eval['overall_size_coverage'],
                'winner': 'integrated_milp' if int_eval['overall_size_coverage'] > ts_eval['overall_size_coverage'] else '2_step',
                'difference': abs(int_eval['overall_size_coverage'] - ts_eval['overall_size_coverage'])
            },
            'allocation_efficiency': {
                'integrated_milp': int_eval['overall_allocation_efficiency'],
                '2_step': ts_eval['overall_allocation_efficiency'],
                'winner': 'integrated_milp' if int_eval['overall_allocation_efficiency'] > ts_eval['overall_allocation_efficiency'] else '2_step',
                'difference': abs(int_eval['overall_allocation_efficiency'] - ts_eval['overall_allocation_efficiency'])
            },
            'total_score': {
                'integrated_milp': int_eval['total_score'],
                '2_step': ts_eval['total_score'],
                'winner': 'integrated_milp' if int_eval['total_score'] > ts_eval['total_score'] else '2_step',
                'difference': abs(int_eval['total_score'] - ts_eval['total_score'])
            }
        }
    
    def _compare_computational_efficiency(self, integrated_result, two_step_result):
        """계산 효율성 비교"""
        
        comparison = {
            'total_time': {
                'integrated_milp': integrated_result['total_time'],
                '2_step': two_step_result['total_time'],
                'winner': 'integrated_milp' if integrated_result['total_time'] < two_step_result['total_time'] else '2_step',
                'speedup': max(integrated_result['total_time'], two_step_result['total_time']) / min(integrated_result['total_time'], two_step_result['total_time'])
            }
        }
        
        # 2-Step 방식의 세부 시간 분석
        if '2_step' in two_step_result['method']:
            step_analysis = two_step_result.get('step_analysis', {})
            comparison['2_step_breakdown'] = {
                'step1_time': step_analysis.get('step1', {}).get('time', 0),
                'step2_time': step_analysis.get('step2', {}).get('time', 0),
                'step1_ratio': step_analysis.get('step1', {}).get('time', 0) / two_step_result['total_time'] if two_step_result['total_time'] > 0 else 0
            }
        
        return comparison
    
    def _compare_coverage(self, integrated_analysis, two_step_analysis):
        """커버리지 성능 비교"""
        
        int_style = integrated_analysis['style_coverage']
        ts_style = two_step_analysis['style_coverage']
        
        return {
            'color_coverage_detail': {
                'integrated_milp': {
                    'avg': int_style['color_coverage']['avg_ratio'],
                    'max': int_style['color_coverage']['max_ratio'],
                    'min': int_style['color_coverage']['min_ratio']
                },
                '2_step': {
                    'avg': ts_style['color_coverage']['avg_ratio'],
                    'max': ts_style['color_coverage']['max_ratio'],
                    'min': ts_style['color_coverage']['min_ratio']
                }
            },
            'size_coverage_detail': {
                'integrated_milp': {
                    'avg': int_style['size_coverage']['avg_ratio'],
                    'max': int_style['size_coverage']['max_ratio'],
                    'min': int_style['size_coverage']['min_ratio']
                },
                '2_step': {
                    'avg': ts_style['size_coverage']['avg_ratio'],
                    'max': ts_style['size_coverage']['max_ratio'],
                    'min': ts_style['size_coverage']['min_ratio']
                }
            }
        }
    
    def _compare_allocation_efficiency(self, integrated_result, two_step_result):
        """배분 효율성 비교"""
        
        int_opt = integrated_result['optimization_result']
        ts_opt = two_step_result['optimization_result']
        
        return {
            'allocation_rate': {
                'integrated_milp': int_opt['allocation_rate'],
                '2_step': ts_opt['allocation_rate'],
                'winner': 'integrated_milp' if int_opt['allocation_rate'] > ts_opt['allocation_rate'] else '2_step',
                'difference': abs(int_opt['allocation_rate'] - ts_opt['allocation_rate'])
            },
            'total_allocated': {
                'integrated_milp': int_opt['total_allocated'],
                '2_step': ts_opt['total_allocated'],
                'winner': 'integrated_milp' if int_opt['total_allocated'] > ts_opt['total_allocated'] else '2_step',
                'difference': abs(int_opt['total_allocated'] - ts_opt['total_allocated'])
            },
            'allocated_stores': {
                'integrated_milp': int_opt['allocated_stores'],
                '2_step': ts_opt['allocated_stores'],
                'winner': 'integrated_milp' if int_opt['allocated_stores'] > ts_opt['allocated_stores'] else '2_step',
                'difference': abs(int_opt['allocated_stores'] - ts_opt['allocated_stores'])
            }
        }
    
    def _create_overall_assessment(self, comparison):
        """종합 평가 생성"""
        
        perf_metrics = comparison['performance_metrics']
        comp_eff = comparison['computational_efficiency']
        alloc_eff = comparison['allocation_efficiency']
        
        # 승리 횟수 계산
        integrated_wins = 0
        two_step_wins = 0
        
        for metric in perf_metrics.values():
            if metric['winner'] == 'integrated_milp':
                integrated_wins += 1
            else:
                two_step_wins += 1
        
        for metric in alloc_eff.values():
            if metric['winner'] == 'integrated_milp':
                integrated_wins += 1
            else:
                two_step_wins += 1
        
        # 시간 효율성
        if comp_eff['total_time']['winner'] == 'integrated_milp':
            integrated_wins += 1
        else:
            two_step_wins += 1
        
        # 종합 판정
        if integrated_wins > two_step_wins:
            overall_winner = 'integrated_milp'
            strength = 'comprehensive optimization'
        elif two_step_wins > integrated_wins:
            overall_winner = '2_step'
            strength = 'coverage priority and flexibility'
        else:
            overall_winner = 'tie'
            strength = 'context dependent'
        
        return {
            'overall_winner': overall_winner,
            'integrated_wins': integrated_wins,
            '2_step_wins': two_step_wins,
            'key_strength': strength,
            'speedup_factor': comp_eff['total_time']['speedup'],
            'coverage_gap': max(
                perf_metrics['color_coverage']['difference'],
                perf_metrics['size_coverage']['difference']
            ),
            'allocation_gap': alloc_eff['allocation_rate']['difference']
        }
    
    def _print_comparison_results(self, comparison):
        """비교 결과 출력"""
        
        print(f"\n🏆 방식별 성능 비교 결과")
        print("="*60)
        
        if 'performance_metrics' not in comparison:
            print("❌ 한 쪽 이상의 방식이 실패하여 비교할 수 없습니다.")
            return
        
        perf = comparison['performance_metrics']
        comp = comparison['computational_efficiency']
        alloc = comparison['allocation_efficiency']
        overall = comparison['overall_assessment']
        
        print(f"📊 성능 메트릭 비교:")
        print(f"   색상 커버리지: 통합 {perf['color_coverage']['integrated_milp']:.3f} vs 2-Step {perf['color_coverage']['2_step']:.3f} ({'승리: ' + perf['color_coverage']['winner']})")
        print(f"   사이즈 커버리지: 통합 {perf['size_coverage']['integrated_milp']:.3f} vs 2-Step {perf['size_coverage']['2_step']:.3f} ({'승리: ' + perf['size_coverage']['winner']})")
        print(f"   배분 효율성: 통합 {perf['allocation_efficiency']['integrated_milp']:.4f} vs 2-Step {perf['allocation_efficiency']['2_step']:.4f} ({'승리: ' + perf['allocation_efficiency']['winner']})")
        print(f"   종합 점수: 통합 {perf['total_score']['integrated_milp']:.3f} vs 2-Step {perf['total_score']['2_step']:.3f} ({'승리: ' + perf['total_score']['winner']})")
        
        print(f"\n⏱️ 계산 효율성:")
        print(f"   실행 시간: 통합 {comp['total_time']['integrated_milp']:.2f}초 vs 2-Step {comp['total_time']['2_step']:.2f}초")
        print(f"   속도 우위: {comp['total_time']['winner']} ({comp['total_time']['speedup']:.1f}배 빠름)")
        
        if '2_step_breakdown' in comp:
            breakdown = comp['2_step_breakdown']
            print(f"   2-Step 세부: Step1 {breakdown['step1_time']:.2f}초 ({breakdown['step1_ratio']:.1%}), Step2 {breakdown['step2_time']:.2f}초")
        
        print(f"\n📦 배분 성과:")
        print(f"   배분률: 통합 {alloc['allocation_rate']['integrated_milp']:.1%} vs 2-Step {alloc['allocation_rate']['2_step']:.1%} ({'승리: ' + alloc['allocation_rate']['winner']})")
        print(f"   총 배분량: 통합 {alloc['total_allocated']['integrated_milp']:,}개 vs 2-Step {alloc['total_allocated']['2_step']:,}개")
        print(f"   배분 매장수: 통합 {alloc['allocated_stores']['integrated_milp']}개 vs 2-Step {alloc['allocated_stores']['2_step']}개")
        
        print(f"\n🏆 종합 평가:")
        print(f"   전체 승자: {overall['overall_winner']}")
        print(f"   승리 점수: 통합 MILP {overall['integrated_wins']}승 vs 2-Step {overall['2_step_wins']}승")
        print(f"   핵심 강점: {overall['key_strength']}")
        print(f"   속도 차이: {overall['speedup_factor']:.1f}배")
        print(f"   커버리지 격차: 최대 {overall['coverage_gap']:.3f}")
        print(f"   배분률 격차: {overall['allocation_gap']:.1%}")
        
        # 권장사항
        print(f"\n💡 권장사항:")
        if overall['overall_winner'] == 'integrated_milp':
            print(f"   ✅ 통합 MILP 방식 권장")
            print(f"   - 종합적 최적화 성능 우수")
            print(f"   - 수학적 최적성 보장")
        elif overall['overall_winner'] == '2_step':
            print(f"   ✅ 2-Step 방식 권장")
            print(f"   - 커버리지 우선순위 명확")
            print(f"   - 유연한 룰 적용 가능")
        else:
            print(f"   ⚖️ 상황에 따른 선택 권장")
            print(f"   - 커버리지 절대 우선: 2-Step")
            print(f"   - 복합 최적화 필요: 통합 MILP")


if __name__ == "__main__":
    # 비교 실험 실행
    experiment = MethodComparisonExperiment()
    
    print("🚀 2-Step vs 통합 MILP 성능 비교 실험")
    print("="*50)
    
    # 여러 시나리오로 비교
    scenarios_to_test = ['baseline', 'balance_focused', 'equity_focused']
    
    for scenario in scenarios_to_test:
        print(f"\n{'='*70}")
        print(f"시나리오: {scenario}")
        print(f"{'='*70}")
        
        try:
            comparison_result = experiment.compare_methods(scenario)
            # 필요하면 결과를 파일로 저장
            
        except Exception as e:
            print(f"❌ {scenario} 시나리오 실험 실패: {e}")
            continue
    
    print(f"\n🎉 모든 비교 실험 완료!") 