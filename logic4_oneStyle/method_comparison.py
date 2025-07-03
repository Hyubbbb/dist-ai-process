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
    IntegratedOptimizer, ResultAnalyzer
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
        
        # 3. 2-Step 방식 실행
        two_step_result = self.run_two_step_method(experiment_data, scenario_params)
        
        # 4. 결과 비교 출력
        self._print_comparison_results(integrated_result, two_step_result)
        
        return {
            'integrated_result': integrated_result,
            'two_step_result': two_step_result,
            'experiment_data': experiment_data
        }
    
    def _print_comparison_results(self, integrated_result, two_step_result):
        """비교 결과 출력"""
        
        print(f"\n🏆 방식별 성능 비교 결과")
        print("="*60)
        
        if integrated_result['status'] == 'success' and two_step_result['status'] == 'success':
            
            int_opt = integrated_result['optimization_result']
            ts_opt = two_step_result['optimization_result']
            
            print(f"📊 최적화 성공 - 두 방식 모두 성공")
            print(f"\n⏱️ 계산 시간:")
            print(f"   통합 MILP: {integrated_result['total_time']:.2f}초")
            print(f"   2-Step: {two_step_result['total_time']:.2f}초")
            
            if 'step_analysis' in two_step_result:
                step = two_step_result['step_analysis']
                print(f"   2-Step 세부: Step1 {step['step1']['time']:.2f}초 + Step2 {step['step2']['time']:.2f}초")
            
            speedup = integrated_result['total_time'] / two_step_result['total_time']
            if speedup > 1:
                print(f"   ✅ 2-Step이 {speedup:.1f}배 빠름")
            else:
                print(f"   ✅ 통합 MILP가 {1/speedup:.1f}배 빠름")
            
            print(f"\n📦 배분 성과:")
            print(f"   총 배분량: 통합 {int_opt['total_allocated']:,}개 vs 2-Step {ts_opt['total_allocated']:,}개")
            print(f"   배분률: 통합 {int_opt['allocation_rate']:.1%} vs 2-Step {ts_opt['allocation_rate']:.1%}")
            print(f"   배분 매장수: 통합 {int_opt['allocated_stores']}개 vs 2-Step {ts_opt['allocated_stores']}개")
            
            # 2-Step 세부 정보
            if 'step1_combinations' in ts_opt and 'step2_additional' in ts_opt:
                print(f"\n🔄 2-Step 세부 분석:")
                print(f"   Step1 선택 조합: {ts_opt['step1_combinations']}개")
                print(f"   Step1 커버리지: {ts_opt['step1_objective']:.1f}")
                print(f"   Step2 추가 배분: {ts_opt['step2_additional']}개")
            
            # 승자 판정
            if int_opt['allocation_rate'] > ts_opt['allocation_rate']:
                print(f"\n🏆 배분 효율성 승자: 통합 MILP")
            elif ts_opt['allocation_rate'] > int_opt['allocation_rate']:
                print(f"\n🏆 배분 효율성 승자: 2-Step")
            else:
                print(f"\n🏆 배분 효율성: 무승부")
            
            # 객관적 평가
            print(f"\n💡 객관적 평가:")
            
            # 계산 복잡성
            if two_step_result['total_time'] < integrated_result['total_time']:
                print(f"   ✅ 계산 효율성: 2-Step 우수 ({speedup:.1f}배 빠름)")
            else:
                print(f"   ✅ 계산 효율성: 통합 MILP 우수 ({1/speedup:.1f}배 빠름)")
            
            # 배분 품질
            if int_opt['total_allocated'] > ts_opt['total_allocated']:
                print(f"   ✅ 배분 품질: 통합 MILP 우수 ({int_opt['total_allocated'] - ts_opt['total_allocated']}개 더 배분)")
            elif ts_opt['total_allocated'] > int_opt['total_allocated']:
                print(f"   ✅ 배분 품질: 2-Step 우수 ({ts_opt['total_allocated'] - int_opt['total_allocated']}개 더 배분)")
            else:
                print(f"   ✅ 배분 품질: 동일함")
            
            # 커버리지 특성
            if 'step1_objective' in ts_opt:
                print(f"   📊 커버리지 특성: 2-Step은 순수 커버리지 {ts_opt['step1_objective']:.1f} 달성")
            
            # 최적화 특성
            if 'objective_breakdown' in integrated_result:
                obj = integrated_result['objective_breakdown']
                print(f"   🎯 통합 MILP 목적함수:")
                print(f"      커버리지: {obj.get('coverage_term', 0):.1f}")
                print(f"      공평성: {obj.get('equity_term', 0):.3f}")
                print(f"      효율성: {obj.get('efficiency_term', 0):.3f}")
                print(f"      배분량: {obj.get('allocation_term', 0):.1f}")
            
        else:
            print(f"❌ 최적화 실패")
            if integrated_result['status'] != 'success':
                print(f"   통합 MILP 실패: {integrated_result.get('error', 'unknown')}")
            if two_step_result['status'] != 'success':
                print(f"   2-Step 실패: {two_step_result.get('error', 'unknown')}")


if __name__ == "__main__":
    # 비교 실험 실행
    experiment = MethodComparisonExperiment()
    
    print("🚀 2-Step vs 통합 MILP 성능 비교 실험")
    print("="*50)
    
    # 기본 시나리오로 비교
    try:
        comparison_result = experiment.compare_methods('baseline')
        print(f"\n🎉 비교 실험 완료!")
        
    except Exception as e:
        print(f"❌ 실험 실패: {e}")
        import traceback
        traceback.print_exc() 