"""
SKU 분류 모듈 (희소/충분 SKU 구분)
"""

import pandas as pd


class SKUClassifier:
    """SKU를 희소/충분으로 분류하는 클래스"""
    
    def __init__(self, df_sku_filtered):
        self.df_sku_filtered = df_sku_filtered
        self.scarce_skus = []
        self.abundant_skus = []
        
    def classify_skus(self, A, target_stores):
        """SKU를 희소/충분으로 분류"""
        SKUs = list(A.keys())
        num_target_stores = len(target_stores)
        
        print(f"🔍 SKU 분류 시작:")
        print(f"   배분 대상 매장 수: {num_target_stores}개")
        print(f"   희소 SKU 기준: 수량 < {num_target_stores}개")
        
        # 기본 희소 SKU 식별
        basic_scarce = [sku for sku, qty in A.items() if qty < num_target_stores]
        
        # 확장된 희소 SKU 그룹 생성 (관련 SKU 추가)
        extended_scarce = set(basic_scarce)
        
        for scarce_sku in basic_scarce:
            # 해당 SKU의 색상, 사이즈 추출
            color = self.df_sku_filtered.loc[self.df_sku_filtered['SKU']==scarce_sku, 'COLOR_CD'].iloc[0]
            size = self.df_sku_filtered.loc[self.df_sku_filtered['SKU']==scarce_sku, 'SIZE_CD'].iloc[0]
            
            # 동일 스타일에서 관련 SKU들 찾기
            for related_sku in SKUs:
                if related_sku != scarce_sku:
                    related_color = self.df_sku_filtered.loc[self.df_sku_filtered['SKU']==related_sku, 'COLOR_CD'].iloc[0]
                    related_size = self.df_sku_filtered.loc[self.df_sku_filtered['SKU']==related_sku, 'SIZE_CD'].iloc[0]
                    
                    # 같은 색상 다른 사이즈 OR 같은 사이즈 다른 색상
                    if (color == related_color and size != related_size) or \
                       (color != related_color and size == related_size):
                        extended_scarce.add(related_sku)
        
        self.scarce_skus = list(extended_scarce)
        self.abundant_skus = [sku for sku in SKUs if sku not in self.scarce_skus]
        
        print(f"   기본 희소 SKU: {len(basic_scarce)}개")
        print(f"   확장 희소 SKU: {len(self.scarce_skus)}개")
        print(f"   충분 SKU: {len(self.abundant_skus)}개")
        
        return self.scarce_skus, self.abundant_skus
    
    def get_sku_type(self, sku):
        """특정 SKU의 타입 반환"""
        if sku in self.scarce_skus:
            return 'scarce'
        elif sku in self.abundant_skus:
            return 'abundant'
        else:
            return 'unknown'
    
    def get_sku_info(self, sku):
        """특정 SKU의 상세 정보 반환"""
        if sku not in self.df_sku_filtered['SKU'].values:
            return None
            
        row = self.df_sku_filtered[self.df_sku_filtered['SKU'] == sku].iloc[0]
        
        return {
            'sku': sku,
            'part_cd': row['PART_CD'],
            'color_cd': row['COLOR_CD'],
            'size_cd': row['SIZE_CD'],
            'ord_qty': row['ORD_QTY'],
            'sku_type': self.get_sku_type(sku)
        }
    
    def get_color_size_summary(self):
        """색상별, 사이즈별 SKU 분포 요약"""
        color_summary = {}
        size_summary = {}
        
        # 색상별 요약
        for color in self.df_sku_filtered['COLOR_CD'].unique():
            color_skus = self.df_sku_filtered[self.df_sku_filtered['COLOR_CD'] == color]['SKU'].tolist()
            color_scarce = [sku for sku in color_skus if sku in self.scarce_skus]
            color_abundant = [sku for sku in color_skus if sku in self.abundant_skus]
            
            color_summary[color] = {
                'total_skus': len(color_skus),
                'scarce_skus': len(color_scarce),
                'abundant_skus': len(color_abundant),
                'total_qty': self.df_sku_filtered[self.df_sku_filtered['COLOR_CD'] == color]['ORD_QTY'].sum()
            }
        
        # 사이즈별 요약
        for size in self.df_sku_filtered['SIZE_CD'].unique():
            size_skus = self.df_sku_filtered[self.df_sku_filtered['SIZE_CD'] == size]['SKU'].tolist()
            size_scarce = [sku for sku in size_skus if sku in self.scarce_skus]
            size_abundant = [sku for sku in size_skus if sku in self.abundant_skus]
            
            size_summary[size] = {
                'total_skus': len(size_skus),
                'scarce_skus': len(size_scarce),
                'abundant_skus': len(size_abundant),
                'total_qty': self.df_sku_filtered[self.df_sku_filtered['SIZE_CD'] == size]['ORD_QTY'].sum()
            }
        
        return color_summary, size_summary
    
    def print_detailed_summary(self, A, show_details=False):
        """상세 분류 결과 출력"""
        print("\n📊 SKU 분류 상세 결과:")
        
        if show_details and len(self.scarce_skus) <= 10:
            print(f"\n🔴 희소 SKU 목록:")
            for sku in self.scarce_skus:
                info = self.get_sku_info(sku)
                print(f"   {sku}: {A[sku]}개 (색상:{info['color_cd']}, 사이즈:{info['size_cd']})")
        
        if show_details and len(self.abundant_skus) <= 10:
            print(f"\n🟢 충분 SKU 목록:")
            for sku in self.abundant_skus[:5]:
                info = self.get_sku_info(sku)
                print(f"   {sku}: {A[sku]}개 (색상:{info['color_cd']}, 사이즈:{info['size_cd']})")
            if len(self.abundant_skus) > 5:
                print(f"   + 추가 {len(self.abundant_skus)-5}개 SKU...")
        
        # 색상/사이즈별 요약
        color_summary, size_summary = self.get_color_size_summary()
        
        print(f"\n🎨 색상별 분포:")
        for color, stats in color_summary.items():
            print(f"   {color}: 총 {stats['total_skus']}개 SKU "
                  f"(희소: {stats['scarce_skus']}개, 충분: {stats['abundant_skus']}개)")
        
        print(f"\n📏 사이즈별 분포:")
        for size, stats in size_summary.items():
            print(f"   {size}: 총 {stats['total_skus']}개 SKU "
                  f"(희소: {stats['scarce_skus']}개, 충분: {stats['abundant_skus']}개)")
    
    def get_classification_stats(self):
        """분류 통계 반환"""
        return {
            'total_skus': len(self.scarce_skus) + len(self.abundant_skus),
            'scarce_count': len(self.scarce_skus),
            'abundant_count': len(self.abundant_skus),
            'scarce_ratio': len(self.scarce_skus) / (len(self.scarce_skus) + len(self.abundant_skus)),
            'abundant_ratio': len(self.abundant_skus) / (len(self.scarce_skus) + len(self.abundant_skus))
        } 