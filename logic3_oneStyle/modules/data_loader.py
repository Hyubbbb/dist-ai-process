"""
데이터 로드 및 전처리 모듈
"""

import pandas as pd
import os
from config import DATA_PATH


class DataLoader:
    """데이터 로드 및 전처리를 담당하는 클래스"""
    
    def __init__(self, data_path=DATA_PATH):
        self.data_path = data_path
        self.df_sku = None
        self.df_store = None
        self.target_style = None
        self.df_sku_filtered = None
        
    def load_data(self):
        """기본 데이터 로드"""
        print("📊 데이터 로드 중...")
        
        # SKU 데이터 로드
        sku_file = os.path.join(self.data_path, '발주수량.csv')
        self.df_sku = pd.read_csv(sku_file)
        
        # 매장 데이터 로드
        store_file = os.path.join(self.data_path, '매장데이터.csv')
        self.df_store = pd.read_csv(store_file)
        
        # 매장 데이터를 QTY_SUM 기준 내림차순 정렬
        self.df_store = self.df_store.sort_values('QTY_SUM', ascending=False).reset_index(drop=True)
        
        print(f"✅ 데이터 로드 완료 - SKU: {len(self.df_sku)}개, 매장: {len(self.df_store)}개")
        return self.df_sku, self.df_store
    
    def filter_by_style(self, target_style):
        """특정 스타일로 필터링"""
        self.target_style = target_style
        
        # 사용 가능한 스타일 확인
        available_styles = self.df_sku['PART_CD'].unique().tolist()
        
        if target_style not in available_styles:
            raise ValueError(f"스타일 '{target_style}'이 존재하지 않습니다. 사용 가능: {available_styles}")
        
        # 선택된 스타일로 필터링
        self.df_sku_filtered = self.df_sku[self.df_sku['PART_CD'] == target_style].copy()
        
        # SKU 식별자 생성
        self.df_sku_filtered['SKU'] = (
            self.df_sku_filtered['PART_CD'] + '_' + 
            self.df_sku_filtered['COLOR_CD'] + '_' + 
            self.df_sku_filtered['SIZE_CD']
        )
        
        print(f"🎯 스타일 '{target_style}' 필터링 완료:")
        print(f"   SKU 개수: {len(self.df_sku_filtered)}개")
        print(f"   색상: {self.df_sku_filtered['COLOR_CD'].nunique()}종류")
        print(f"   사이즈: {self.df_sku_filtered['SIZE_CD'].nunique()}종류")
        print(f"   총 수량: {self.df_sku_filtered['ORD_QTY'].sum():,}개")
        
        return self.df_sku_filtered
    
    def get_basic_data_structures(self):
        """기본 데이터 구조 반환"""
        if self.df_sku_filtered is None:
            raise ValueError("먼저 filter_by_style()을 호출하세요")
            
        # SKU 데이터
        A = self.df_sku_filtered.set_index('SKU')['ORD_QTY'].to_dict()
        SKUs = list(A.keys())
        
        # 매장 데이터  
        stores = self.df_store['SHOP_ID'].tolist()
        QSUM = self.df_store.set_index('SHOP_ID')['QTY_SUM'].to_dict()
        
        # 스타일별 색상/사이즈 그룹
        styles = [self.target_style]
        I_s = {self.target_style: SKUs}
        K_s = {self.target_style: self.df_sku_filtered['COLOR_CD'].unique().tolist()}
        L_s = {self.target_style: self.df_sku_filtered['SIZE_CD'].unique().tolist()}
        
        return {
            'A': A,           # SKU별 공급량
            'SKUs': SKUs,     # SKU 리스트  
            'stores': stores, # 매장 리스트 (QTY_SUM 내림차순)
            'QSUM': QSUM,     # 매장별 QTY_SUM
            'styles': styles, # 스타일 리스트
            'I_s': I_s,       # 스타일별 SKU 그룹
            'K_s': K_s,       # 스타일별 색상 그룹
            'L_s': L_s        # 스타일별 사이즈 그룹
        }
    
    def get_summary_stats(self):
        """요약 통계 반환"""
        if self.df_sku_filtered is None or self.df_store is None:
            return None
            
        return {
            'target_style': self.target_style,
            'total_skus': len(self.df_sku_filtered),
            'total_stores': len(self.df_store),
            'total_quantity': self.df_sku_filtered['ORD_QTY'].sum(),
            'avg_quantity_per_sku': self.df_sku_filtered['ORD_QTY'].mean(),
            'unique_colors': self.df_sku_filtered['COLOR_CD'].nunique(),
            'unique_sizes': self.df_sku_filtered['SIZE_CD'].nunique(),
            'max_store_qty_sum': self.df_store['QTY_SUM'].iloc[0],
            'min_store_qty_sum': self.df_store['QTY_SUM'].iloc[-1],
            'avg_store_qty_sum': self.df_store['QTY_SUM'].mean()
        } 