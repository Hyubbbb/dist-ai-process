"""
Coverage 최적화 모듈 (Step1 MILP)
"""

from pulp import (
    LpProblem, LpVariable, LpBinary, LpInteger,
    LpMaximize, lpSum, PULP_CBC_CMD
)


class CoverageOptimizer:
    """희소 SKU 커버리지 최적화를 담당하는 클래스"""
    
    def __init__(self, target_style):
        self.target_style = target_style
        self.prob = None
        self.b_hat = {}  # 최적화 결과 저장
        
    def optimize_coverage(self, data, scarce_skus, target_stores, 
                         store_allocation_limits, df_sku_filtered):
        """
        희소 SKU 커버리지 최적화 실행
        
        Args:
            data: 기본 데이터 구조 (A, SKUs, stores, K_s, L_s 등)
            scarce_skus: 희소 SKU 리스트
            target_stores: 배분 대상 매장 리스트
            store_allocation_limits: 매장별 SKU 배분 상한
            df_sku_filtered: 필터링된 SKU 데이터프레임
        """
        A = data['A']
        stores = data['stores']
        K_s = data['K_s']
        L_s = data['L_s']
        
        print(f"🎯 Step1: Coverage 최적화 시작 (스타일: {self.target_style})")
        print(f"   희소 SKU: {len(scarce_skus)}개")
        print(f"   대상 매장: {len(target_stores)}개")
        
        # 최적화 문제 생성
        self.prob = LpProblem(f'Step1_Coverage_{self.target_style}', LpMaximize)
        
        # 변수 정의
        b = self._create_variables(scarce_skus, stores, target_stores)
        color_coverage, size_coverage = self._create_coverage_variables(stores, target_stores, K_s, L_s)
        
        # 목적함수 설정
        self._set_objective(color_coverage, size_coverage, b, scarce_skus, stores, target_stores)
        
        # 제약조건 추가
        self._add_supply_constraints(b, scarce_skus, stores, A)
        self._add_store_limit_constraints(b, scarce_skus, stores, target_stores, store_allocation_limits)
        self._add_coverage_constraints(b, color_coverage, size_coverage, scarce_skus, stores, 
                                     target_stores, K_s, L_s, df_sku_filtered)
        
        # 최적화 실행
        self.prob.solve(PULP_CBC_CMD(msg=False))
        
        # 결과 저장
        self._save_results(b, scarce_skus, stores)
        
        return self._get_optimization_summary()
    
    def _create_variables(self, scarce_skus, stores, target_stores):
        """할당 변수 생성"""
        b = {}
        for i in scarce_skus:
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
    
    def _set_objective(self, color_coverage, size_coverage, b, scarce_skus, stores, target_stores):
        """목적함수 설정"""
        s = self.target_style
        
        # 색상 + 사이즈 커버리지 합계
        color_coverage_sum = lpSum(
            color_coverage[(s,j)] for j in stores if isinstance(color_coverage[(s,j)], LpVariable)
        )
        size_coverage_sum = lpSum(
            size_coverage[(s,j)] for j in stores if isinstance(size_coverage[(s,j)], LpVariable)
        )
        
        self.prob += color_coverage_sum + size_coverage_sum
    
    def _add_supply_constraints(self, b, scarce_skus, stores, A):
        """공급량 제약조건"""
        for i in scarce_skus:
            valid_allocation_sum = lpSum(
                b[i][j] for j in stores if isinstance(b[i][j], LpVariable)
            )
            self.prob += valid_allocation_sum <= A[i]
    
    def _add_store_limit_constraints(self, b, scarce_skus, stores, target_stores, store_allocation_limits):
        """매장별 배분 상한 제약조건"""
        for j in stores:
            if j in target_stores:
                max_allocation = store_allocation_limits[j]
                store_scarce_allocation = lpSum(
                    b[i][j] for i in scarce_skus if isinstance(b[i][j], LpVariable)
                )
                self.prob += store_scarce_allocation <= max_allocation
    
    def _add_coverage_constraints(self, b, color_coverage, size_coverage, scarce_skus, stores, 
                                target_stores, K_s, L_s, df_sku_filtered):
        """커버리지 제약조건"""
        s = self.target_style
        I_s = {s: list(set(df_sku_filtered['SKU'].tolist()) & set(scarce_skus))}
        
        for j in stores:
            if j not in target_stores:
                continue
                
            if not isinstance(color_coverage[(s,j)], LpVariable):
                continue
            
            # 색상 커버리지 제약
            color_covered = {}
            for k in K_s[s]:
                color_covered[k] = LpVariable(f"color_covered_{s}_{k}_{j}", cat=LpBinary)
                
                idx_color = [i for i in I_s[s] 
                           if df_sku_filtered.loc[df_sku_filtered['SKU']==i,'COLOR_CD'].iloc[0]==k 
                           and isinstance(b[i][j], LpVariable)]
                
                if idx_color:
                    self.prob += lpSum(b[i][j] for i in idx_color) >= color_covered[k]
                    for i in idx_color:
                        self.prob += b[i][j] <= color_covered[k]
                else:
                    self.prob += color_covered[k] == 0
            
            self.prob += color_coverage[(s,j)] == lpSum(color_covered[k] for k in K_s[s])
            
            # 사이즈 커버리지 제약
            size_covered = {}
            for l in L_s[s]:
                size_covered[l] = LpVariable(f"size_covered_{s}_{l}_{j}", cat=LpBinary)
                
                idx_size = [i for i in I_s[s] 
                          if df_sku_filtered.loc[df_sku_filtered['SKU']==i,'SIZE_CD'].iloc[0]==l 
                          and isinstance(b[i][j], LpVariable)]
                
                if idx_size:
                    self.prob += lpSum(b[i][j] for i in idx_size) >= size_covered[l]
                    for i in idx_size:
                        self.prob += b[i][j] <= size_covered[l]
                else:
                    self.prob += size_covered[l] == 0
            
            self.prob += size_coverage[(s,j)] == lpSum(size_covered[l] for l in L_s[s])
    
    def _save_results(self, b, scarce_skus, stores):
        """최적화 결과 저장"""
        self.b_hat = {}
        for i in scarce_skus:
            for j in stores:
                if isinstance(b[i][j], LpVariable):
                    self.b_hat[(i,j)] = int(b[i][j].value()) if b[i][j].value() is not None else 0
                else:
                    self.b_hat[(i,j)] = 0
    
    def _get_optimization_summary(self):
        """최적화 결과 요약"""
        if self.prob.status == 1:
            total_marked = sum(self.b_hat.values())
            print(f"✅ Step1 Coverage 최적화 완료!")
            print(f"   마킹된 SKU-매장 조합: {total_marked}개")
            
            return {
                'status': 'success',
                'total_marked': total_marked,
                'b_hat': self.b_hat
            }
        else:
            print(f"❌ Step1 Coverage 최적화 실패: 상태 {self.prob.status}")
            return {
                'status': 'failed',
                'problem_status': self.prob.status,
                'b_hat': {}
            }
    
    def get_marked_allocations(self):
        """마킹된 할당 결과 반환"""
        return self.b_hat 