"""
결정론적 추가 배분 모듈 (Step2)
"""


class GreedyAllocator:
    """결정론적 그리디 알고리즘을 통한 추가 배분을 담당하는 클래스"""
    
    def __init__(self, tier_system):
        self.tier_system = tier_system
        self.final_allocation = {}
        self.current_supply = {}
        
    def allocate(self, data, b_hat, scarce_skus, abundant_skus, target_stores, 
                store_allocation_limits, QSUM):
        """
        결정론적 추가 배분 실행
        
        Args:
            data: 기본 데이터 구조 (A, SKUs 등)
            b_hat: Step1에서 마킹된 할당 결과
            scarce_skus: 희소 SKU 리스트
            abundant_skus: 충분 SKU 리스트  
            target_stores: 배분 대상 매장 리스트
            store_allocation_limits: 매장별 SKU 배분 상한
            QSUM: 매장별 QTY_SUM
        """
        A = data['A']
        SKUs = data['SKUs']
        
        print(f"🚀 Step2: 결정론적 추가 배분 시작")
        print(f"   총 SKU: {len(SKUs)}개 (희소: {len(scarce_skus)}개, 충분: {len(abundant_skus)}개)")
        print(f"   대상 매장: {len(target_stores)}개")
        
        # 1. 우선 배분 수행
        priority_allocation = self._priority_allocation(b_hat, scarce_skus, target_stores, A)
        
        # 2. 매장별 추가 배분
        self._additional_allocation(priority_allocation, A, SKUs, scarce_skus, abundant_skus, 
                                  target_stores, store_allocation_limits, QSUM)
        
        # 3. 추가 수량 배분 (tier 제한 내에서)
        self._quantity_increase_allocation(target_stores, store_allocation_limits)
        
        return self._get_allocation_summary(A)
    
    def _priority_allocation(self, b_hat, scarce_skus, target_stores, A):
        """우선 배분: Step1에서 마킹된 희소 SKU들을 1개씩 배분"""
        priority_allocation = {}
        remaining_supply = A.copy()
        priority_count = 0
        
        print("🔄 우선 배분 진행...")
        
        for i in scarce_skus:
            for j in target_stores:
                if b_hat.get((i,j), 0) == 1:
                    if remaining_supply[i] > 0:
                        priority_allocation[(i,j)] = 1
                        remaining_supply[i] -= 1
                        priority_count += 1
        
        print(f"   우선 배분 완료: {priority_count}개")
        
        self.final_allocation = priority_allocation
        self.current_supply = remaining_supply
        
        return priority_allocation
    
    def _additional_allocation(self, priority_allocation, A, SKUs, scarce_skus, abundant_skus,
                             target_stores, store_allocation_limits, QSUM):
        """매장별 추가 배분"""
        print("🔄 매장별 추가 배분 진행...")
        
        allocated_stores = 0
        
        for store_idx, store_id in enumerate(target_stores):
            # 매장 tier 정보 가져오기
            tier_info = self.tier_system.get_store_tier_info(store_id, target_stores)
            max_skus_per_store = tier_info['max_sku_limit']
            
            # 현재 매장에 이미 배분된 SKU 개수
            current_allocated = len([sku for (sku, store), qty in self.final_allocation.items() 
                                   if store == store_id and qty > 0])
            
            # 추가 배분 가능한 SKU 개수
            additional_slots = max_skus_per_store - current_allocated
            
            if additional_slots <= 0:
                continue
            
            # 배분 후보 SKU 준비 (희소 SKU 우선)
            candidate_skus = self._get_candidate_skus(scarce_skus, abundant_skus, store_id)
            
            # 추가 배분 실행
            allocated_in_round = self._allocate_to_store(store_id, candidate_skus, additional_slots, 
                                                       tier_info)
            
            if allocated_in_round > 0:
                allocated_stores += 1
        
        print(f"   추가 배분 완료: {allocated_stores}개 매장")
    
    def _get_candidate_skus(self, scarce_skus, abundant_skus, store_id):
        """배분 후보 SKU 리스트 생성"""
        candidate_skus = []
        
        # 희소 SKU 우선
        for sku in scarce_skus:
            if self.current_supply[sku] > 0 and (sku, store_id) not in self.final_allocation:
                candidate_skus.append((sku, 'scarce', self.current_supply[sku]))
        
        # 충분 SKU
        for sku in abundant_skus:
            if self.current_supply[sku] > 0 and (sku, store_id) not in self.final_allocation:
                candidate_skus.append((sku, 'abundant', self.current_supply[sku]))
        
        # 희소 SKU 우선, 같은 타입 내에서는 수량 적은 순
        candidate_skus.sort(key=lambda x: (0 if x[1] == 'scarce' else 1, x[2]))
        
        return candidate_skus
    
    def _allocate_to_store(self, store_id, candidate_skus, additional_slots, tier_info):
        """특정 매장에 SKU 배분"""
        allocated_count = 0
        max_qty_per_sku = tier_info['max_sku_limit']
        
        for sku, sku_type, available_qty in candidate_skus:
            if allocated_count >= additional_slots:
                break
            
            # 일단 1개씩만 배분
            allocated_qty = min(max_qty_per_sku, available_qty, 1)
            
            if allocated_qty > 0:
                self.final_allocation[(sku, store_id)] = allocated_qty
                self.current_supply[sku] -= allocated_qty
                allocated_count += 1
        
        return allocated_count
    
    def _quantity_increase_allocation(self, target_stores, store_allocation_limits):
        """기존 배분된 SKU들의 수량 증가"""
        print("🔄 수량 증가 배분...")
        
        additional_allocated = 0
        
        for store_idx, store_id in enumerate(target_stores):
            tier = self.tier_system.get_store_tier(store_idx, len(target_stores))
            max_qty_per_sku = self.tier_system.tier_limits[tier]
            
            if max_qty_per_sku == 1:
                continue  # Tier 3는 추가 불가
            
            # 이 매장에 배분된 SKU들의 수량 증가
            store_allocations = [(sku, qty) for (sku, store), qty in self.final_allocation.items() 
                               if store == store_id]
            
            for sku, current_qty in store_allocations:
                if current_qty < max_qty_per_sku and self.current_supply[sku] > 0:
                    additional_qty = min(max_qty_per_sku - current_qty, self.current_supply[sku])
                    self.final_allocation[(sku, store_id)] += additional_qty
                    self.current_supply[sku] -= additional_qty
                    additional_allocated += additional_qty
        
        if additional_allocated > 0:
            print(f"   수량 증가 완료: {additional_allocated}개")
    
    def _get_allocation_summary(self, A):
        """배분 결과 요약"""
        total_final_allocation = sum(self.final_allocation.values())
        total_remaining = sum(self.current_supply.values())
        total_original = sum(A.values())
        
        print(f"\n✅ Step2 결정론적 배분 완료!")
        print(f"   총 배분량: {total_final_allocation:,}개")
        print(f"   남은 수량: {total_remaining:,}개")
        print(f"   배분률: {total_final_allocation/total_original*100:.1f}%")
        
        # 매장별 배분 현황
        store_allocation_summary = {}
        for (sku, store), qty in self.final_allocation.items():
            if store not in store_allocation_summary:
                store_allocation_summary[store] = {'sku_count': 0, 'total_qty': 0}
            store_allocation_summary[store]['sku_count'] += 1
            store_allocation_summary[store]['total_qty'] += qty
        
        allocated_stores = len(store_allocation_summary)
        print(f"   배분 받은 매장: {allocated_stores}개")
        
        # SKU 타입별 배분 현황
        scarce_allocated = sum(qty for (sku, store), qty in self.final_allocation.items() 
                             if sku in (self.scarce_skus if hasattr(self, 'scarce_skus') else []))
        abundant_allocated = sum(qty for (sku, store), qty in self.final_allocation.items() 
                               if sku in (self.abundant_skus if hasattr(self, 'abundant_skus') else []))
        
        return {
            'status': 'success',
            'total_allocated': total_final_allocation,
            'total_remaining': total_remaining,
            'allocation_rate': total_final_allocation/total_original,
            'allocated_stores': allocated_stores,
            'final_allocation': self.final_allocation,
            'remaining_supply': self.current_supply
        }
    
    def convert_to_matrix_format(self, SKUs, target_stores):
        """결과를 기존 x[i][j] 매트릭스 형태로 변환"""
        x = {}
        for i in SKUs:
            x[i] = {}
            for j in target_stores:
                x[i][j] = self.final_allocation.get((i, j), 0)
        return x
    
    def get_allocation_results(self):
        """최종 할당 결과 반환"""
        return self.final_allocation 