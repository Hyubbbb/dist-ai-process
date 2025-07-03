"""
매장 Tier 시스템 관리 모듈 (SKU별 지정 매장 기반)
"""

from config import TIER_CONFIG


class StoreTierSystem:
    """SKU별 지정된 매장들에 대한 tier 분류 및 관리를 담당하는 클래스"""
    
    def __init__(self, tier_config=TIER_CONFIG):
        self.tier_config = tier_config
        self.tier_names = list(tier_config.keys())
        
        # Tier별 정보 추출
        self.tier_ratios = {name: config['ratio'] for name, config in tier_config.items()}
        self.tier_limits = {name: config['max_sku_limit'] for name, config in tier_config.items()}
        self.tier_displays = {name: config['display'] for name, config in tier_config.items()}
        
        # SKU별 지정된 배분 대상 매장 저장소 (향후 사용)
        self.sku_target_stores = {}
    
    def set_sku_target_stores(self, sku, target_stores, QSUM):
        """SKU별 배분 대상 매장 설정 (사람이 직접 지정)"""
        # QTY_SUM 기준으로 내림차순 정렬
        sorted_stores = sorted(target_stores, key=lambda x: QSUM.get(x, 0), reverse=True)
        self.sku_target_stores[sku] = sorted_stores
        return sorted_stores
    
    def get_sku_target_stores(self, sku, default_stores=None):
        """SKU별 배분 대상 매장 반환"""
        return self.sku_target_stores.get(sku, default_stores or [])
    
    def get_store_tier_for_sku(self, sku, store, QSUM):
        """SKU별 특정 매장의 tier 결정"""
        sku_stores = self.get_sku_target_stores(sku)
        
        if not sku_stores or store not in sku_stores:
            return 'TIER_3_LOW'  # 기본값
        
        # QTY_SUM 기준으로 정렬된 매장들 중에서 위치 찾기
        sorted_stores = sorted(sku_stores, key=lambda x: QSUM.get(x, 0), reverse=True)
        
        try:
            store_index = sorted_stores.index(store)
            total_stores = len(sorted_stores)
            
            # 30%, 20%, 50% 비율로 tier 분할
            tier1_count = int(total_stores * 0.3)
            tier2_count = int(total_stores * 0.2)
            
            if store_index < tier1_count:
                return 'TIER_1_HIGH'
            elif store_index < tier1_count + tier2_count:
                return 'TIER_2_MEDIUM'
            else:
                return 'TIER_3_LOW'
        except ValueError:
            return 'TIER_3_LOW'
    
    def get_store_tier_info_for_sku(self, store_id, sku, QSUM):
        """SKU별 특정 매장의 tier 정보 반환"""
        tier_name = self.get_store_tier_for_sku(sku, store_id, QSUM)
        tier_info = self.tier_config[tier_name]
        
        return {
            'store_id': store_id,
            'tier_name': tier_name,
            'tier_display': tier_info['display'],
            'max_sku_limit': tier_info['max_sku_limit'],
            'tier_ratio': tier_info['ratio'],
            'sku': sku
        }
    
    def get_max_allocatable_for_sku(self, sku, QSUM, A):
        """SKU별 최대 배분 가능량 계산 (tier 기반)"""
        sku_stores = self.get_sku_target_stores(sku)
        if not sku_stores:
            return A.get(sku, 0)  # 지정된 매장이 없으면 전체 공급량
        
        # 각 매장별 tier에 따른 최대 배분량 합계
        tier_based_capacity = 0
        for store in sku_stores:
            tier_info = self.get_store_tier_info_for_sku(store, sku, QSUM)
            tier_based_capacity += tier_info['max_sku_limit']
        
        # 실제 공급량과 tier 기반 용량 중 작은 값
        actual_supply = A.get(sku, 0)
        return min(actual_supply, tier_based_capacity)
    
    def create_store_allocation_limits_for_sku(self, sku, QSUM):
        """SKU별 매장 배분 상한 설정"""
        sku_stores = self.get_sku_target_stores(sku)
        if not sku_stores:
            return {}
        
        store_limits = {}
        for store in sku_stores:
            tier_info = self.get_store_tier_info_for_sku(store, sku, QSUM)
            store_limits[store] = tier_info['max_sku_limit']
        
        return store_limits
    
    def print_sku_tier_summary(self, sku, QSUM):
        """SKU별 tier 요약 정보 출력"""
        sku_stores = self.get_sku_target_stores(sku)
        if not sku_stores:
            print(f"   SKU {sku}: 배분 대상 매장이 지정되지 않음")
            return
        
        # QTY_SUM 기준으로 정렬
        sorted_stores = sorted(sku_stores, key=lambda x: QSUM.get(x, 0), reverse=True)
        total_stores = len(sorted_stores)
        
        # Tier별 매장 수 계산
        tier1_count = int(total_stores * 0.3)
        tier2_count = int(total_stores * 0.2)
        tier3_count = total_stores - tier1_count - tier2_count
        
        print(f"   SKU {sku} 배분 대상: {total_stores}개 매장")
        print(f"      🥇 T1 (HIGH): {tier1_count}개 매장 (SKU당 최대 3개)")
        print(f"      🥈 T2 (MED): {tier2_count}개 매장 (SKU당 최대 2개)")
        print(f"      🥉 T3 (LOW): {tier3_count}개 매장 (SKU당 최대 1개)")
        
        return {
            'TIER_1_HIGH': tier1_count,
            'TIER_2_MEDIUM': tier2_count,
            'TIER_3_LOW': tier3_count
        }
    
    # ========== 기존 메서드들 (하위 호환성 유지) ==========
    
    def get_store_tier(self, store_index, total_stores, sku=None):
        """매장 인덱스를 기반으로 tier 결정 (기본 시스템용)"""
        ratio_1 = self.tier_ratios['TIER_1_HIGH']
        ratio_2 = self.tier_ratios['TIER_2_MEDIUM']
        
        if store_index < total_stores * ratio_1:
            return 'TIER_1_HIGH'
        elif store_index < total_stores * (ratio_1 + ratio_2):
            return 'TIER_2_MEDIUM'
        else:
            return 'TIER_3_LOW'
    
    def get_target_stores(self, all_stores, target_style=None):
        """배분 대상 매장 결정 (기본 시스템용)"""
        return all_stores.copy()
    
    def get_store_tier_info(self, store_id, stores):
        """특정 매장의 tier 정보 반환 (기본 시스템용)"""
        try:
            store_index = stores.index(store_id)
            tier_name = self.get_store_tier(store_index, len(stores))
            tier_info = self.tier_config[tier_name]
            
            return {
                'store_id': store_id,
                'tier_name': tier_name,
                'tier_display': tier_info['display'],
                'max_sku_limit': tier_info['max_sku_limit'],
                'tier_ratio': tier_info['ratio']
            }
        except ValueError:
            raise ValueError(f"매장 {store_id}를 찾을 수 없습니다")
    
    def create_store_allocation_limits(self, stores, sku=None):
        """매장별 SKU 배분 상한 설정 (기본 시스템용)"""
        total_stores = len(stores)
        store_allocation_limits = {}
        
        for i, store_id in enumerate(stores):
            tier = self.get_store_tier(i, total_stores)
            store_allocation_limits[store_id] = self.tier_limits[tier]
        
        # 통계 출력
        print("🏆 매장 Tier 시스템 설정 완료:")
        tier_counts = {}
        for tier_name in self.tier_names:
            count = sum(1 for i in range(total_stores) 
                       if self.get_store_tier(i, total_stores) == tier_name)
            tier_counts[tier_name] = count
        
        for tier_name in self.tier_names:
            tier_info = self.tier_config[tier_name]
            count = tier_counts[tier_name]
            display = tier_info['display']
            limit = tier_info['max_sku_limit']
            print(f"   {display}: {count}개 매장 (SKU당 최대 {limit}개)")
        
        return store_allocation_limits
    
    def get_tier_info(self, tier_name):
        """특정 tier 정보 반환"""
        if tier_name not in self.tier_config:
            raise ValueError(f"알 수 없는 tier: {tier_name}")
        return self.tier_config[tier_name]
    
    def print_tier_summary(self, stores):
        """Tier 요약 정보 출력 (기본 시스템용)"""
        total_stores = len(stores)
        
        print("\n📊 매장 Tier 요약:")
        for tier_name in self.tier_names:
            tier_info = self.tier_config[tier_name]
            count = sum(1 for i in range(total_stores) 
                       if self.get_store_tier(i, total_stores) == tier_name)
            
            print(f"   {tier_info['display']}: {count}개 매장 "
                  f"({tier_info['ratio']*100:.0f}%, SKU당 최대 {tier_info['max_sku_limit']}개)")
        
        return {
            tier_name: sum(1 for i in range(total_stores) 
                          if self.get_store_tier(i, total_stores) == tier_name)
            for tier_name in self.tier_names
        } 