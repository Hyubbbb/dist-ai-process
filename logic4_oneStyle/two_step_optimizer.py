"""
2-Step 배분 최적화 모듈
Step 1: 바이너리 커버리지 최적화 
Step 2: 룰베이스 추가 배분
"""

from pulp import (
    LpProblem, LpVariable, LpBinary, LpInteger,
    LpMaximize, lpSum, PULP_CBC_CMD
)
import numpy as np
import time
import random
import math


class TwoStepOptimizer:
    """2-Step 배분 최적화: 커버리지 우선 + 룰베이스 추가 배분"""
    
    def __init__(self, target_style):
        self.target_style = target_style
        self.step1_prob = None
        self.step1_allocation = {}  # Step 1 바이너리 결과
        self.final_allocation = {}  # Step 2 최종 결과
        
        # 분석용 저장 변수
        self.step1_time = 0
        self.step2_time = 0
        self.step1_objective = 0
        self.step2_additional_allocation = 0
        
    def optimize_two_step(self, data, scarce_skus, abundant_skus, target_stores, 
                         store_allocation_limits, df_sku_filtered, tier_system, 
                         scenario_params):
        """
        2-Step 최적화 실행
        
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
        
        print(f"🎯 2-Step 최적화 시작 (스타일: {self.target_style})")
        print(f"   전체 SKU: {len(SKUs)}개")
        print(f"   대상 매장: {len(target_stores)}개")
        print(f"   배분 우선순위: {scenario_params.get('allocation_priority', 'balanced')}")
        
        # Step 1: 바이너리 커버리지 최적화
        step1_result = self._step1_coverage_optimization(
            data, SKUs, stores, target_stores, store_allocation_limits, 
            df_sku_filtered, K_s, L_s
        )
        
        if step1_result['status'] != 'success':
            return {
                'status': 'failed',
                'step': 1,
                'final_allocation': {}
            }
        
        # Step 2: 룰베이스 추가 배분
        step2_result = self._step2_rule_based_allocation(
            data, SKUs, stores, target_stores, store_allocation_limits,
            tier_system, scenario_params, QSUM
        )
        
        return self._get_optimization_summary(A, target_stores, step1_result, step2_result)
    
    def _step1_coverage_optimization(self, data, SKUs, stores, target_stores, 
                                   store_allocation_limits, df_sku_filtered, K_s, L_s):
        """Step 1: 순수 커버리지 최적화 (바이너리)"""
        print(f"\n📊 Step 1: 바이너리 커버리지 최적화")
        
        start_time = time.time()
        
        # MILP 문제 생성
        self.step1_prob = LpProblem(f'Step1_Coverage_{self.target_style}', LpMaximize)
        
        # 1. 바이너리 변수 생성: b[i][j] ∈ {0,1}
        b = self._create_binary_variables(SKUs, stores, target_stores)
        
        # 2. 커버리지 변수 생성
        color_coverage, size_coverage = self._create_coverage_variables(stores, target_stores, K_s, L_s)
        
        # 3. 순수 커버리지 목적함수 설정
        self._set_coverage_objective(color_coverage, size_coverage, stores, target_stores)
        
        # 4. 제약조건 추가
        self._add_step1_constraints(b, color_coverage, size_coverage, SKUs, stores, 
                                   target_stores, store_allocation_limits, 
                                   df_sku_filtered, K_s, L_s, data['A'])
        
        # 5. 최적화 실행
        print(f"   ⚡ Step 1 최적화 실행 중...")
        
        solver = PULP_CBC_CMD(msg=False, timeLimit=300)
        self.step1_prob.solve(solver=solver)
        
        self.step1_time = time.time() - start_time
        
        # 6. 결과 저장
        if self.step1_prob.status == 1:
            self._save_step1_results(b, SKUs, stores)
            
            allocated_combinations = sum(1 for v in self.step1_allocation.values() if v > 0)
            self.step1_objective = self.step1_prob.objective.value()
            
            print(f"   ✅ Step 1 완료: {allocated_combinations}개 SKU-매장 조합 선택")
            print(f"   📊 커버리지 점수: {self.step1_objective:.1f}")
            print(f"   ⏱️ 소요 시간: {self.step1_time:.2f}초")
            
            return {
                'status': 'success',
                'allocated_combinations': allocated_combinations,
                'coverage_objective': self.step1_objective
            }
        else:
            print(f"   ❌ Step 1 실패: 상태 {self.step1_prob.status}")
            return {
                'status': 'failed',
                'problem_status': self.step1_prob.status
            }
    
    def _step2_rule_based_allocation(self, data, SKUs, stores, target_stores, 
                                   store_allocation_limits, tier_system, 
                                   scenario_params, QSUM):
        """Step 2: 룰베이스 추가 배분"""
        print(f"\n📦 Step 2: 룰베이스 추가 배분")
        
        start_time = time.time()
        A = data['A']
        
        # Step 1 결과를 기반으로 최종 배분 초기화
        self.final_allocation = self.step1_allocation.copy()
        
        # 배분 우선순위 설정
        allocation_priority = scenario_params.get('allocation_priority', 'balanced')
        store_priority_weights = self._calculate_store_priorities(target_stores, QSUM, allocation_priority)
        
        # 각 SKU별로 남은 수량 추가 배분
        total_additional = 0
        
        for sku in SKUs:
            additional_allocated = self._allocate_remaining_sku(
                sku, target_stores, A, tier_system, store_priority_weights, 
                store_allocation_limits
            )
            total_additional += additional_allocated
        
        self.step2_time = time.time() - start_time
        self.step2_additional_allocation = total_additional
        
        print(f"   ✅ Step 2 완료: {total_additional}개 추가 배분")
        print(f"   ⏱️ 소요 시간: {self.step2_time:.2f}초")
        
        return {
            'status': 'success',
            'additional_allocation': total_additional
        }
    
    def _create_binary_variables(self, SKUs, stores, target_stores):
        """바이너리 할당 변수 생성"""
        b = {}
        for i in SKUs:
            b[i] = {}
            for j in stores:
                if j in target_stores:
                    b[i][j] = LpVariable(f'b_{i}_{j}', cat=LpBinary)
                else:
                    b[i][j] = 0
        return b
    
    def _create_coverage_variables(self, stores, target_stores, K_s, L_s):
        """커버리지 변수 생성"""
        color_coverage = {}
        size_coverage = {}
        s = self.target_style
        
        for j in stores:
            if j in target_stores:
                color_coverage[(s,j)] = LpVariable(f"color_coverage_{s}_{j}", 
                                                 lowBound=0, upBound=len(K_s[s]), cat=LpInteger)
                size_coverage[(s,j)] = LpVariable(f"size_coverage_{s}_{j}", 
                                                lowBound=0, upBound=len(L_s[s]), cat=LpInteger)
            else:
                color_coverage[(s,j)] = 0
                size_coverage[(s,j)] = 0
        
        return color_coverage, size_coverage
    
    def _set_coverage_objective(self, color_coverage, size_coverage, stores, target_stores):
        """순수 커버리지 목적함수 설정"""
        s = self.target_style
        
        # 색상 + 사이즈 커버리지 합계만 최대화
        coverage_sum = lpSum(
            color_coverage[(s,j)] + size_coverage[(s,j)] 
            for j in stores if j in target_stores and isinstance(color_coverage[(s,j)], LpVariable)
        )
        
        self.step1_prob += coverage_sum
        
        print(f"   🎯 목적함수: 순수 커버리지 최대화 (색상 + 사이즈)")
    
    def _add_step1_constraints(self, b, color_coverage, size_coverage, SKUs, stores, 
                              target_stores, store_allocation_limits, df_sku_filtered, 
                              K_s, L_s, A):
        """Step 1 제약조건 추가"""
        
        # 1. 각 SKU는 최대 1개만 배분 (바이너리)
        for i in SKUs:
            sku_allocation = lpSum(
                b[i][j] for j in stores if isinstance(b[i][j], LpVariable)
            )
            self.step1_prob += sku_allocation <= A[i]  # 공급량 제한
        
        # 2. 매장별 최대 배분 SKU 수 제한
        for j in stores:
            if j in target_stores:
                store_allocation = lpSum(
                    b[i][j] for i in SKUs if isinstance(b[i][j], LpVariable)
                )
                self.step1_prob += store_allocation <= store_allocation_limits[j]
        
        # 3. 커버리지 제약조건
        self._add_coverage_constraints_step1(b, color_coverage, size_coverage, SKUs, stores, 
                                           target_stores, K_s, L_s, df_sku_filtered)
        
        print(f"   📋 제약조건: 바이너리 배분 + 매장별 한도 + 커버리지")
    
    def _add_coverage_constraints_step1(self, b, color_coverage, size_coverage, SKUs, stores, 
                                      target_stores, K_s, L_s, df_sku_filtered):
        """Step 1 커버리지 제약조건"""
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
            
            # 색상 커버리지 제약
            color_binaries = []
            for color, color_skus in color_sku_groups.items():
                color_allocation = lpSum(b[sku][j] for sku in color_skus if isinstance(b[sku][j], LpVariable))
                
                color_binary = LpVariable(f"color_bin_{color}_{j}", cat=LpBinary)
                
                self.step1_prob += color_allocation >= color_binary
                self.step1_prob += color_allocation <= len(color_skus) * color_binary
                
                color_binaries.append(color_binary)
            
            self.step1_prob += color_coverage[(s,j)] == lpSum(color_binaries)
            
            # 사이즈 커버리지 제약
            size_binaries = []
            for size, size_skus in size_sku_groups.items():
                size_allocation = lpSum(b[sku][j] for sku in size_skus if isinstance(b[sku][j], LpVariable))
                
                size_binary = LpVariable(f"size_bin_{size}_{j}", cat=LpBinary)
                
                self.step1_prob += size_allocation >= size_binary
                self.step1_prob += size_allocation <= len(size_skus) * size_binary
                
                size_binaries.append(size_binary)
            
            self.step1_prob += size_coverage[(s,j)] == lpSum(size_binaries)
    
    def _save_step1_results(self, b, SKUs, stores):
        """Step 1 결과 저장"""
        self.step1_allocation = {}
        for i in SKUs:
            for j in stores:
                if isinstance(b[i][j], LpVariable):
                    value = int(b[i][j].value()) if b[i][j].value() is not None else 0
                    self.step1_allocation[(i, j)] = value
                else:
                    self.step1_allocation[(i, j)] = 0
    
    def _calculate_store_priorities(self, target_stores, QSUM, allocation_priority):
        """매장별 우선순위 가중치 계산"""
        from config import ALLOCATION_PRIORITY_OPTIONS
        
        if allocation_priority not in ALLOCATION_PRIORITY_OPTIONS:
            allocation_priority = 'balanced'
        
        priority_config = ALLOCATION_PRIORITY_OPTIONS[allocation_priority]
        weight_function = priority_config['weight_function']
        randomness = priority_config['randomness']
        
        store_weights = {}
        max_qsum = max(QSUM.values()) if QSUM.values() else 1
        
        for i, store in enumerate(target_stores):
            base_weight = 1.0
            
            if weight_function == 'linear_descending':
                base_weight = 1.0 - (i / len(target_stores))
            elif weight_function == 'log_descending':
                base_weight = math.log(len(target_stores) - i + 1) / math.log(len(target_stores) + 1)
            elif weight_function == 'sqrt_descending':
                base_weight = math.sqrt(len(target_stores) - i) / math.sqrt(len(target_stores))
            elif weight_function == 'uniform':
                base_weight = 1.0
            
            # 랜덤성 적용
            if randomness > 0:
                random_factor = random.uniform(0.5, 1.5)
                base_weight = base_weight * (1 - randomness) + random_factor * randomness
            
            store_weights[store] = base_weight
        
        print(f"   🎲 배분 우선순위: {priority_config['name']}")
        print(f"      가중치 함수: {weight_function}, 랜덤성: {randomness*100:.0f}%")
        
        return store_weights
    
    def _allocate_remaining_sku(self, sku, target_stores, A, tier_system, 
                              store_priority_weights, store_allocation_limits):
        """개별 SKU의 남은 수량 추가 배분"""
        
        # Step 1에서 이미 배분된 수량 계산
        allocated_in_step1 = sum(self.step1_allocation.get((sku, store), 0) for store in target_stores)
        remaining_qty = A[sku] - allocated_in_step1
        
        if remaining_qty <= 0:
            return 0
        
        # 각 매장별 추가 배분 가능량 계산
        store_candidates = []
        for store in target_stores:
            # 현재 매장의 tier 정보
            tier_info = tier_system.get_store_tier_info(store, target_stores)
            max_qty_per_sku = tier_info['max_sku_limit']
            
            # 이미 배분된 수량
            current_qty = self.final_allocation.get((sku, store), 0)
            
            # 추가 배분 가능량
            additional_capacity = max_qty_per_sku - current_qty
            
            if additional_capacity > 0:
                priority_weight = store_priority_weights.get(store, 1.0)
                store_candidates.append({
                    'store': store,
                    'capacity': additional_capacity,
                    'weight': priority_weight
                })
        
        # 우선순위에 따라 정렬
        store_candidates.sort(key=lambda x: x['weight'], reverse=True)
        
        # 우선순위 순서로 배분
        additional_allocated = 0
        for candidate in store_candidates:
            if remaining_qty <= 0:
                break
            
            store = candidate['store']
            capacity = candidate['capacity']
            
            # 배분할 수량 결정
            allocation_qty = min(remaining_qty, capacity)
            
            if allocation_qty > 0:
                # 기존 배분량에 추가
                current_qty = self.final_allocation.get((sku, store), 0)
                self.final_allocation[(sku, store)] = current_qty + allocation_qty
                
                remaining_qty -= allocation_qty
                additional_allocated += allocation_qty
        
        return additional_allocated
    
    def _get_optimization_summary(self, A, target_stores, step1_result, step2_result):
        """최적화 결과 요약"""
        
        total_allocated = sum(self.final_allocation.values())
        total_supply = sum(A.values())
        allocation_rate = total_allocated / total_supply if total_supply > 0 else 0
        
        allocated_stores = len(set(store for (sku, store), qty in self.final_allocation.items() if qty > 0))
        
        print(f"\n✅ 2-Step 최적화 완료!")
        print(f"   Step 1 커버리지: {step1_result['coverage_objective']:.1f}")
        print(f"   Step 2 추가 배분: {step2_result['additional_allocation']}개")
        print(f"   총 배분량: {total_allocated:,}개 / {total_supply:,}개 ({allocation_rate:.1%})")
        print(f"   배분받은 매장: {allocated_stores}개 / {len(target_stores)}개")
        print(f"   전체 소요 시간: {self.step1_time + self.step2_time:.2f}초")
        
        return {
            'status': 'success',
            'total_allocated': total_allocated,
            'total_supply': total_supply,
            'allocation_rate': allocation_rate,
            'allocated_stores': allocated_stores,
            'final_allocation': self.final_allocation,
            
            # 2-Step 특별 정보
            'step1_time': self.step1_time,
            'step2_time': self.step2_time,
            'step1_objective': self.step1_objective,
            'step2_additional': self.step2_additional_allocation,
            'step1_combinations': step1_result['allocated_combinations']
        }
    
    def get_final_allocation(self):
        """최종 배분 결과 반환"""
        return self.final_allocation
    
    def get_step_analysis(self):
        """단계별 분석 정보 반환"""
        return {
            'step1': {
                'time': self.step1_time,
                'objective': self.step1_objective,
                'combinations': len([v for v in self.step1_allocation.values() if v > 0])
            },
            'step2': {
                'time': self.step2_time,
                'additional_allocation': self.step2_additional_allocation
            },
            'total_time': self.step1_time + self.step2_time
        } 