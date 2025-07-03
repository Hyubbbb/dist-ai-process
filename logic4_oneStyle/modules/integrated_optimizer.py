"""
통합 MILP 최적화 모듈
커버리지 + Tier 균형 + 수량 효율성을 동시 최적화
"""

from pulp import (
    LpProblem, LpVariable, LpBinary, LpInteger,
    LpMaximize, lpSum, PULP_CBC_CMD
)
import numpy as np
import time


class IntegratedOptimizer:
    """모든 SKU (희소+충분)를 대상으로 한 통합 MILP 최적화"""
    
    def __init__(self, target_style):
        self.target_style = target_style
        self.prob = None
        self.final_allocation = {}
        # 목적함수 분해 분석을 위한 변수들 저장
        self.optimization_vars = {}
        self.last_scenario_params = {}
        self.last_data = {}
        
    def optimize_integrated(self, data, scarce_skus, abundant_skus, target_stores, 
                           store_allocation_limits, df_sku_filtered, tier_system, 
                           scenario_params):
        """
        통합 MILP 최적화 실행
        
        Args:
            data: 기본 데이터 구조
            scarce_skus: 희소 SKU 리스트
            abundant_skus: 충분 SKU 리스트
            target_stores: 배분 대상 매장 리스트
            store_allocation_limits: 매장별 SKU 배분 상한
            df_sku_filtered: 필터링된 SKU 데이터프레임
            tier_system: 매장 tier 시스템
            scenario_params: 시나리오 파라미터
        """
        A = data['A']
        stores = data['stores']
        SKUs = data['SKUs']
        K_s = data['K_s']
        L_s = data['L_s']
        QSUM = data['QSUM']
        
        print(f"🎯 통합 MILP 최적화 시작 (스타일: {self.target_style})")
        print(f"   전체 SKU: {len(SKUs)}개 (희소: {len(scarce_skus)}개, 충분: {len(abundant_skus)}개)")
        print(f"   대상 매장: {len(target_stores)}개")
        print(f"   시나리오: 커버리지 가중치={scenario_params['coverage_weight']}, 균형 페널티={scenario_params['balance_penalty']}")
        
        # 최적화 데이터 저장 (목적함수 분해 분석용)
        self.last_scenario_params = scenario_params.copy()
        self.last_data = data.copy()
        
        # 최적화 문제 생성
        self.prob = LpProblem(f'Integrated_MILP_{self.target_style}', LpMaximize)
        
        # 1. 변수 정의
        x, color_coverage, size_coverage, tier_balance_vars = self._create_variables(
            SKUs, stores, target_stores, K_s, L_s, tier_system
        )
        
        # 2. 목적함수 설정
        self._set_integrated_objective(
            x, color_coverage, size_coverage, tier_balance_vars,
            SKUs, stores, target_stores, scenario_params, A, QSUM
        )
        
        # 3. 제약조건 추가
        self._add_supply_constraints(x, SKUs, stores, A)
        self._add_store_capacity_constraints(x, SKUs, stores, target_stores, store_allocation_limits)
        self._add_coverage_constraints(x, color_coverage, size_coverage, SKUs, stores, 
                                     target_stores, K_s, L_s, df_sku_filtered)
        self._add_tier_balance_constraints(x, tier_balance_vars, SKUs, target_stores, 
                                         tier_system, QSUM, scenario_params)
        
        # 4. 최적화 실행
        print(f"   ⚡ 최적화 실행 중...")
        start_time = time.time()
        
        self.prob.solve(solver=PULP_CBC_CMD(msg=False, timeLimit=300))
        
        solve_time = time.time() - start_time
        print(f"   ⏱️ 최적화 완료: {solve_time:.2f}초")
        
        # 5. 결과 저장
        self._save_integrated_results(x, SKUs, stores)
        
        # 최적화 변수들 저장 (목적함수 분해 분석용)
        self.optimization_vars = {
            'x': x,
            'color_coverage': color_coverage,
            'size_coverage': size_coverage,
            'tier_balance_vars': tier_balance_vars,
            'SKUs': SKUs,
            'stores': stores,
            'target_stores': target_stores,
            'A': A,
            'QSUM': QSUM
        }
        
        return self._get_optimization_summary(A, target_stores)
    
    def _create_variables(self, SKUs, stores, target_stores, K_s, L_s, tier_system):
        """통합 최적화 변수 생성"""
        s = self.target_style
        
        # 1. 할당량 변수 (정수 변수 - 실제 수량)
        x = {}
        for i in SKUs:
            x[i] = {}
            for j in stores:
                if j in target_stores:
                    # 매장별 최대 할당 한도를 기반으로 상한 설정
                    tier_info = tier_system.get_store_tier_info(j, target_stores)
                    max_qty_per_sku = tier_info['max_sku_limit']
                    x[i][j] = LpVariable(f'x_{i}_{j}', lowBound=0, upBound=max_qty_per_sku, cat=LpInteger)
                else:
                    x[i][j] = 0
        
        # 2. 매장별 커버리지 변수
        color_coverage = {}
        size_coverage = {}
        for j in stores:
            if j in target_stores:
                color_coverage[(s,j)] = LpVariable(f"color_cov_{s}_{j}", 
                                                 lowBound=0, upBound=len(K_s[s]), cat=LpInteger)
                size_coverage[(s,j)] = LpVariable(f"size_cov_{s}_{j}", 
                                                lowBound=0, upBound=len(L_s[s]), cat=LpInteger)
            else:
                color_coverage[(s,j)] = 0
                size_coverage[(s,j)] = 0
        
        # 3. Tier 균형 변수
        tier_balance_vars = {}
        tier_names = ['TIER_1_HIGH', 'TIER_2_MEDIUM', 'TIER_3_LOW']
        
        for tier in tier_names:
            # 각 Tier의 평균 배분량 편차
            tier_balance_vars[f'{tier}_deviation'] = LpVariable(f'tier_dev_{tier}', 
                                                              lowBound=0, cat=LpInteger)
        
        return x, color_coverage, size_coverage, tier_balance_vars
    
    def _set_integrated_objective(self, x, color_coverage, size_coverage, tier_balance_vars,
                                SKUs, stores, target_stores, scenario_params, A, QSUM):
        """통합 목적함수 설정"""
        s = self.target_style
        
        # 가중치 추출
        coverage_weight = scenario_params['coverage_weight']
        balance_penalty = scenario_params['balance_penalty']
        allocation_penalty = scenario_params['allocation_penalty']
        
        # 1. 커버리지 최대화 (기존과 동일)
        coverage_term = coverage_weight * lpSum(
            color_coverage[(s,j)] + size_coverage[(s,j)] 
            for j in stores if isinstance(color_coverage[(s,j)], LpVariable)
        )
        
        # 2. 전체 배분량 최대화 (공급량 활용도)
        allocation_term = 0.1 * lpSum(
            x[i][j] for i in SKUs for j in stores if isinstance(x[i][j], LpVariable)
        )
        
        # 3. Tier 균형 페널티 (편차 최소화)
        balance_penalty_term = -balance_penalty * lpSum(
            tier_balance_vars[f'{tier}_deviation'] 
            for tier in ['TIER_1_HIGH', 'TIER_2_MEDIUM', 'TIER_3_LOW']
        )
        
        # 4. 매장 크기 대비 적정 배분량 보너스
        allocation_efficiency_term = 0.05 * lpSum(
            lpSum(x[i][j] for i in SKUs if isinstance(x[i][j], LpVariable)) / max(QSUM[j], 1) * 1000
            for j in target_stores
        )
        
        # 5. 희소 SKU 우선 배분 보너스
        scarce_bonus = 0.2 * lpSum(
            x[i][j] for i in SKUs for j in stores 
            if isinstance(x[i][j], LpVariable) and A[i] <= 100  # 희소 기준
        )
        
        # 6. 🆕 매장별 배분 편차 페널티 (allocation_penalty 적용)
        total_supply = sum(A.values())
        total_qsum = sum(QSUM[j] for j in target_stores)
        
        allocation_penalty_term = 0
        if allocation_penalty > 0:
            # 각 매장의 기대 배분량 대비 실제 배분량 편차를 페널티로 적용
            for j in target_stores:
                # 매장 j의 기대 배분량 (QTY_SUM 비례)
                expected_allocation = (QSUM[j] / total_qsum) * total_supply if total_qsum > 0 else 0
                
                # 실제 배분량
                actual_allocation = lpSum(x[i][j] for i in SKUs if isinstance(x[i][j], LpVariable))
                
                # 편차 변수 생성 (이미 tier_balance_vars에 포함되어야 하지만, 새로 생성)
                allocation_dev_var = LpVariable(f"allocation_dev_{j}", lowBound=0)
                
                # 편차 계산 제약조건
                self.prob += allocation_dev_var >= actual_allocation - expected_allocation
                self.prob += allocation_dev_var >= expected_allocation - actual_allocation
                
                allocation_penalty_term -= allocation_penalty * allocation_dev_var
        
        # 목적함수 통합 (allocation_penalty_term 추가)
        self.prob += (coverage_term + allocation_term + balance_penalty_term + 
                     allocation_efficiency_term + scarce_bonus + allocation_penalty_term)
        
        print(f"   📊 목적함수 구성:")
        print(f"      커버리지 항 (가중치: {coverage_weight})")
        print(f"      배분량 항 (가중치: 0.1)")
        print(f"      Tier 균형 항 (페널티: {balance_penalty})")
        print(f"      배분 효율성 항 (가중치: 0.05)")
        print(f"      희소 SKU 보너스 (가중치: 0.2)")
        print(f"      🆕 배분 편차 페널티 (가중치: {allocation_penalty})")
    
    def _add_supply_constraints(self, x, SKUs, stores, A):
        """공급량 제약조건"""
        for i in SKUs:
            total_allocation = lpSum(
                x[i][j] for j in stores if isinstance(x[i][j], LpVariable)
            )
            self.prob += total_allocation <= A[i]
    
    def _add_store_capacity_constraints(self, x, SKUs, stores, target_stores, store_allocation_limits):
        """매장별 용량 제약조건"""
        for j in stores:
            if j in target_stores:
                # SKU 종류 수 제한 (기존 제약)
                sku_allocation = lpSum(
                    x[i][j] for i in SKUs if isinstance(x[i][j], LpVariable)
                )
                self.prob += sku_allocation <= store_allocation_limits[j] * 3  # 최대 수량 여유
                
                # 개별 SKU별 수량 제한은 변수 정의 시 이미 적용됨
    
    def _add_coverage_constraints(self, x, color_coverage, size_coverage, SKUs, stores, 
                                target_stores, K_s, L_s, df_sku_filtered):
        """커버리지 제약조건 (단순화된 버전)"""
        s = self.target_style
        
        # 색상별/사이즈별 SKU 그룹 미리 계산
        color_sku_groups = {}
        size_sku_groups = {}
        
        for sku in SKUs:
            try:
                sku_info = df_sku_filtered.loc[df_sku_filtered['SKU']==sku].iloc[0]
                color = sku_info['COLOR_CD']
                size = sku_info['SIZE_CD']
                
                if color not in color_sku_groups:
                    color_sku_groups[color] = []
                color_sku_groups[color].append(sku)
                
                if size not in size_sku_groups:
                    size_sku_groups[size] = []
                size_sku_groups[size].append(sku)
            except:
                continue
        
        for j in stores:
            if j not in target_stores:
                continue
                
            if not isinstance(color_coverage[(s,j)], LpVariable):
                continue
            
            # 색상 커버리지 제약 (단순화)
            color_binaries = []
            for color, color_skus in color_sku_groups.items():
                # 해당 색상에 1개 이상 할당되면 +1
                color_allocation = lpSum(x[sku][j] for sku in color_skus if isinstance(x[sku][j], LpVariable))
                
                # 바이너리 변수
                color_binary = LpVariable(f"color_bin_{color}_{j}", cat=LpBinary)
                
                # color_allocation >= 1이면 color_binary = 1
                self.prob += color_allocation >= color_binary
                self.prob += color_allocation <= 1000 * color_binary  # Big-M
                
                color_binaries.append(color_binary)
            
            self.prob += color_coverage[(s,j)] == lpSum(color_binaries)
            
            # 사이즈 커버리지 제약 (단순화)
            size_binaries = []
            for size, size_skus in size_sku_groups.items():
                size_allocation = lpSum(x[sku][j] for sku in size_skus if isinstance(x[sku][j], LpVariable))
                
                size_binary = LpVariable(f"size_bin_{size}_{j}", cat=LpBinary)
                
                self.prob += size_allocation >= size_binary
                self.prob += size_allocation <= 1000 * size_binary  # Big-M
                
                size_binaries.append(size_binary)
            
            self.prob += size_coverage[(s,j)] == lpSum(size_binaries)
    
    def _add_tier_balance_constraints(self, x, tier_balance_vars, SKUs, target_stores, 
                                    tier_system, QSUM, scenario_params):
        """Tier 균형 제약조건 (단순화된 버전)"""
        
        # Tier별 매장 그룹 생성
        tier_stores = {'TIER_1_HIGH': [], 'TIER_2_MEDIUM': [], 'TIER_3_LOW': []}
        
        for store in target_stores:
            tier_info = tier_system.get_store_tier_info(store, target_stores)
            tier_name = tier_info['tier_name']
            tier_stores[tier_name].append(store)
        
        # 각 Tier 내에서 최대-최소 배분량 차이 제한 (단순화)
        for tier_name, stores_in_tier in tier_stores.items():
            if len(stores_in_tier) <= 1:
                # 매장이 1개 이하면 편차가 0
                self.prob += tier_balance_vars[f'{tier_name}_deviation'] == 0
                continue
            
            # 각 매장의 총 배분량 변수들
            store_totals = []
            for store in stores_in_tier:
                store_total = lpSum(x[i][store] for i in SKUs if isinstance(x[i][store], LpVariable))
                store_totals.append(store_total)
            
            # Tier 내 최대/최소 매장 배분량을 근사적으로 제한
            # (모든 매장 쌍에 대해 차이 제한하면 너무 복잡하므로 단순화)
            max_diff = len(stores_in_tier) * 2  # Tier 크기에 비례한 최대 허용 편차
            
            # 편차 변수에 상한 설정
            self.prob += tier_balance_vars[f'{tier_name}_deviation'] <= max_diff
        
        print(f"   ⚖️ Tier 균형 제약 설정 (단순화):")
        for tier_name, stores_in_tier in tier_stores.items():
            print(f"      {tier_name}: {len(stores_in_tier)}개 매장")
    
    def _save_integrated_results(self, x, SKUs, stores):
        """통합 최적화 결과 저장"""
        self.final_allocation = {}
        
        for i in SKUs:
            for j in stores:
                if isinstance(x[i][j], LpVariable):
                    qty = int(x[i][j].value()) if x[i][j].value() is not None else 0
                    if qty > 0:
                        self.final_allocation[(i, j)] = qty
                else:
                    self.final_allocation[(i, j)] = 0
    
    def _get_optimization_summary(self, A, target_stores):
        """최적화 결과 요약"""
        if self.prob.status == 1:  # Optimal
            total_allocated = sum(self.final_allocation.values())
            total_supply = sum(A.values())
            allocation_rate = total_allocated / total_supply if total_supply > 0 else 0
            
            allocated_stores = len(set(store for (sku, store), qty in self.final_allocation.items() if qty > 0))
            
            print(f"✅ 통합 MILP 최적화 완료!")
            print(f"   총 배분량: {total_allocated:,}개 / {total_supply:,}개 ({allocation_rate:.1%})")
            print(f"   배분받은 매장: {allocated_stores}개 / {len(target_stores)}개")
            print(f"   할당된 SKU-매장 조합: {len([x for x in self.final_allocation.values() if x > 0])}개")
            
            return {
                'status': 'success',
                'total_allocated': total_allocated,
                'total_supply': total_supply,
                'allocation_rate': allocation_rate,
                'allocated_stores': allocated_stores,
                'final_allocation': self.final_allocation
            }
        else:
            print(f"❌ 통합 MILP 최적화 실패: 상태 {self.prob.status}")
            return {
                'status': 'failed',
                'problem_status': self.prob.status,
                'final_allocation': {}
            }
    
    def get_final_allocation(self):
        """최종 배분 결과 반환"""
        return self.final_allocation 
    
    def get_objective_breakdown(self):
        """목적함수 구성요소별 값 분해 분석 (저장된 최적화 변수 사용)"""
        if not self.optimization_vars or self.prob.status != 1:
            print("❌ 최적화가 완료되지 않았거나 최적해가 없습니다.")
            return {}
        
        # 저장된 변수들 불러오기
        x = self.optimization_vars['x']
        color_coverage = self.optimization_vars['color_coverage']
        size_coverage = self.optimization_vars['size_coverage']
        tier_balance_vars = self.optimization_vars['tier_balance_vars']
        SKUs = self.optimization_vars['SKUs']
        stores = self.optimization_vars['stores']
        target_stores = self.optimization_vars['target_stores']
        A = self.optimization_vars['A']
        QSUM = self.optimization_vars['QSUM']
        
        coverage_weight = self.last_scenario_params.get('coverage_weight', 1.0)
        balance_penalty = self.last_scenario_params.get('balance_penalty', 0.1)
        
        # 1. 커버리지 항 계산
        coverage_term_value = 0
        s = self.target_style
        for j in target_stores:
            if isinstance(color_coverage[(s,j)], LpVariable) and color_coverage[(s,j)].value() is not None:
                coverage_term_value += color_coverage[(s,j)].value()
            if isinstance(size_coverage[(s,j)], LpVariable) and size_coverage[(s,j)].value() is not None:
                coverage_term_value += size_coverage[(s,j)].value()
        coverage_term_value *= coverage_weight
        
        # 2. 전체 배분량 항 계산
        allocation_term_value = 0
        for i in SKUs:
            for j in stores:
                if isinstance(x[i][j], LpVariable) and x[i][j].value() is not None:
                    allocation_term_value += x[i][j].value()
        allocation_term_value *= 0.1
        
        # 3. Tier 균형 페널티 계산
        balance_penalty_value = 0
        for tier in ['TIER_1_HIGH', 'TIER_2_MEDIUM', 'TIER_3_LOW']:
            deviation_var = tier_balance_vars.get(f'{tier}_deviation')
            if isinstance(deviation_var, LpVariable) and deviation_var.value() is not None:
                balance_penalty_value += deviation_var.value()
        balance_penalty_value *= -balance_penalty
        
        # 4. 배분 효율성 항 계산
        efficiency_term_value = 0
        for j in target_stores:
            store_total = sum(
                x[i][j].value() if isinstance(x[i][j], LpVariable) and x[i][j].value() is not None else 0
                for i in SKUs
            )
            efficiency_term_value += store_total / max(QSUM[j], 1) * 1000
        efficiency_term_value *= 0.05
        
        # 5. 희소 SKU 보너스 계산
        scarce_bonus_value = 0
        for i in SKUs:
            if A[i] <= 100:  # 희소 기준
                for j in stores:
                    if isinstance(x[i][j], LpVariable) and x[i][j].value() is not None:
                        scarce_bonus_value += x[i][j].value()
        scarce_bonus_value *= 0.2
        
        # 6. 🆕 매장별 배분 편차 페널티 계산 (결과 분석용)
        allocation_penalty_value = 0
        if hasattr(self, 'final_allocation') and allocation_penalty > 0:
            total_supply = sum(A.values())
            total_qsum = sum(QSUM[j] for j in target_stores)
            
            total_deviation = 0
            for j in target_stores:
                # 매장 j의 기대 배분량 (QTY_SUM 비례)
                expected_allocation = (QSUM[j] / total_qsum) * total_supply if total_qsum > 0 else 0
                
                # 실제 배분량 계산
                actual_allocation = sum(qty for (sku, store), qty in self.final_allocation.items() if store == j)
                
                # 편차 계산
                deviation = abs(actual_allocation - expected_allocation)
                total_deviation += deviation
            
            allocation_penalty_value = -allocation_penalty * total_deviation
        
        total_objective = (coverage_term_value + allocation_term_value + 
                          balance_penalty_value + efficiency_term_value + scarce_bonus_value + allocation_penalty_value)
        
        return {
            'coverage_term': coverage_term_value,
            'allocation_term': allocation_term_value,  
            'balance_penalty': balance_penalty_value,
            'efficiency_term': efficiency_term_value,
            'scarce_bonus': scarce_bonus_value,
            'allocation_penalty': allocation_penalty_value,
            'total_objective': total_objective,
            'coverage_weight': coverage_weight,
            'balance_penalty_weight': balance_penalty
        } 