"""
매장 Tier 시스템 관리 모듈
"""

from config import TIER_CONFIG


class StoreTierSystem:
    """매장 tier 분류 및 관리를 담당하는 클래스"""
    
    def __init__(self, tier_config=TIER_CONFIG):
        self.tier_config = tier_config
        self.tier_names = list(tier_config.keys())
        
        # Tier별 정보 추출
        self.tier_ratios = {name: config['ratio'] for name, config in tier_config.items()}
        self.tier_limits = {name: config['max_sku_limit'] for name, config in tier_config.items()}
        self.tier_displays = {name: config['display'] for name, config in tier_config.items()}
        
    def get_store_tier(self, store_index, total_stores):
        """매장 인덱스를 기반으로 tier 결정"""
        ratio_1 = self.tier_ratios['TIER_1_HIGH']
        ratio_2 = self.tier_ratios['TIER_2_MEDIUM']
        
        if store_index < total_stores * ratio_1:
            return 'TIER_1_HIGH'
        elif store_index < total_stores * (ratio_1 + ratio_2):
            return 'TIER_2_MEDIUM'
        else:
            return 'TIER_3_LOW'
    
    def create_store_allocation_limits(self, stores):
        """매장별 SKU 배분 상한 설정"""
        total_stores = len(stores)
        store_allocation_limits = {}
        
        # 각 매장별 tier 결정 및 배분 상한 설정
        for i, store_id in enumerate(stores):
            tier = self.get_store_tier(i, total_stores)
            store_allocation_limits[store_id] = self.tier_limits[tier]
        
        # 통계 계산
        tier_counts = {}
        for tier_name in self.tier_names:
            count = sum(1 for i in range(total_stores) 
                       if self.get_store_tier(i, total_stores) == tier_name)
            tier_counts[tier_name] = count
        
        print("🏆 매장 Tier 시스템 설정 완료:")
        for tier_name in self.tier_names:
            ratio = self.tier_ratios[tier_name]
            limit = self.tier_limits[tier_name]
            count = tier_counts[tier_name]
            display = self.tier_displays[tier_name]
            print(f"   {display}: {count}개 매장 (SKU당 최대 {limit}개)")
        
        return store_allocation_limits
    
    def get_target_stores(self, all_stores, target_style=None):
        """배분 대상 매장 결정 (현재는 모든 매장)"""
        # 향후 스타일별 매장 제한 로직 추가 가능
        return all_stores.copy()
    
    def get_tier_info(self, tier_name):
        """특정 tier 정보 반환"""
        if tier_name not in self.tier_config:
            raise ValueError(f"알 수 없는 tier: {tier_name}")
        return self.tier_config[tier_name]
    
    def get_store_tier_info(self, store_id, stores):
        """특정 매장의 tier 정보 반환"""
        try:
            store_index = stores.index(store_id)
            tier_name = self.get_store_tier(store_index, len(stores))
            tier_info = self.get_tier_info(tier_name)
            
            return {
                'store_id': store_id,
                'tier_name': tier_name,
                'tier_display': tier_info['display'],
                'max_sku_limit': tier_info['max_sku_limit'],
                'tier_ratio': tier_info['ratio']
            }
        except ValueError:
            raise ValueError(f"매장 {store_id}를 찾을 수 없습니다")
    
    def print_tier_summary(self, stores):
        """Tier 요약 정보 출력"""
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