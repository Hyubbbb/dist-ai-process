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
import math


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
        
        # tier_system을 인스턴스 변수로 저장
        self.tier_system = tier_system
        
        print(f"🎯 통합 MILP 최적화 시작 (스타일: {self.target_style})")
        print(f"   전체 SKU: {len(SKUs)}개 (희소: {len(scarce_skus)}개, 충분: {len(abundant_skus)}개)")
        print(f"   대상 매장: {len(target_stores)}개")
        print(f"   시나리오: 커버리지 가중치={scenario_params['coverage_weight']} (순수 커버리지만)")
        
        # 최적화 데이터 저장 (목적함수 분해 분석용)
        self.last_scenario_params = scenario_params.copy()
        self.last_data = data.copy()
        self.df_sku_filtered = df_sku_filtered  # SKU별 확장을 위해 저장
        
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
        
        # 🔍 문제 복잡도 진단
        self._diagnose_problem_complexity()
        
        start_time = time.time()
        
        # Solver 설정: verbose 출력 + 더 긴 timeout
        solver = PULP_CBC_CMD(
            msg=True,           # verbose 출력 켜기
            timeLimit=600,      # 10분 timeout
            gapRel=0.01,        # 1% gap에서 허용
            threads=4           # 멀티쓰레딩 사용
        )
        
        print(f"   🔧 Solver 설정: CBC with 10분 timeout, 1% gap tolerance")
        
        self.prob.solve(solver=solver)
        
        solve_time = time.time() - start_time
        
        # 🔍 최적화 결과 진단
        self._diagnose_optimization_result(solve_time)
        
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
            
            # 현재는 모든 SKU가 같은 target_stores를 사용
            # 향후 SKU별로 다른 매장 리스트가 지정될 수 있음
            sku_target_stores = target_stores  # 현재는 동일
            
            for j in stores:
                if j in sku_target_stores:
                    # 해당 매장의 tier 정보 가져오기 (기본 시스템 사용)
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
    
    def _get_sku_target_stores(self, sku, default_target_stores, tier_system):
        """SKU별 배분 대상 매장 결정"""
        # 현재는 모든 SKU가 같은 매장을 사용
        # 향후 tier_system에 SKU별 매장 지정 정보가 있으면 그것을 사용
        sku_stores = tier_system.get_sku_target_stores(sku)
        if sku_stores:
            return sku_stores
        else:
            return default_target_stores
    
    def _get_sku_store_tier_info(self, sku, store, sku_target_stores, tier_system):
        """SKU별 매장 tier 정보 가져오기"""
        # 현재는 기본 tier 시스템 사용
        # 향후 SKU별로 다른 tier 정보가 필요하면 확장 가능
        try:
            return tier_system.get_store_tier_info(store, sku_target_stores)
        except:
            # 기본값 반환 (안전장치)
            return {
                'store_id': store,
                'tier_name': 'TIER_3_LOW',
                'max_sku_limit': 1,
                'tier_ratio': 0.5
            }
    
    def _set_integrated_objective(self, x, color_coverage, size_coverage, tier_balance_vars,
                                SKUs, stores, target_stores, scenario_params, A, QSUM):
        """개선된 계층적 통합 목적함수 설정 - 1순위: 커버리지, 2순위: 계층적 공평성/동적 효율성, 3순위: 배분량 최대화"""
        import math
        
        s = self.target_style
        
        # 가중치 추출
        coverage_weight = scenario_params['coverage_weight']
        equity_weight = scenario_params.get('equity_weight', 0.5)
        efficiency_weight = scenario_params.get('efficiency_weight', 0.5)
        allocation_priority = scenario_params.get('allocation_priority', 'balanced')
        
        # 파라미터 정규화 (equity_weight + efficiency_weight = 1)
        total_secondary = equity_weight + efficiency_weight
        if total_secondary > 0:
            equity_weight = equity_weight / total_secondary
            efficiency_weight = efficiency_weight / total_secondary
        
        # 1순위: 커버리지 최대화 (매우 큰 가중치)
        coverage_term = 1000 * coverage_weight * lpSum(
            color_coverage[(s,j)] + size_coverage[(s,j)] 
            for j in stores if isinstance(color_coverage[(s,j)], LpVariable)
        )
        
        # 2순위: 개선된 계층적 공평성 - 단계별 매장 커버리지 + 추가 배분 인센티브
        equity_term = 0
        if equity_weight > 0:
            # 각 매장별 받은 SKU 개수 변수들
            store_sku_counts = {}
            store_coverage_binaries = {}
            
            for j in target_stores:
                # 매장별 총 SKU 개수 계산
                store_total_skus = lpSum(
                    x[i][j] for i in SKUs if isinstance(x[i][j], LpVariable)
                )
                store_sku_counts[j] = store_total_skus
                
                # 1단계: 최소 1개 SKU 받은 매장 (기본 생존권)
                basic_coverage_binary = LpVariable(f"basic_cov_{j}", cat=LpBinary)
                self.prob += store_total_skus >= basic_coverage_binary
                self.prob += store_total_skus <= 100 * basic_coverage_binary  # Big-M
                
                # 2단계: 최소 2개 SKU 받은 매장 (향상된 서비스)
                enhanced_coverage_binary = LpVariable(f"enhanced_cov_{j}", cat=LpBinary)
                self.prob += store_total_skus >= 2 * enhanced_coverage_binary
                self.prob += store_total_skus <= 100 * enhanced_coverage_binary + 1  # Big-M + slack
                
                # 3단계: 최소 3개 SKU 받은 매장 (프리미엄 서비스)
                premium_coverage_binary = LpVariable(f"premium_cov_{j}", cat=LpBinary)
                self.prob += store_total_skus >= 3 * premium_coverage_binary
                self.prob += store_total_skus <= 100 * premium_coverage_binary + 2  # Big-M + slack
                
                store_coverage_binaries[j] = {
                    'basic': basic_coverage_binary,
                    'enhanced': enhanced_coverage_binary,
                    'premium': premium_coverage_binary
                }
            
            # 계층적 공평성 점수: 1000:100:10 비율
            basic_coverage_sum = lpSum(store_coverage_binaries[j]['basic'] for j in target_stores)
            enhanced_coverage_sum = lpSum(store_coverage_binaries[j]['enhanced'] for j in target_stores)
            premium_coverage_sum = lpSum(store_coverage_binaries[j]['premium'] for j in target_stores)
            
            # 📈 개선: 매장별 실제 SKU 개수도 소량 가산 (3개 이상에서도 인센티브)
            total_sku_diversity = lpSum(store_sku_counts[j] for j in target_stores)
            
            equity_term = equity_weight * (
                1000 * basic_coverage_sum +
                100 * enhanced_coverage_sum +
                10 * premium_coverage_sum +
                0.1 * total_sku_diversity  # 매장당 SKU 다양성 보너스
            )
        
        # 2순위: 개선된 동적 가중치 효율성 - 매장 규모 대비 배분량
        efficiency_term = 0
        if efficiency_weight > 0:
            max_qsum = max(QSUM.values()) if QSUM.values() else 1
            
            efficiency_components = []
            for j in target_stores:
                # 동적 가중치: 매장 규모를 로그 스케일로 정규화
                qsum_weight = math.log(QSUM[j] + 1) / math.log(max_qsum + 1)
                
                # 매장별 총 배분량
                store_total_allocation = lpSum(
                    x[i][j] for i in SKUs if isinstance(x[i][j], LpVariable)
                )
                
                # 동적 가중치 × 배분량
                efficiency_components.append(qsum_weight * store_total_allocation)
            
            efficiency_term = efficiency_weight * lpSum(efficiency_components)
        
        # 3순위: 배분량 최대화 (배분 우선순위 옵션 적용)
        allocation_term = self._create_allocation_maximization_term(
            x, SKUs, target_stores, allocation_priority, QSUM
        )
        
        # 최종 목적함수: 계층적 구조 (배분량 최대화 항 추가)
        self.prob += coverage_term + equity_term + efficiency_term + allocation_term
        
        print(f"   📊 개선된 계층적 목적함수 구성:")
        print(f"      🎯 1순위 - 커버리지 최대화 (가중치: {1000 * coverage_weight})")
        print(f"      ⚖️  2순위 - 계층적 공평성 (가중치: {equity_weight:.3f})")
        print(f"          └ 1단계(기본): 1000점 × 1개이상받은매장수")
        print(f"          └ 2단계(향상): 100점 × 2개이상받은매장수") 
        print(f"          └ 3단계(프리미엄): 10점 × 3개이상받은매장수")
        print(f"          └ 📈 다양성 보너스: 0.1점 × 매장별SKU개수 (3개 이상에서도 인센티브)")
        print(f"      📈 2순위 - 동적 효율성 (가중치: {efficiency_weight:.3f})")
        print(f"          └ 매장별 QTY_SUM 정규화 가중치 × 배분량")
        print(f"          └ 큰 매장일수록 높은 가중치 (로그 스케일 정규화)")
        print(f"      📦 3순위 - 배분량 최대화 (우선순위: {allocation_priority})")
        print(f"          └ 남은 재고를 우선순위에 따라 추가 배분")
        
        # 배분 우선순위 설명 출력
        from config import ALLOCATION_PRIORITY_OPTIONS
        if allocation_priority in ALLOCATION_PRIORITY_OPTIONS:
            priority_info = ALLOCATION_PRIORITY_OPTIONS[allocation_priority]
            print(f"          └ {priority_info['name']}: {priority_info['description']}")
        
        if equity_weight > efficiency_weight:
            print(f"      → 공평성 우선: 모든 매장이 최소한 받는 것 중시")
        elif efficiency_weight > equity_weight:
            print(f"      → 효율성 우선: 매출 규모 큰 매장 우선 배분")
        else:
            print(f"      → 균형 전략: 공평성과 효율성 동등 고려")
        print(f"      🔄 배분 최대화: 남은 재고를 우선순위에 따라 추가 배분")
    
    def _create_allocation_maximization_term(self, x, SKUs, target_stores, allocation_priority, QSUM):
        """배분량 최대화 항 생성 (배분 우선순위 옵션 적용)"""
        import math
        import random
        
        # 배분 우선순위 옵션 정보 가져오기
        from config import ALLOCATION_PRIORITY_OPTIONS
        
        if allocation_priority not in ALLOCATION_PRIORITY_OPTIONS:
            allocation_priority = 'balanced'  # 기본값
        
        priority_config = ALLOCATION_PRIORITY_OPTIONS[allocation_priority]
        weight_function = priority_config['weight_function']
        randomness = priority_config['randomness']
        
        # 매장별 가중치 계산
        store_weights = {}
        max_qsum = max(QSUM.values()) if QSUM.values() else 1
        
        for i, store in enumerate(target_stores):
            base_weight = 1.0
            qsum_normalized = QSUM[store] / max_qsum
            
            # 기본 가중치 함수 적용
            if weight_function == 'linear_descending':
                # 상위 매장일수록 높은 가중치 (선형)
                base_weight = 1.0 - (i / len(target_stores))
            elif weight_function == 'log_descending':
                # 상위 매장일수록 높은 가중치 (로그)
                base_weight = math.log(len(target_stores) - i + 1) / math.log(len(target_stores) + 1)
            elif weight_function == 'sqrt_descending':
                # 상위 매장일수록 높은 가중치 (제곱근)
                base_weight = math.sqrt(len(target_stores) - i) / math.sqrt(len(target_stores))
            elif weight_function == 'uniform':
                # 모든 매장 동일 가중치
                base_weight = 1.0
            
            # 랜덤성 적용
            if randomness > 0:
                random_factor = random.uniform(0.5, 1.5)  # 0.5 ~ 1.5 사이 랜덤
                base_weight = base_weight * (1 - randomness) + random_factor * randomness
            
            store_weights[store] = base_weight
        
        # 가중치 정규화 (합이 1이 되도록)
        total_weight = sum(store_weights.values())
        if total_weight > 0:
            for store in store_weights:
                store_weights[store] /= total_weight
        
        # 배분량 최대화 항 생성 (낮은 가중치로 3순위 유지)
        allocation_components = []
        for store in target_stores:
            store_weight = store_weights[store]
            store_total_allocation = lpSum(
                x[i][store] for i in SKUs if isinstance(x[i][store], LpVariable)
            )
            allocation_components.append(store_weight * store_total_allocation)
        
        # 3순위로 낮은 가중치 (1.0)
        return 1.0 * lpSum(allocation_components)
    
    def _get_store_tier_info_safe(self, store, target_stores):
        """안전한 매장 tier 정보 가져오기"""
        try:
            # 기존 tier_system 사용 시도
            if hasattr(self, 'tier_system'):
                return self.tier_system.get_store_tier_info(store, target_stores)
            
            # tier_system이 없으면 인덱스 기반으로 계산
            store_index = target_stores.index(store)
            total_stores = len(target_stores)
            
            if store_index < total_stores * 0.3:
                return {'tier_name': 'TIER_1_HIGH', 'max_sku_limit': 3}
            elif store_index < total_stores * 0.5:
                return {'tier_name': 'TIER_2_MEDIUM', 'max_sku_limit': 2}
            else:
                return {'tier_name': 'TIER_3_LOW', 'max_sku_limit': 1}
        except:
            # 기본값 반환
            return {'tier_name': 'TIER_3_LOW', 'max_sku_limit': 1}
    
    def _add_supply_constraints(self, x, SKUs, stores, A):
        """공급량 제약조건 (강제 배분 제약 제거)"""
        
        # 공급량 상한 제약만 유지
        for i in SKUs:
            total_allocation = lpSum(
                x[i][j] for j in stores if isinstance(x[i][j], LpVariable)
            )
            self.prob += total_allocation <= A[i]
        
        print(f"   📦 공급량 제약 설정:")
        print(f"      각 SKU별 공급량 상한 제약만 적용 (≤ {sum(A.values()):,}개)")
        print(f"      강제 배분 제약 제거 - 남은 재고는 우선순위에 따라 추가 배분")
    
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
    
    def _diagnose_problem_complexity(self):
        """🔍 문제 복잡도 진단"""
        num_variables = len([var for var in self.prob.variables() if var.name])
        num_constraints = len(self.prob.constraints)
        
        print(f"   📊 문제 복잡도 분석:")
        print(f"      변수 수: {num_variables:,}개")
        print(f"      제약조건 수: {num_constraints:,}개")
        
        # 복잡도 평가
        if num_variables > 10000 or num_constraints > 5000:
            print(f"      ⚠️  대규모 문제: 수렴에 시간이 오래 걸릴 수 있습니다")
        elif num_variables > 5000 or num_constraints > 2000:
            print(f"      🔶 중간 규모 문제: 적당한 수렴 시간 예상")
        else:
            print(f"      ✅ 소규모 문제: 빠른 수렴 예상")
        
        # 변수 타입별 분석
        integer_vars = len([var for var in self.prob.variables() if var.cat == 'Integer'])
        binary_vars = len([var for var in self.prob.variables() if var.cat == 'Binary'])
        continuous_vars = num_variables - integer_vars - binary_vars
        
        print(f"      변수 타입: 정수 {integer_vars}, 바이너리 {binary_vars}, 연속 {continuous_vars}")
        
        if binary_vars > 1000:
            print(f"      ⚠️  바이너리 변수가 많아 조합 복잡도가 높습니다")
    
    def _diagnose_optimization_result(self, solve_time):
        """🔍 최적화 결과 진단"""
        status_messages = {
            1: "✅ Optimal - 최적해 발견",
            0: "❓ Not Solved - 해를 찾지 못함",
            -1: "❌ Infeasible - 실행 불가능한 문제",
            -2: "❌ Unbounded - 무한대 해",
            -3: "❌ Undefined - 정의되지 않은 상태"
        }
        
        status = self.prob.status
        message = status_messages.get(status, f"❓ Unknown Status: {status}")
        
        print(f"   🔍 최적화 결과 진단:")
        print(f"      상태: {message}")
        print(f"      소요 시간: {solve_time:.2f}초")
        
        if status == 1:  # Optimal
            obj_value = self.prob.objective.value()
            print(f"      목적함수 값: {obj_value:.2f}")
            print(f"      ✅ 성공적으로 최적해를 찾았습니다!")
            
        elif status == 0:  # Not Solved
            print(f"      ⚠️  시간 초과 또는 수렴 실패")
            print(f"      💡 가능한 원인:")
            print(f"         - 문제가 너무 복잡함 (timeout 증가 필요)")
            print(f"         - 여러 동등한 최적해 존재 (solver가 선택 어려움)")
            print(f"         - 제약조건이 너무 tight함")
            
        elif status == -1:  # Infeasible
            print(f"      ❌ 실행 불가능한 문제입니다")
            print(f"      💡 가능한 원인:")
            print(f"         - 공급량 < 수요량")
            print(f"         - 매장별 제한이 너무 엄격함")
            print(f"         - 상충하는 제약조건들")
            print(f"      🔧 해결책:")
            print(f"         - 제약조건 완화")
            print(f"         - 공급량 증가")
            print(f"         - 매장별 한도 조정")
            
        elif status == -2:  # Unbounded
            print(f"      ❌ 무한대 해 - 목적함수가 제한되지 않음")
            print(f"      💡 제약조건이 부족하거나 잘못 설정됨")
            
        # 추가 진단 정보
        if solve_time > 300:  # 5분 이상
            print(f"      ⏰ 긴 수렴 시간 감지")
            print(f"      💡 개선 방안:")
            print(f"         - Solver 파라미터 조정")
            print(f"         - 문제 단순화")
            print(f"         - 휴리스틱 초기해 제공")
    
    def get_objective_breakdown(self):
        """개선된 목적함수 구성요소별 값 분해 분석 (계층적 공평성 + 동적 효율성 + 배분량 최대화)"""
        import math
        
        if not self.optimization_vars or self.prob.status != 1:
            print("❌ 최적화가 완료되지 않았거나 최적해가 없습니다.")
            return {}
        
        # 저장된 변수들 불러오기
        x = self.optimization_vars['x']
        color_coverage = self.optimization_vars['color_coverage']
        size_coverage = self.optimization_vars['size_coverage']
        target_stores = self.optimization_vars['target_stores']
        SKUs = self.optimization_vars['SKUs']
        stores = self.optimization_vars['stores']
        QSUM = self.optimization_vars['QSUM']
        A = self.optimization_vars['A']
        
        coverage_weight = self.last_scenario_params.get('coverage_weight', 1.0)
        equity_weight = self.last_scenario_params.get('equity_weight', 0.5)
        efficiency_weight = self.last_scenario_params.get('efficiency_weight', 0.5)
        allocation_priority = self.last_scenario_params.get('allocation_priority', 'balanced')
        
        # 파라미터 정규화
        total_secondary = equity_weight + efficiency_weight
        if total_secondary > 0:
            equity_weight = equity_weight / total_secondary
            efficiency_weight = efficiency_weight / total_secondary
        
        # 1순위: 커버리지 항 계산
        coverage_term_value = 0
        s = self.target_style
        for j in target_stores:
            if isinstance(color_coverage[(s,j)], LpVariable) and color_coverage[(s,j)].value() is not None:
                coverage_term_value += color_coverage[(s,j)].value()
            if isinstance(size_coverage[(s,j)], LpVariable) and size_coverage[(s,j)].value() is not None:
                coverage_term_value += size_coverage[(s,j)].value()
        coverage_term_value *= 1000 * coverage_weight
        
        # 2순위: 계층적 공평성 항 계산 (다양성 보너스 포함)
        equity_term_value = 0
        basic_coverage_count = 0  # 1개 이상 받은 매장 수
        enhanced_coverage_count = 0  # 2개 이상 받은 매장 수  
        premium_coverage_count = 0  # 3개 이상 받은 매장 수
        total_sku_diversity = 0  # 매장별 SKU 개수 총합
        
        if equity_weight > 0:
            for j in target_stores:
                # 매장별 총 SKU 개수 계산
                store_total_skus = 0
                for i in SKUs:
                    if isinstance(x[i][j], LpVariable) and x[i][j].value() is not None:
                        store_total_skus += x[i][j].value()
                
                total_sku_diversity += store_total_skus
                
                # 계층별 카운트
                if store_total_skus >= 1:
                    basic_coverage_count += 1
                if store_total_skus >= 2:
                    enhanced_coverage_count += 1
                if store_total_skus >= 3:
                    premium_coverage_count += 1
            
            # 계층적 공평성 점수 계산 (다양성 보너스 포함)
            equity_term_value = equity_weight * (
                1000 * basic_coverage_count +
                100 * enhanced_coverage_count +
                10 * premium_coverage_count +
                0.1 * total_sku_diversity  # 다양성 보너스
            )
        
        # 2순위: 동적 효율성 항 계산
        efficiency_term_value = 0
        total_weighted_allocation = 0  # 가중치 적용된 총 배분량
        
        if efficiency_weight > 0:
            max_qsum = max(QSUM.values()) if QSUM.values() else 1
            
            for j in target_stores:
                # 동적 가중치 계산
                qsum_weight = math.log(QSUM[j] + 1) / math.log(max_qsum + 1)
                
                # 매장별 총 배분량
                store_total_allocation = 0
                for i in SKUs:
                    if isinstance(x[i][j], LpVariable) and x[i][j].value() is not None:
                        store_total_allocation += x[i][j].value()
                
                # 가중치 적용
                weighted_allocation = qsum_weight * store_total_allocation
                total_weighted_allocation += weighted_allocation
            
            efficiency_term_value = efficiency_weight * total_weighted_allocation
        
        # 3순위: 배분량 최대화 항 계산
        allocation_term_value = 0
        total_allocated = 0  # 총 배분량
        priority_weighted_allocation = 0  # 우선순위 가중치 적용된 배분량
        
        # 배분 우선순위 정보 가져오기
        from config import ALLOCATION_PRIORITY_OPTIONS
        if allocation_priority in ALLOCATION_PRIORITY_OPTIONS:
            priority_config = ALLOCATION_PRIORITY_OPTIONS[allocation_priority]
            weight_function = priority_config['weight_function']
            randomness = priority_config['randomness']
            
            # 매장별 가중치 계산 (분석용)
            store_weights = {}
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
                
                store_weights[store] = base_weight
            
            # 가중치 정규화
            total_weight = sum(store_weights.values())
            if total_weight > 0:
                for store in store_weights:
                    store_weights[store] /= total_weight
            
            # 우선순위 가중치 적용된 배분량 계산
            for j in target_stores:
                store_weight = store_weights[j]
                store_total_allocation = 0
                for i in SKUs:
                    if isinstance(x[i][j], LpVariable) and x[i][j].value() is not None:
                        store_total_allocation += x[i][j].value()
                
                total_allocated += store_total_allocation
                priority_weighted_allocation += store_weight * store_total_allocation
        
        allocation_term_value = 1.0 * priority_weighted_allocation
        
        # 최종 목적함수 계산
        total_objective = coverage_term_value + equity_term_value + efficiency_term_value + allocation_term_value
        
        # 배분률 계산
        total_supply = sum(A.values())
        allocation_rate = total_allocated / total_supply if total_supply > 0 else 0
        
        # 최대 가능 점수 계산
        max_basic_coverage = len(target_stores)  # 모든 매장이 1개 이상
        max_enhanced_coverage = len(target_stores)  # 모든 매장이 2개 이상
        max_premium_coverage = len(target_stores)  # 모든 매장이 3개 이상
        max_equity_score = 1000 * max_basic_coverage + 100 * max_enhanced_coverage + 10 * max_premium_coverage
        
        return {
            'coverage_term': coverage_term_value,
            'equity_term': equity_term_value,
            'efficiency_term': efficiency_term_value,
            'allocation_term': allocation_term_value,
            'total_objective': total_objective,
            'coverage_weight': coverage_weight,
            'equity_weight': equity_weight,
            'efficiency_weight': efficiency_weight,
            'allocation_priority': allocation_priority,
            
            # 계층적 공평성 세부 정보
            'basic_coverage_count': basic_coverage_count,
            'enhanced_coverage_count': enhanced_coverage_count,
            'premium_coverage_count': premium_coverage_count,
            'total_sku_diversity': total_sku_diversity,
            'max_basic_coverage': max_basic_coverage,
            'max_enhanced_coverage': max_enhanced_coverage,
            'max_premium_coverage': max_premium_coverage,
            'max_equity_score': max_equity_score,
            'equity_coverage_rate': (1000 * basic_coverage_count + 100 * enhanced_coverage_count + 10 * premium_coverage_count + 0.1 * total_sku_diversity) / (max_equity_score + 0.1 * len(target_stores) * len(SKUs)) if max_equity_score > 0 else 0,
            
            # 동적 효율성 세부 정보
            'total_weighted_allocation': total_weighted_allocation,
            'efficiency_coverage_rate': total_weighted_allocation / len(target_stores) if len(target_stores) > 0 else 0,
            
            # 배분량 최대화 세부 정보 (새로 추가)
            'total_allocated': total_allocated,
            'total_supply': total_supply,
            'allocation_rate': allocation_rate,
            'priority_weighted_allocation': priority_weighted_allocation,
        } 