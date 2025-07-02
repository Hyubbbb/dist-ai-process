"""
SKU 최적화 엔진 모듈

이 모듈은 2단계 최적화 로직을 구현합니다:
1. Step1: Coverage MILP - 희소 SKU 커버리지 최적화
2. Step2: Quantity ILP - 전체 SKU 수량 최적화
"""

import time
import pandas as pd
from pulp import (
    LpProblem, LpVariable, LpBinary, LpInteger, LpContinuous,
    LpMaximize, lpSum, PULP_CBC_CMD
)
from typing import Dict, List, Any, Tuple, Optional
import logging
import numpy as np


class SKUOptimizer:
    """SKU 분배 최적화 엔진"""
    
    def __init__(self, data: Dict[str, Any]):
        """
        최적화 엔진 초기화
        
        Args:
            data: 전처리된 데이터 딕셔너리
        """
        self.data = data
        self.logger = logging.getLogger(__name__)
        
        # 데이터 추출
        self.df_sku = data['df_sku']
        self.df_store = data['df_store']
        self.A = data['A']  # SKU별 공급량
        self.SKUs = data['SKUs']
        self.stores = data['stores']
        self.QSUM = data['QSUM']  # 매장별 판매량
        self.scarce = data['scarce']
        self.abundant = data['abundant']
        self.styles = data['styles']
        self.I_s = data['I_s']  # 스타일별 SKU 그룹
        self.K_s = data['K_s']  # 스타일별 색상 그룹
        self.L_s = data['L_s']  # 스타일별 사이즈 그룹
        
        # 최적화 결과 저장
        self.step1_result = None
        self.step2_result = None
        self.b_hat = {}  # Step1 결과
        self.x_result = {}  # Step2 결과
    
    def optimize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        전체 최적화 수행 (Step1 + Step2)
        
        Args:
            params: 실험 파라미터
            
        Returns:
            Dict[str, Any]: 최적화 결과
        """
        start_time = time.time()
        
        try:
            # Step1: Coverage MILP
            self.logger.info("Step1 최적화 시작...")
            step1_timeout = params.get('step1_timeout', 300)  # 기본 5분
            self.step1_result = self._solve_step1(step1_timeout)
            
            if self.step1_result['status'] != 'Optimal':
                return {
                    'status': 'failed',
                    'step': 1,
                    'message': 'Step1 최적화 실패',
                    'execution_time': time.time() - start_time
                }
            
            # Step2: Quantity ILP
            self.logger.info("Step2 최적화 시작...")
            step2_timeout = params.get('step2_timeout', 600)  # 기본 10분
            self.step2_result = self._solve_step2(params, step2_timeout)
            
            if self.step2_result['status'] != 'Optimal':
                return {
                    'status': 'failed',
                    'step': 2,
                    'message': 'Step2 최적화 실패',
                    'execution_time': time.time() - start_time
                }
            
            # 성공적으로 완료
            execution_time = time.time() - start_time
            self.logger.info(f"최적화 완료 (실행 시간: {execution_time:.2f}초)")
            
            return {
                'status': 'success',
                'step1_result': self.step1_result,
                'step2_result': self.step2_result,
                'objective_value': self.step2_result['objective_value'],
                'execution_time': execution_time
            }
            
        except Exception as e:
            self.logger.error(f"최적화 중 오류 발생: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'execution_time': time.time() - start_time
            }
    
    def _solve_step1(self, timeout: int) -> Dict[str, Any]:
        """Step1: Coverage MILP 해결"""
        prob1 = LpProblem('Step1_Coverage', LpMaximize)
        
        # 변수 정의
        b = LpVariable.dicts('b', (self.scarce, self.stores), cat=LpBinary)
        
        # 커버리지 변수
        color_coverage = {
            (s, j): LpVariable(f"color_coverage_{s}_{j}", 
                              lowBound=0, upBound=len(self.K_s[s]), cat=LpInteger)
            for s in self.styles for j in self.stores
        }
        
        size_coverage = {
            (s, j): LpVariable(f"size_coverage_{s}_{j}", 
                              lowBound=0, upBound=len(self.L_s[s]), cat=LpInteger)
            for s in self.styles for j in self.stores
        }
        
        # 목적함수
        epsilon = 0.001
        prob1 += (
            lpSum(color_coverage[s, j] for s in self.styles for j in self.stores) +
            lpSum(size_coverage[s, j] for s in self.styles for j in self.stores) +
            epsilon * lpSum(b[i][j] for i in self.scarce for j in self.stores)
        )
        
        # 제약조건
        # 1) 희소 SKU 공급량 제한
        for i in self.scarce:
            prob1 += lpSum(b[i][j] for j in self.stores) <= self.A[i]
        
        # 2) 색상 커버리지 제약조건
        for s in self.styles:
            for j in self.stores:
                color_covered = {}
                for k in self.K_s[s]:
                    color_covered[k] = LpVariable(f"color_covered_{s}_{k}_{j}", cat=LpBinary)
                    
                    idx_color = [i for i in self.I_s[s] 
                               if (self.df_sku.loc[self.df_sku['SKU']==i, 'COLOR_CD'].iloc[0] == k 
                                   and i in self.scarce)]
                    
                    if idx_color:
                        prob1 += lpSum(b[i][j] for i in idx_color) >= color_covered[k]
                        for i in idx_color:
                            prob1 += b[i][j] <= color_covered[k]
                    else:
                        prob1 += color_covered[k] == 0
                
                prob1 += color_coverage[s, j] == lpSum(color_covered[k] for k in self.K_s[s])
        
        # 3) 사이즈 커버리지 제약조건
        for s in self.styles:
            for j in self.stores:
                size_covered = {}
                for l in self.L_s[s]:
                    size_covered[l] = LpVariable(f"size_covered_{s}_{l}_{j}", cat=LpBinary)
                    
                    idx_size = [i for i in self.I_s[s] 
                              if (self.df_sku.loc[self.df_sku['SKU']==i, 'SIZE_CD'].iloc[0] == l 
                                  and i in self.scarce)]
                    
                    if idx_size:
                        prob1 += lpSum(b[i][j] for i in idx_size) >= size_covered[l]
                        for i in idx_size:
                            prob1 += b[i][j] <= size_covered[l]
                    else:
                        prob1 += size_covered[l] == 0
                
                prob1 += size_coverage[s, j] == lpSum(size_covered[l] for l in self.L_s[s])
        
        # 최적화 실행
        prob1.solve(PULP_CBC_CMD(msg=False, timeLimit=timeout))
        
        # 결과 저장
        if prob1.status == 1:  # Optimal
            self.b_hat = {}
            for i in self.scarce:
                for j in self.stores:
                    if b[i][j].value() and b[i][j].value() > 0.5:
                        self.b_hat[(i, j)] = 1
                    else:
                        self.b_hat[(i, j)] = 0
            
            return {
                'status': 'Optimal',
                'objective_value': prob1.objective.value(),
                'assignments': sum(self.b_hat.values())
            }
        else:
            return {
                'status': 'Failed',
                'status_code': prob1.status
            }
    
    def _solve_step2(self, params: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Step2: Quantity ILP 해결"""
        prob2 = LpProblem('Step2_Quantity', LpMaximize)
        
        # 변수 정의
        x = LpVariable.dicts('x', (self.SKUs, self.stores), lowBound=0, cat=LpInteger)
        
        # 매장 가중치
        total_qty = sum(self.QSUM.values())
        w = {j: self.QSUM[j] / total_qty for j in self.stores}
        
        # 커버리지 변수 (Step2용)
        step2_color_coverage = {
            (s, j): LpVariable(f"step2_color_coverage_{s}_{j}", 
                              lowBound=0, upBound=len(self.K_s[s]), cat=LpInteger)
            for s in self.styles for j in self.stores
        }
        
        step2_size_coverage = {
            (s, j): LpVariable(f"step2_size_coverage_{s}_{j}", 
                              lowBound=0, upBound=len(self.L_s[s]), cat=LpInteger)
            for s in self.styles for j in self.stores
        }
        
        # 균형 변수들
        coverage_balance = {
            (s, j): LpVariable(f"coverage_balance_{s}_{j}", lowBound=0, cat=LpContinuous)
            for s in self.styles for j in self.stores
        }
        
        total_allocation = {
            j: LpVariable(f"total_allocation_{j}", lowBound=0, cat=LpInteger) 
            for j in self.stores
        }
        
        allocation_deviation = {
            j: LpVariable(f"allocation_deviation_{j}", lowBound=0, cat=LpContinuous) 
            for j in self.stores
        }
        
        # SKU 분산 제약을 위한 변수들
        sku_distribution_deviation = {
            i: LpVariable(f"sku_distribution_deviation_{i}", lowBound=0, cat=LpContinuous)
            for i in self.SKUs
        }
        
        # 목적함수
        total_items = sum(self.A.values())
        
        # SKU 분산 페널티 가중치 (기본값 추가)
        sku_distribution_penalty = params.get('sku_distribution_penalty', 0.5)
        
        prob2 += (
            lpSum(w[j] * x[i][j] for i in self.SKUs for j in self.stores) +
            params['coverage_weight'] * lpSum(
                step2_color_coverage[s, j] + step2_size_coverage[s, j] 
                for s in self.styles for j in self.stores
            ) +
            -params['balance_penalty'] * lpSum(
                coverage_balance[s, j] for s in self.styles for j in self.stores
            ) +
            -params['allocation_penalty'] * lpSum(
                allocation_deviation[j] for j in self.stores
            ) +
            -sku_distribution_penalty * lpSum(
                sku_distribution_deviation[i] for i in self.SKUs
            )
        )
        
        # 제약조건
        # 1) SKU 공급량 완전 소진
        for i in self.SKUs:
            prob2 += lpSum(x[i][j] for j in self.stores) == self.A[i]
        
        # 2) Step1 커버리지 보장
        for (i, j), val in self.b_hat.items():
            if val == 1:
                prob2 += x[i][j] >= 1
        
        # 3) 매장별 총 배분량 계산
        for j in self.stores:
            prob2 += total_allocation[j] == lpSum(x[i][j] for i in self.SKUs)
        
        # 4) 배분량 비례 제약조건
        for j in self.stores:
            expected_allocation = w[j] * total_items
            prob2 += allocation_deviation[j] >= total_allocation[j] - expected_allocation
            prob2 += allocation_deviation[j] >= expected_allocation - total_allocation[j]
            
            prob2 += total_allocation[j] >= params['allocation_range_min'] * expected_allocation
            prob2 += total_allocation[j] <= params['allocation_range_max'] * expected_allocation
        
        # 5) QTY_SUM 기반 비례 배분 제약 (새로운 접근법 - 수렴성 개선)
        use_proportional_allocation = params.get('use_proportional_allocation', True)
        
        if use_proportional_allocation:
            # 매장별 비율 계산 (QTY_SUM 기반)
            total_qsum = sum(self.QSUM.values())
            store_ratios = {j: self.QSUM[j] / total_qsum for j in self.stores}
            
            # 배분 범위 승수 (더 관대한 기본값)
            min_allocation_multiplier = params.get('min_allocation_multiplier', 0.1)  # 0.5 → 0.1
            max_allocation_multiplier = params.get('max_allocation_multiplier', 3.0)  # 1.5 → 3.0
            
            self.logger.info(f"QTY_SUM 기반 비례 배분 제약 적용: {min_allocation_multiplier:.1f}x ~ {max_allocation_multiplier:.1f}x")
            
            # 각 SKU의 매장별 기대 배분량 계산 및 제약 적용 (더 유연하게)
            for i in self.SKUs:
                for j in self.stores:
                    # 기대 배분량 = SKU 총량 × 매장 비율
                    expected_allocation = self.A[i] * store_ratios[j]
                    
                    # 최소 할당량 보장 (1개 이상)
                    min_expected = max(min_allocation_multiplier * expected_allocation, 0.1)
                    max_expected = min(max_allocation_multiplier * expected_allocation, self.A[i])
                    
                    # 비례 배분 범위 제약 (실행 가능성 확보)
                    if min_expected <= max_expected:
                        prob2 += x[i][j] >= min_expected
                        prob2 += x[i][j] <= max_expected
                    else:
                        # 제약 충돌 시 완화
                        prob2 += x[i][j] <= self.A[i]
        
        else:
            # 기존 MAX_SKU_CONCENTRATION 방식 (백업용)
            max_sku_concentration = params.get('max_sku_concentration', 0.9)
            for i in self.SKUs:
                for j in self.stores:
                    prob2 += x[i][j] <= max_sku_concentration * self.A[i]
        
        # 5-1) 희소 SKU에 대한 추가 분산 제약 (조건부 적용)
        enforce_scarce_distribution = params.get('enforce_scarce_distribution', False)  # 기본값 false로 변경
        if enforce_scarce_distribution and use_proportional_allocation:
            scarce_min_multiplier = params.get('scarce_min_allocation_multiplier', 0.05)  # 0.3 → 0.05
            scarce_max_multiplier = params.get('scarce_max_allocation_multiplier', 5.0)   # 1.2 → 5.0
            
            total_qsum = sum(self.QSUM.values())
            store_ratios = {j: self.QSUM[j] / total_qsum for j in self.stores}
            
            self.logger.info(f"희소 SKU 분산 제약 적용: {scarce_min_multiplier:.2f}x ~ {scarce_max_multiplier:.1f}x")
            
            for i in self.scarce:
                for j in self.stores:
                    expected_allocation = self.A[i] * store_ratios[j]
                    min_scarce = max(scarce_min_multiplier * expected_allocation, 0.05)
                    max_scarce = min(scarce_max_multiplier * expected_allocation, self.A[i])
                    
                    # 희소 SKU는 더 관대한 분산 제약
                    if min_scarce <= max_scarce:
                        prob2 += x[i][j] >= min_scarce
                        prob2 += x[i][j] <= max_scarce
        
        # 5-2) 매장 크기별 차등 제약 (조건부 적용)
        apply_store_size_constraints = params.get('apply_store_size_constraints', False)
        if apply_store_size_constraints and use_proportional_allocation:
            # 큰 매장/작은 매장 구분
            median_qsum = np.median(list(self.QSUM.values()))
            large_stores = [j for j in self.stores if self.QSUM[j] >= median_qsum]
            small_stores = [j for j in self.stores if self.QSUM[j] < median_qsum]
            
            large_store_max_multiplier = params.get('large_store_max_multiplier', 5.0)  # 2.0 → 5.0
            small_store_max_multiplier = params.get('small_store_max_multiplier', 3.0)  # 1.2 → 3.0
            
            total_qsum = sum(self.QSUM.values())
            store_ratios = {j: self.QSUM[j] / total_qsum for j in self.stores}
            
            self.logger.info(f"매장 크기별 차등 제약 적용 - 대형: {large_store_max_multiplier:.1f}x, 소형: {small_store_max_multiplier:.1f}x")
            
            # 큰 매장은 더 많은 변동 허용
            for i in self.SKUs:
                for j in large_stores:
                    expected_allocation = self.A[i] * store_ratios[j]
                    max_large = min(large_store_max_multiplier * expected_allocation, self.A[i])
                    prob2 += x[i][j] <= max_large
                
                for j in small_stores:
                    expected_allocation = self.A[i] * store_ratios[j]
                    max_small = min(small_store_max_multiplier * expected_allocation, self.A[i])
                    prob2 += x[i][j] <= max_small
        
        # 6) SKU 분산 제약 (QTY_SUM 기반으로 수정 - 옵션)
        apply_sku_distribution_penalty = params.get('sku_distribution_penalty', 0) > 0
        if apply_sku_distribution_penalty:
            for i in self.SKUs:
                total_qsum = sum(self.QSUM.values())
                for j in self.stores:
                    # QTY_SUM 기반 기대 배분량 계산
                    expected_sku_allocation = (self.QSUM[j] / total_qsum) * self.A[i]
                    prob2 += sku_distribution_deviation[i] >= x[i][j] - expected_sku_allocation
                    prob2 += sku_distribution_deviation[i] >= expected_sku_allocation - x[i][j]
        
        # 7) 최소 배분 보장 (조건부 적용)
        apply_min_allocation = params.get('min_allocation_per_store', 0) > 0
        if apply_min_allocation:
            min_allocation_per_store = params.get('min_allocation_per_store', 1)
            min_stores_per_sku = params.get('min_stores_per_sku', 2)
            
            self.logger.info(f"최소 배분 보장: 매장당 {min_allocation_per_store}개, SKU당 {min_stores_per_sku}개 매장")
            
            for i in self.SKUs:
                if self.A[i] >= len(self.stores) * min_allocation_per_store:  # 충분한 수량이 있는 경우만
                    # 최소 N개 매장에는 배분되도록 보장
                    effective_min_stores = min(min_stores_per_sku, len(self.stores), int(self.A[i] / min_allocation_per_store))
                    
                    if effective_min_stores > 0:
                        # 이진 변수: 매장 j에 SKU i가 배분되는지 여부
                        y_allocation = LpVariable.dicts(f'y_allocation_{i}', self.stores, cat=LpBinary)
                        
                        for j in self.stores:
                            # x[i][j] > 0이면 y_allocation[i][j] = 1
                            prob2 += x[i][j] <= self.A[i] * y_allocation[j]
                            prob2 += x[i][j] >= y_allocation[j] * min_allocation_per_store
                        
                        # 최소 매장 수 제약
                        prob2 += lpSum(y_allocation[j] for j in self.stores) >= effective_min_stores
        
        # 8) 색상/사이즈 커버리지 제약조건 (Step2)
        self._add_step2_coverage_constraints(prob2, x, step2_color_coverage, step2_size_coverage)
        
        # 9) 커버리지 균형 제약조건
        for s in self.styles:
            for j in self.stores:
                prob2 += coverage_balance[s, j] >= step2_color_coverage[s, j] - step2_size_coverage[s, j]
                prob2 += coverage_balance[s, j] >= step2_size_coverage[s, j] - step2_color_coverage[s, j]
        
        # 10) 최소 커버리지 보장
        if params['min_coverage_threshold'] > 0:
            for s in self.styles:
                for j in self.stores:
                    prob2 += step2_color_coverage[s, j] >= params['min_coverage_threshold'] * len(self.K_s[s])
                    prob2 += step2_size_coverage[s, j] >= params['min_coverage_threshold'] * len(self.L_s[s])
        
        # 최적화 실행
        prob2.solve(PULP_CBC_CMD(msg=False, timeLimit=timeout))
        
        # 결과 저장 및 상세 상태 정보 로깅
        status_messages = {
            1: "Optimal",
            0: "Not Solved", 
            -1: "Infeasible (실행 불가능한 해)",
            -2: "Unbounded (무제한)",
            -3: "Undefined (정의되지 않음)"
        }
        
        status_msg = status_messages.get(prob2.status, f"Unknown status: {prob2.status}")
        self.logger.info(f"Step2 최적화 상태: {status_msg} (코드: {prob2.status})")
        
        if prob2.status == 1:  # Optimal
            self.x_result = {}
            for i in self.SKUs:
                for j in self.stores:
                    value = int(x[i][j].value()) if x[i][j].value() else 0
                    if value > 0:
                        self.x_result[(i, j)] = value
            
            return {
                'status': 'Optimal',
                'objective_value': prob2.objective.value(),
                'total_allocations': len(self.x_result)
            }
        else:
            # 실패 원인 상세 분석
            failure_analysis = self._analyze_step2_failure(prob2, params)
            
            self.logger.error(f"Step2 최적화 실패: {status_msg}")
            self.logger.error(f"실패 분석: {failure_analysis}")
            
            return {
                'status': 'Failed',
                'status_code': prob2.status,
                'status_message': status_msg,
                'failure_analysis': failure_analysis
            }
    
    def _add_step2_coverage_constraints(self, prob2, x, step2_color_coverage, step2_size_coverage):
        """Step2 커버리지 제약조건 추가"""
        # 색상 커버리지
        for s in self.styles:
            for j in self.stores:
                step2_color_covered = {}
                for k in self.K_s[s]:
                    step2_color_covered[k] = LpVariable(f"step2_color_covered_{s}_{k}_{j}", cat=LpBinary)
                    
                    idx_color = [i for i in self.I_s[s] 
                               if self.df_sku.loc[self.df_sku['SKU']==i, 'COLOR_CD'].iloc[0] == k]
                    
                    if idx_color:
                        prob2 += lpSum(x[i][j] for i in idx_color) >= step2_color_covered[k]
                        for i in idx_color:
                            prob2 += x[i][j] <= self.A[i] * step2_color_covered[k]
                    else:
                        prob2 += step2_color_covered[k] == 0
                
                prob2 += step2_color_coverage[s, j] == lpSum(step2_color_covered[k] for k in self.K_s[s])
        
        # 사이즈 커버리지
        for s in self.styles:
            for j in self.stores:
                step2_size_covered = {}
                for l in self.L_s[s]:
                    step2_size_covered[l] = LpVariable(f"step2_size_covered_{s}_{l}_{j}", cat=LpBinary)
                    
                    idx_size = [i for i in self.I_s[s] 
                              if self.df_sku.loc[self.df_sku['SKU']==i, 'SIZE_CD'].iloc[0] == l]
                    
                    if idx_size:
                        prob2 += lpSum(x[i][j] for i in idx_size) >= step2_size_covered[l]
                        for i in idx_size:
                            prob2 += x[i][j] <= self.A[i] * step2_size_covered[l]
                    else:
                        prob2 += step2_size_covered[l] == 0
                
                prob2 += step2_size_coverage[s, j] == lpSum(step2_size_covered[l] for l in self.L_s[s])
    
    def _analyze_step2_failure(self, prob2, params: Dict[str, Any]) -> Dict[str, Any]:
        """Step2 실패 원인 분석"""
        analysis = {
            'constraint_summary': {},
            'parameter_analysis': {},
            'recommendations': []
        }
        
        try:
            # 1. 제약조건 수 카운트
            total_constraints = len(prob2.constraints)
            total_variables = len(prob2.variables())
            
            analysis['constraint_summary'] = {
                'total_constraints': total_constraints,
                'total_variables': total_variables,
                'constraint_to_variable_ratio': total_constraints / total_variables if total_variables > 0 else 0
            }
            
            # 2. 핵심 파라미터 분석
            use_proportional = params.get('use_proportional_allocation', True)
            min_mult = params.get('min_allocation_multiplier', 0.1)
            max_mult = params.get('max_allocation_multiplier', 3.0)
            
            analysis['parameter_analysis'] = {
                'use_proportional_allocation': use_proportional,
                'min_allocation_multiplier': min_mult,
                'max_allocation_multiplier': max_mult,
                'allocation_range_min': params.get('allocation_range_min', 0.1),
                'allocation_range_max': params.get('allocation_range_max', 10.0),
                'enforce_scarce_distribution': params.get('enforce_scarce_distribution', False),
                'apply_store_size_constraints': params.get('apply_store_size_constraints', False),
                'min_allocation_per_store': params.get('min_allocation_per_store', 0)
            }
            
            # 3. 가능한 원인 및 권장사항
            if prob2.status == -1:  # Infeasible
                analysis['recommendations'].extend([
                    "제약조건이 너무 엄격하여 실행 가능한 해가 없습니다.",
                    f"min_allocation_multiplier ({min_mult})를 더 낮추거나 max_allocation_multiplier ({max_mult})를 더 높이세요.",
                    "allocation_range_min을 더 낮추고 allocation_range_max를 더 높이세요.",
                    "enforce_scarce_distribution을 false로 설정하세요.",
                    "apply_store_size_constraints를 false로 설정하세요.",
                    "min_allocation_per_store를 0으로 설정하세요."
                ])
                
                # 데이터 기반 분석
                total_supply = sum(self.A.values())
                total_demand_capacity = sum(self.QSUM.values())
                supply_demand_ratio = total_supply / total_demand_capacity if total_demand_capacity > 0 else 0
                
                analysis['data_analysis'] = {
                    'total_supply': total_supply,
                    'total_demand_capacity': total_demand_capacity,
                    'supply_demand_ratio': supply_demand_ratio,
                    'num_skus': len(self.SKUs),
                    'num_stores': len(self.stores),
                    'num_scarce_skus': len(self.scarce)
                }
                
                if supply_demand_ratio > 1.5:
                    analysis['recommendations'].append("공급량이 수요 대비 과도하게 많습니다. allocation_range_max를 더 높이세요.")
                elif supply_demand_ratio < 0.5:
                    analysis['recommendations'].append("공급량이 수요 대비 부족합니다. allocation_range_min을 더 낮추세요.")
            
            elif prob2.status == -2:  # Unbounded
                analysis['recommendations'].extend([
                    "목적함수가 무제한으로 증가할 수 있습니다.",
                    "상한 제약조건을 추가하거나 강화하세요.",
                    "allocation_range_max를 더 낮추세요."
                ])
            
            elif prob2.status == 0:  # Not Solved
                analysis['recommendations'].extend([
                    "시간 내에 해를 찾지 못했습니다.",
                    "solver_timeout을 늘리거나 문제 크기를 줄이세요.",
                    "제약조건을 완화하여 문제를 단순화하세요."
                ])
                
        except Exception as e:
            analysis['analysis_error'] = str(e)
        
        return analysis
    
    def get_allocation_results(self) -> pd.DataFrame:
        """할당 결과를 DataFrame으로 반환"""
        if not self.x_result:
            return pd.DataFrame()
        
        allocation_results = []
        
        for (i, j), qty in self.x_result.items():
            part_cd, color_cd, size_cd = i.split('_')
            allocation_results.append({
                'SKU': i,
                'PART_CD': part_cd,
                'COLOR_CD': color_cd,
                'SIZE_CD': size_cd,
                'SHOP_ID': j,
                'ALLOCATED_QTY': qty,
                'SUPPLY_QTY': self.A[i],
                'SKU_TYPE': 'scarce' if i in self.scarce else 'abundant',
                'STEP1_ASSIGNED': 1 if (i, j) in self.b_hat and self.b_hat[(i, j)] == 1 else 0
            })
        
        return pd.DataFrame(allocation_results)
    
    def get_store_summary(self) -> pd.DataFrame:
        """매장별 요약 정보를 DataFrame으로 반환"""
        if not self.x_result:
            return pd.DataFrame()
        
        store_data = {}
        for (i, j), qty in self.x_result.items():
            if j not in store_data:
                store_data[j] = {'SKU_COUNT': 0, 'TOTAL_QTY': 0}
            store_data[j]['SKU_COUNT'] += 1
            store_data[j]['TOTAL_QTY'] += qty
        
        store_summary = pd.DataFrame.from_dict(store_data, orient='index')
        store_summary.reset_index(inplace=True)
        store_summary.rename(columns={'index': 'SHOP_ID'}, inplace=True)
        
        return store_summary 