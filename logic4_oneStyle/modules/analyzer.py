"""
결과 분석 모듈
"""

import pandas as pd
import numpy as np


class ResultAnalyzer:
    """배분 결과 분석을 담당하는 클래스"""
    
    def __init__(self, target_style):
        self.target_style = target_style
        
    def analyze_results(self, final_allocation, data, scarce_skus, abundant_skus, 
                       target_stores, df_sku_filtered, QSUM, tier_system):
        """
        배분 결과 종합 분석
        
        Args:
            final_allocation: 최종 배분 결과
            data: 기본 데이터 구조
            scarce_skus: 희소 SKU 리스트
            abundant_skus: 충분 SKU 리스트
            target_stores: 배분 대상 매장 리스트
            df_sku_filtered: 필터링된 SKU 데이터프레임
            QSUM: 매장별 QTY_SUM
            tier_system: 매장 tier 시스템
        """
        print("\n" + "="*50)
        print("           📊 배분 결과 분석")
        print("="*50)
        
        # 1. 매장별 커버리지 계산
        store_coverage = self._calculate_store_coverage(final_allocation, data, target_stores, df_sku_filtered)
        
        # 2. 스타일별 컬러/사이즈 커버리지 계산
        style_coverage = self._calculate_style_coverage(store_coverage, data, target_stores)
        
        return {
            'store_coverage': store_coverage,
            'style_coverage': style_coverage,
        }
    
    def _calculate_store_coverage(self, final_allocation, data, target_stores, df_sku_filtered):
        """매장별 커버리지 계산"""
        K_s = data['K_s']
        L_s = data['L_s']
        
        store_coverage = {}
        
        for j in target_stores:
            # 해당 매장에 할당된 SKU들
            allocated_skus = [sku for (sku, store), qty in final_allocation.items() 
                            if store == j and qty > 0]
            
            # 커버된 색상들
            covered_colors = set()
            for sku in allocated_skus:
                color = df_sku_filtered.loc[df_sku_filtered['SKU']==sku, 'COLOR_CD'].iloc[0]
                covered_colors.add(color)
            
            # 커버된 사이즈들
            covered_sizes = set()
            for sku in allocated_skus:
                size = df_sku_filtered.loc[df_sku_filtered['SKU']==sku, 'SIZE_CD'].iloc[0]
                covered_sizes.add(size)
            
            store_coverage[j] = {
                'colors': covered_colors,
                'sizes': covered_sizes,
                'allocated_skus': allocated_skus,
                'total_allocated': sum(qty for (sku, store), qty in final_allocation.items() if store == j)
            }
        
        return store_coverage
    
    def _calculate_style_coverage(self, store_coverage, data, target_stores):
        """스타일별 컬러/사이즈 커버리지 계산"""
        K_s = data['K_s']
        L_s = data['L_s']
        s = self.target_style
        
        total_colors = len(K_s[s])
        total_sizes = len(L_s[s])
        
        # 색상 커버리지 비율
        color_ratios = []
        for j in target_stores:
            covered_colors = len(store_coverage[j]['colors'])
            ratio = covered_colors / total_colors if total_colors > 0 else 0
            color_ratios.append(ratio)
        
        # 사이즈 커버리지 비율
        size_ratios = []
        for j in target_stores:
            covered_sizes = len(store_coverage[j]['sizes'])
            ratio = covered_sizes / total_sizes if total_sizes > 0 else 0
            size_ratios.append(ratio)
        
        return {
            'color_coverage': {
                'total_colors': total_colors,
                'store_ratios': color_ratios,
                'avg_ratio': np.mean(color_ratios),
                'max_ratio': np.max(color_ratios),
                'min_ratio': np.min(color_ratios)
            },
            'size_coverage': {
                'total_sizes': total_sizes,
                'store_ratios': size_ratios,
                'avg_ratio': np.mean(size_ratios),
                'max_ratio': np.max(size_ratios),
                'min_ratio': np.min(size_ratios)
            }
        }
    
    def create_result_dataframes(self, final_allocation, data, scarce_skus, target_stores, 
                               df_sku_filtered, tier_system, b_hat=None):
        """결과를 DataFrame으로 변환"""
        A = data['A']
        allocation_results = []
        
        for (sku, store), qty in final_allocation.items():
            if qty > 0:
                # SKU 정보 파싱
                part_cd, color_cd, size_cd = sku.split('_')
                
                # 매장 tier 정보
                try:
                    tier_info = tier_system.get_store_tier_info(store, target_stores)
                    store_tier = tier_info['tier_name']
                    max_sku_limit = tier_info['max_sku_limit']
                except:
                    store_tier = 'UNKNOWN'
                    max_sku_limit = 1
                
                allocation_results.append({
                    'SKU': sku,
                    'PART_CD': part_cd,
                    'COLOR_CD': color_cd,
                    'SIZE_CD': size_cd,
                    'SHOP_ID': store,
                    'ALLOCATED_QTY': qty,
                    'SUPPLY_QTY': A[sku],
                    'SKU_TYPE': 'scarce' if sku in scarce_skus else 'abundant',
                    'STORE_TIER': store_tier,
                    'MAX_SKU_LIMIT': max_sku_limit
                })
        
        return pd.DataFrame(allocation_results) 