"""
데이터 로딩 및 전처리 모듈

이 모듈은 SKU 및 매장 데이터를 로드하고 최적화에 필요한 형태로 전처리합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Set
import logging


class DataLoader:
    """데이터 로딩 및 전처리 클래스"""
    
    def __init__(self, sku_file_path: str, store_file_path: str):
        """
        데이터 로더 초기화
        
        Args:
            sku_file_path: SKU 데이터 파일 경로
            store_file_path: 매장 데이터 파일 경로
        """
        self.sku_file_path = sku_file_path
        self.store_file_path = store_file_path
        self.logger = logging.getLogger(__name__)
        
        # 데이터 저장 변수들
        self.df_sku = None
        self.df_store = None
        self.A = {}  # SKU별 공급량
        self.SKUs = []  # 전체 SKU 리스트
        self.stores = []  # 매장 리스트
        self.QSUM = {}  # 매장별 판매량
        self.scarce = []  # 희소 SKU
        self.abundant = []  # 충분한 SKU
        self.styles = []  # 스타일 리스트
        self.I_s = {}  # 스타일별 SKU 그룹
        self.K_s = {}  # 스타일별 색상 그룹
        self.L_s = {}  # 스타일별 사이즈 그룹
    
    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        데이터 파일을 로드합니다.
        
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (SKU 데이터, 매장 데이터)
        """
        try:
            self.df_sku = pd.read_csv(self.sku_file_path)
            self.df_store = pd.read_csv(self.store_file_path)
            
            self.logger.info(f"SKU 데이터 로드 완료: {len(self.df_sku)} 행")
            self.logger.info(f"매장 데이터 로드 완료: {len(self.df_store)} 행")
            
            return self.df_sku, self.df_store
            
        except Exception as e:
            self.logger.error(f"데이터 로드 실패: {e}")
            raise
    
    def preprocess_data(self) -> Dict:
        """
        데이터를 전처리하고 최적화에 필요한 형태로 변환합니다.
        
        Returns:
            Dict: 전처리된 데이터 딕셔너리
        """
        if self.df_sku is None or self.df_store is None:
            self.load_data()
        
        # SKU 식별자 및 공급량 생성
        self._create_sku_identifiers()
        
        # 매장 데이터 전처리
        self._preprocess_store_data()
        
        # 희소/충분 SKU 분류
        self._classify_skus()
        
        # 스타일별 그룹핑
        self._create_style_groups()
        
        return self._get_processed_data()
    
    def _create_sku_identifiers(self):
        """SKU 식별자 및 공급량 딕셔너리 생성"""
        self.df_sku['SKU'] = (self.df_sku['PART_CD'] + '_' + 
                              self.df_sku['COLOR_CD'] + '_' + 
                              self.df_sku['SIZE_CD'])
        
        self.A = self.df_sku.set_index('SKU')['ORD_QTY'].to_dict()
        self.SKUs = list(self.A.keys())
        
        self.logger.info(f"총 {len(self.SKUs)}개 SKU 생성")
    
    def _preprocess_store_data(self):
        """매장 데이터 전처리"""
        self.stores = self.df_store['SHOP_ID'].tolist()
        self.QSUM = self.df_store.set_index('SHOP_ID')['QTY_SUM'].to_dict()
        
        self.logger.info(f"총 {len(self.stores)}개 매장")
    
    def _classify_skus(self):
        """희소/충분 SKU 분류 (확장된 분류 적용)"""
        num_stores = len(self.stores)
        
        # 기본 희소 SKU 식별
        basic_scarce = [i for i, qty in self.A.items() if qty < num_stores]
        
        # 확장된 희소 SKU 그룹 생성
        extended_scarce = set(basic_scarce)
        
        for scarce_sku in basic_scarce:
            # 해당 SKU의 스타일, 색상, 사이즈 추출
            style = self.df_sku.loc[self.df_sku['SKU']==scarce_sku, 'PART_CD'].iloc[0]
            color = self.df_sku.loc[self.df_sku['SKU']==scarce_sku, 'COLOR_CD'].iloc[0]
            size = self.df_sku.loc[self.df_sku['SKU']==scarce_sku, 'SIZE_CD'].iloc[0]
            
            # 동일 스타일에서 관련 SKU들 찾기
            same_style_skus = self.df_sku[self.df_sku['PART_CD'] == style]['SKU'].tolist()
            
            for related_sku in same_style_skus:
                if related_sku in self.SKUs:
                    related_color = self.df_sku.loc[self.df_sku['SKU']==related_sku, 'COLOR_CD'].iloc[0]
                    related_size = self.df_sku.loc[self.df_sku['SKU']==related_sku, 'SIZE_CD'].iloc[0]
                    
                    # 같은 색상 다른 사이즈 OR 같은 사이즈 다른 색상
                    if ((color == related_color and size != related_size) or 
                        (color != related_color and size == related_size)):
                        extended_scarce.add(related_sku)
        
        self.scarce = list(extended_scarce)
        self.abundant = [i for i in self.SKUs if i not in self.scarce]
        
        self.logger.info(f"희소 SKU: {len(self.scarce)}개")
        self.logger.info(f"충분한 SKU: {len(self.abundant)}개")
    
    def _create_style_groups(self):
        """스타일별 색상/사이즈 그룹 생성"""
        self.styles = self.df_sku['PART_CD'].unique().tolist()
        
        self.I_s = {s: self.df_sku[self.df_sku['PART_CD']==s]['SKU'].tolist() 
                    for s in self.styles}
        
        self.K_s = {s: self.df_sku[self.df_sku['PART_CD']==s]['COLOR_CD'].unique().tolist() 
                    for s in self.styles}
        
        self.L_s = {s: self.df_sku[self.df_sku['PART_CD']==s]['SIZE_CD'].unique().tolist() 
                    for s in self.styles}
        
        self.logger.info(f"총 {len(self.styles)}개 스타일")
    
    def _get_processed_data(self) -> Dict:
        """전처리된 데이터를 딕셔너리로 반환"""
        return {
            'df_sku': self.df_sku,
            'df_store': self.df_store,
            'A': self.A,  # SKU별 공급량
            'SKUs': self.SKUs,  # 전체 SKU 리스트
            'stores': self.stores,  # 매장 리스트
            'QSUM': self.QSUM,  # 매장별 판매량
            'scarce': self.scarce,  # 희소 SKU
            'abundant': self.abundant,  # 충분한 SKU
            'styles': self.styles,  # 스타일 리스트
            'I_s': self.I_s,  # 스타일별 SKU 그룹
            'K_s': self.K_s,  # 스타일별 색상 그룹
            'L_s': self.L_s   # 스타일별 사이즈 그룹
        }
    
    def get_data_summary(self) -> str:
        """데이터 요약 정보를 문자열로 반환"""
        if not self.SKUs:
            return "데이터가 로드되지 않았습니다."
        
        summary = f"""
        📊 데이터 요약:
        • 총 SKU 수: {len(self.SKUs)}개
        • 희소 SKU: {len(self.scarce)}개 ({len(self.scarce)/len(self.SKUs)*100:.1f}%)
        • 충분한 SKU: {len(self.abundant)}개 ({len(self.abundant)/len(self.SKUs)*100:.1f}%)
        • 총 매장 수: {len(self.stores)}개
        • 스타일 수: {len(self.styles)}개
        • 총 공급량: {sum(self.A.values()):,}개
        • 평균 매장 판매량: {sum(self.QSUM.values())/len(self.QSUM):,.0f}개
        """
        return summary
    
    def validate_data(self) -> List[str]:
        """데이터 유효성 검증"""
        issues = []
        
        if not self.SKUs:
            issues.append("SKU 데이터가 없습니다.")
        
        if not self.stores:
            issues.append("매장 데이터가 없습니다.")
        
        # 중복 SKU 확인
        if len(self.SKUs) != len(set(self.SKUs)):
            issues.append("중복된 SKU가 있습니다.")
        
        # 음수 공급량 확인
        negative_supply = [sku for sku, qty in self.A.items() if qty < 0]
        if negative_supply:
            issues.append(f"음수 공급량이 있는 SKU: {len(negative_supply)}개")
        
        # 빈 스타일 그룹 확인
        empty_styles = [s for s in self.styles if not self.I_s.get(s)]
        if empty_styles:
            issues.append(f"빈 스타일 그룹: {empty_styles}")
        
        return issues 