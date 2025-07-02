"""
결과 분석 모듈

이 모듈은 최적화 결과를 다양한 관점에서 분석하고 성과 메트릭을 계산합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
import logging


class ResultAnalyzer:
    """결과 분석 클래스"""
    
    def __init__(self, data: Dict[str, Any], optimizer):
        """
        분석기 초기화
        
        Args:
            data: 전처리된 데이터
            optimizer: 최적화 결과가 포함된 SKUOptimizer 인스턴스
        """
        self.data = data
        self.optimizer = optimizer
        self.logger = logging.getLogger(__name__)
        
        # 데이터 추출
        self.df_sku = data['df_sku']
        self.df_store = data['df_store']
        self.A = data['A']
        self.SKUs = data['SKUs']
        self.stores = data['stores']
        self.QSUM = data['QSUM']
        self.scarce = data['scarce']
        self.abundant = data['abundant']
        self.styles = data['styles']
        self.I_s = data['I_s']
        self.K_s = data['K_s']
        self.L_s = data['L_s']
        
        # 결과 데이터
        self.allocation_df = None
        self.store_summary_df = None
        
    def analyze(self) -> Dict[str, pd.DataFrame]:
        """
        전체 분석 수행
        
        Returns:
            Dict[str, pd.DataFrame]: 분석 결과 DataFrame들
        """
        self.logger.info("결과 분석 시작...")
        
        # 기본 데이터 준비
        self.allocation_df = self.optimizer.get_allocation_results()
        self.store_summary_df = self.optimizer.get_store_summary()
        
        if self.allocation_df.empty:
            self.logger.warning("할당 결과가 없습니다.")
            return self._get_empty_results()
        
        # 각종 분석 수행
        analysis_results = {
            'style_analysis': self._analyze_styles(),
            'top_performers': self._analyze_top_performers(),
            'scarce_effectiveness': self._analyze_scarce_effectiveness(),
            'coverage_analysis': self._analyze_coverage(),
            'balance_metrics': self._calculate_balance_metrics(),
            'business_metrics': self._calculate_business_metrics(),
            'sku_distribution': self._analyze_sku_distribution()
        }
        
        self.logger.info("결과 분석 완료")
        return analysis_results
    
    def _get_empty_results(self) -> Dict[str, pd.DataFrame]:
        """빈 결과 반환"""
        return {
            'style_analysis': pd.DataFrame(),
            'top_performers': pd.DataFrame(),
            'scarce_effectiveness': pd.DataFrame(),
            'coverage_analysis': pd.DataFrame(),
            'balance_metrics': pd.DataFrame(),
            'business_metrics': pd.DataFrame(),
            'sku_distribution': pd.DataFrame()
        }
    
    def _analyze_styles(self) -> pd.DataFrame:
        """스타일별 분석"""
        style_results = []
        
        for style in self.styles:
            style_skus = self.I_s[style]
            style_allocations = self.allocation_df[self.allocation_df['PART_CD'] == style]
            
            if style_allocations.empty:
                continue
            
            # 기본 통계
            total_qty = style_allocations['ALLOCATED_QTY'].sum()
            total_supply = sum(self.A[sku] for sku in style_skus if sku in self.A)
            utilization_rate = total_qty / total_supply if total_supply > 0 else 0
            
            # 색상/사이즈 다양성
            colors_allocated = style_allocations['COLOR_CD'].nunique()
            sizes_allocated = style_allocations['SIZE_CD'].nunique()
            total_colors = len(self.K_s[style])
            total_sizes = len(self.L_s[style])
            
            # 매장 분포
            stores_covered = style_allocations['SHOP_ID'].nunique()
            avg_qty_per_store = total_qty / stores_covered if stores_covered > 0 else 0
            
            # 희소 SKU 비율
            scarce_skus_in_style = [sku for sku in style_skus if sku in self.scarce]
            scarce_allocations = style_allocations[style_allocations['SKU_TYPE'] == 'scarce']
            scarce_ratio = len(scarce_allocations) / len(style_allocations) if len(style_allocations) > 0 else 0
            
            style_results.append({
                'STYLE': style,
                'TOTAL_ALLOCATED_QTY': total_qty,
                'TOTAL_SUPPLY_QTY': total_supply,
                'UTILIZATION_RATE': utilization_rate,
                'COLORS_ALLOCATED': colors_allocated,
                'TOTAL_COLORS': total_colors,
                'COLOR_COVERAGE_RATE': colors_allocated / total_colors if total_colors > 0 else 0,
                'SIZES_ALLOCATED': sizes_allocated,
                'TOTAL_SIZES': total_sizes,
                'SIZE_COVERAGE_RATE': sizes_allocated / total_sizes if total_sizes > 0 else 0,
                'STORES_COVERED': stores_covered,
                'AVG_QTY_PER_STORE': avg_qty_per_store,
                'SCARCE_SKU_COUNT': len(scarce_skus_in_style),
                'SCARCE_ALLOCATION_RATIO': scarce_ratio,
                'DIVERSITY_SCORE': (colors_allocated * sizes_allocated) / (total_colors * total_sizes) if (total_colors * total_sizes) > 0 else 0
            })
        
        return pd.DataFrame(style_results)
    
    def _analyze_top_performers(self) -> pd.DataFrame:
        """최고 성과 매장 분석"""
        if self.store_summary_df.empty:
            return pd.DataFrame()
        
        # 매장별 상세 분석
        store_performance = []
        
        for store_id in self.stores:
            store_allocations = self.allocation_df[self.allocation_df['SHOP_ID'] == store_id]
            
            if store_allocations.empty:
                continue
            
            # 기본 통계
            total_qty = store_allocations['ALLOCATED_QTY'].sum()
            total_skus = len(store_allocations)
            expected_share = self.QSUM[store_id] / sum(self.QSUM.values())
            actual_share = total_qty / self.allocation_df['ALLOCATED_QTY'].sum()
            
            # 다양성 지표
            styles_count = store_allocations['PART_CD'].nunique()
            colors_count = store_allocations['COLOR_CD'].nunique()
            sizes_count = store_allocations['SIZE_CD'].nunique()
            
            # 커버리지 계산
            color_coverage, size_coverage = self._calculate_store_coverage(store_id, store_allocations)
            
            # 희소 SKU 비율
            scarce_count = len(store_allocations[store_allocations['SKU_TYPE'] == 'scarce'])
            scarce_ratio = scarce_count / total_skus if total_skus > 0 else 0
            
            # 성과 점수 계산 (종합 지표)
            performance_score = (
                (color_coverage + size_coverage) * 0.4 +  # 커버리지 40%
                (actual_share / expected_share if expected_share > 0 else 0) * 0.3 +  # 공정성 30%
                (styles_count / len(self.styles)) * 0.2 +  # 스타일 다양성 20%
                scarce_ratio * 0.1  # 희소 SKU 활용 10%
            )
            
            store_performance.append({
                'SHOP_ID': store_id,
                'SHOP_NAME': self._get_store_name(store_id),
                'TOTAL_QTY': total_qty,
                'TOTAL_SKUS': total_skus,
                'EXPECTED_SHARE': expected_share,
                'ACTUAL_SHARE': actual_share,
                'SHARE_RATIO': actual_share / expected_share if expected_share > 0 else 0,
                'STYLES_COUNT': styles_count,
                'COLORS_COUNT': colors_count,
                'SIZES_COUNT': sizes_count,
                'COLOR_COVERAGE': color_coverage,
                'SIZE_COVERAGE': size_coverage,
                'OVERALL_COVERAGE': (color_coverage + size_coverage) / 2,
                'SCARCE_SKU_COUNT': scarce_count,
                'SCARCE_SKU_RATIO': scarce_ratio,
                'PERFORMANCE_SCORE': performance_score,
                'QTY_SUM': self.QSUM[store_id]
            })
        
        performance_df = pd.DataFrame(store_performance)
        
        if not performance_df.empty:
            # 상위 성과 매장만 선별 (상위 20개 또는 전체의 20%)
            top_count = min(20, max(5, int(len(performance_df) * 0.2)))
            performance_df = performance_df.nlargest(top_count, 'PERFORMANCE_SCORE')
            
            # 순위 추가
            performance_df['RANK'] = range(1, len(performance_df) + 1)
            performance_df = performance_df[['RANK'] + [col for col in performance_df.columns if col != 'RANK']]
        
        return performance_df
    
    def _analyze_scarce_effectiveness(self) -> pd.DataFrame:
        """희소 SKU 효과성 분석"""
        scarce_results = []
        
        for scarce_sku in self.scarce:
            sku_allocations = self.allocation_df[self.allocation_df['SKU'] == scarce_sku]
            
            if sku_allocations.empty:
                continue
            
            # 기본 정보
            part_cd, color_cd, size_cd = scarce_sku.split('_')
            supply_qty = self.A[scarce_sku]
            allocated_qty = sku_allocations['ALLOCATED_QTY'].sum()
            stores_covered = len(sku_allocations)
            
            # 효과성 지표
            utilization_rate = allocated_qty / supply_qty if supply_qty > 0 else 0
            coverage_effectiveness = stores_covered / len(self.stores)
            avg_qty_per_store = allocated_qty / stores_covered if stores_covered > 0 else 0
            
            # Step1에서 할당된 비율 (b_hat 확인)
            step1_assignments = sum(1 for store in self.stores 
                                  if (scarce_sku, store) in self.optimizer.b_hat 
                                  and self.optimizer.b_hat[(scarce_sku, store)] == 1)
            step1_effectiveness = step1_assignments / len(self.stores)
            
            # 동일 스타일 내 다른 SKU들과의 경쟁력
            same_style_skus = self.I_s[part_cd]
            same_style_allocations = self.allocation_df[self.allocation_df['PART_CD'] == part_cd]
            style_total_qty = same_style_allocations['ALLOCATED_QTY'].sum()
            within_style_share = allocated_qty / style_total_qty if style_total_qty > 0 else 0
            
            # SKU 분산도 계산 (새로 추가)
            distribution_variance = self._calculate_sku_distribution_variance(sku_allocations)
            max_concentration = sku_allocations['ALLOCATED_QTY'].max() / supply_qty if supply_qty > 0 else 0
            
            scarce_results.append({
                'SKU': scarce_sku,
                'PART_CD': part_cd,
                'COLOR_CD': color_cd,
                'SIZE_CD': size_cd,
                'SUPPLY_QTY': supply_qty,
                'ALLOCATED_QTY': allocated_qty,
                'UTILIZATION_RATE': utilization_rate,
                'STORES_COVERED': stores_covered,
                'COVERAGE_EFFECTIVENESS': coverage_effectiveness,
                'AVG_QTY_PER_STORE': avg_qty_per_store,
                'STEP1_ASSIGNMENTS': step1_assignments,
                'STEP1_EFFECTIVENESS': step1_effectiveness,
                'WITHIN_STYLE_SHARE': within_style_share,
                'DISTRIBUTION_VARIANCE': distribution_variance,
                'MAX_CONCENTRATION': max_concentration,
                'EFFECTIVENESS_SCORE': (utilization_rate * 0.3 + 
                                      coverage_effectiveness * 0.4 + 
                                      step1_effectiveness * 0.3)
            })
        
        scarce_df = pd.DataFrame(scarce_results)
        
        if not scarce_df.empty:
            # 효과성 순으로 정렬
            scarce_df = scarce_df.sort_values('EFFECTIVENESS_SCORE', ascending=False)
            scarce_df['RANK'] = range(1, len(scarce_df) + 1)
            scarce_df = scarce_df[['RANK'] + [col for col in scarce_df.columns if col != 'RANK']]
        
        return scarce_df
    
    def _analyze_coverage(self) -> pd.DataFrame:
        """커버리지 분석"""
        coverage_results = []
        
        for store_id in self.stores:
            store_allocations = self.allocation_df[self.allocation_df['SHOP_ID'] == store_id]
            
            if store_allocations.empty:
                # 할당받지 못한 매장
                coverage_results.append({
                    'SHOP_ID': store_id,
                    'SHOP_NAME': self._get_store_name(store_id),
                    'TOTAL_QTY': 0,
                    'TOTAL_SKUS': 0,
                    'OVERALL_COLOR_COVERAGE': 0,
                    'OVERALL_SIZE_COVERAGE': 0,
                    'STYLE_COVERAGE_DETAILS': {}
                })
                continue
            
            # 전체 커버리지 계산
            color_coverage, size_coverage = self._calculate_store_coverage(store_id, store_allocations)
            
            # 스타일별 상세 커버리지
            style_coverage_details = {}
            for style in self.styles:
                style_allocations = store_allocations[store_allocations['PART_CD'] == style]
                if not style_allocations.empty:
                    style_colors = style_allocations['COLOR_CD'].nunique()
                    style_sizes = style_allocations['SIZE_CD'].nunique()
                    total_colors = len(self.K_s[style])
                    total_sizes = len(self.L_s[style])
                    
                    style_coverage_details[style] = {
                        'color_coverage': style_colors / total_colors if total_colors > 0 else 0,
                        'size_coverage': style_sizes / total_sizes if total_sizes > 0 else 0,
                        'colors': f"{style_colors}/{total_colors}",
                        'sizes': f"{style_sizes}/{total_sizes}"
                    }
            
            coverage_results.append({
                'SHOP_ID': store_id,
                'SHOP_NAME': self._get_store_name(store_id),
                'TOTAL_QTY': store_allocations['ALLOCATED_QTY'].sum(),
                'TOTAL_SKUS': len(store_allocations),
                'OVERALL_COLOR_COVERAGE': color_coverage,
                'OVERALL_SIZE_COVERAGE': size_coverage,
                'AVERAGE_COVERAGE': (color_coverage + size_coverage) / 2,
                'STYLE_COVERAGE_DETAILS': style_coverage_details,
                'QTY_SUM': self.QSUM[store_id]
            })
        
        return pd.DataFrame(coverage_results)
    
    def _calculate_balance_metrics(self) -> pd.DataFrame:
        """균형 메트릭 계산"""
        metrics = []
        
        # 전체 시스템 균형 메트릭
        if not self.allocation_df.empty:
            # 매장별 할당량 분포
            store_allocations = self.allocation_df.groupby('SHOP_ID')['ALLOCATED_QTY'].sum()
            expected_allocations = pd.Series(self.QSUM)
            
            # 정규화된 분배 (총합 기준)
            total_allocated = store_allocations.sum()
            total_expected = expected_allocations.sum()
            
            actual_shares = store_allocations / total_allocated
            expected_shares = expected_allocations / total_expected
            
            # Gini 계수 계산
            gini_coefficient = self._calculate_gini_coefficient(actual_shares.values)
            
            # 상관계수
            correlation = actual_shares.corr(expected_shares) if len(actual_shares) > 1 else 0
            
            # 표준편차 비율
            std_ratio = actual_shares.std() / expected_shares.std() if expected_shares.std() > 0 else 0
            
            metrics.append({
                'METRIC_TYPE': 'ALLOCATION_BALANCE',
                'METRIC_NAME': 'Gini Coefficient',
                'VALUE': gini_coefficient,
                'DESCRIPTION': '분배 불평등 지수 (0=완전평등, 1=완전불평등)',
                'SCORE': 1 - gini_coefficient  # 낮을수록 좋음
            })
            
            metrics.append({
                'METRIC_TYPE': 'ALLOCATION_BALANCE',
                'METRIC_NAME': 'Allocation Correlation',
                'VALUE': correlation,
                'DESCRIPTION': '기대 분배와 실제 분배의 상관계수',
                'SCORE': max(0, correlation)  # 높을수록 좋음
            })
            
            metrics.append({
                'METRIC_TYPE': 'ALLOCATION_BALANCE',
                'METRIC_NAME': 'Std Deviation Ratio',
                'VALUE': std_ratio,
                'DESCRIPTION': '실제/기대 분배의 표준편차 비율',
                'SCORE': 1 / (1 + abs(std_ratio - 1))  # 1에 가까울수록 좋음
            })
        
        # 커버리지 균형 메트릭
        coverage_df = self._analyze_coverage()
        if not coverage_df.empty:
            color_coverage_std = coverage_df['OVERALL_COLOR_COVERAGE'].std()
            size_coverage_std = coverage_df['OVERALL_SIZE_COVERAGE'].std()
            
            metrics.append({
                'METRIC_TYPE': 'COVERAGE_BALANCE',
                'METRIC_NAME': 'Color Coverage Std',
                'VALUE': color_coverage_std,
                'DESCRIPTION': '매장별 색상 커버리지 표준편차',
                'SCORE': max(0, 1 - color_coverage_std)  # 낮을수록 좋음
            })
            
            metrics.append({
                'METRIC_TYPE': 'COVERAGE_BALANCE',
                'METRIC_NAME': 'Size Coverage Std',
                'VALUE': size_coverage_std,
                'DESCRIPTION': '매장별 사이즈 커버리지 표준편차',
                'SCORE': max(0, 1 - size_coverage_std)  # 낮을수록 좋음
            })
        
        return pd.DataFrame(metrics)
    
    def _calculate_business_metrics(self) -> pd.DataFrame:
        """비즈니스 메트릭 계산"""
        metrics = []
        
        if self.allocation_df.empty:
            return pd.DataFrame(metrics)
        
        # 1. 총 할당 효율성
        total_allocated = self.allocation_df['ALLOCATED_QTY'].sum()
        total_supply = sum(self.A.values())
        allocation_efficiency = total_allocated / total_supply if total_supply > 0 else 0
        
        metrics.append({
            'METRIC_NAME': 'Total Allocation Efficiency',
            'VALUE': allocation_efficiency,
            'DESCRIPTION': '전체 공급량 대비 할당율',
            'SCORE': allocation_efficiency,
            'CATEGORY': 'EFFICIENCY'
        })
        
        # 2. 희소 SKU 활용률
        scarce_allocated = len(self.allocation_df[self.allocation_df['SKU_TYPE'] == 'scarce'])
        scarce_utilization = scarce_allocated / len(self.scarce) if len(self.scarce) > 0 else 0
        
        metrics.append({
            'METRIC_NAME': 'Scarce SKU Utilization',
            'VALUE': scarce_utilization,
            'DESCRIPTION': '희소 SKU 활용 비율',
            'SCORE': scarce_utilization,
            'CATEGORY': 'UTILIZATION'
        })
        
        # 3. 매장별 상품 다양성 지수
        store_diversity_scores = []
        for store_id in self.stores:
            store_allocations = self.allocation_df[self.allocation_df['SHOP_ID'] == store_id]
            if not store_allocations.empty:
                styles_count = store_allocations['PART_CD'].nunique()
                colors_count = store_allocations['COLOR_CD'].nunique()
                sizes_count = store_allocations['SIZE_CD'].nunique()
                
                # 심슨 다양성 지수 응용
                diversity_score = (styles_count / len(self.styles)) * 0.4 + \
                                (colors_count / sum(len(colors) for colors in self.K_s.values())) * 0.3 + \
                                (sizes_count / sum(len(sizes) for sizes in self.L_s.values())) * 0.3
                
                store_diversity_scores.append(diversity_score)
        
        avg_diversity = np.mean(store_diversity_scores) if store_diversity_scores else 0
        
        metrics.append({
            'METRIC_NAME': 'Average Store Diversity',
            'VALUE': avg_diversity,
            'DESCRIPTION': '매장별 평균 상품 다양성 지수',
            'SCORE': avg_diversity,
            'CATEGORY': 'DIVERSITY'
        })
        
        # 4. 커버리지 성과 점수
        coverage_df = self._analyze_coverage()
        if not coverage_df.empty:
            avg_color_coverage = coverage_df['OVERALL_COLOR_COVERAGE'].mean()
            avg_size_coverage = coverage_df['OVERALL_SIZE_COVERAGE'].mean()
            overall_coverage_score = (avg_color_coverage + avg_size_coverage) / 2
            
            metrics.append({
                'METRIC_NAME': 'Overall Coverage Score',
                'VALUE': overall_coverage_score,
                'DESCRIPTION': '전체 평균 커버리지 점수',
                'SCORE': overall_coverage_score,
                'CATEGORY': 'COVERAGE'
            })
        
        # 5. 예상 고객 만족도 점수 (종합 지표)
        balance_df = self._calculate_balance_metrics()
        if not balance_df.empty:
            avg_balance_score = balance_df['SCORE'].mean()
            
            customer_satisfaction = (
                allocation_efficiency * 0.2 +
                scarce_utilization * 0.2 +
                avg_diversity * 0.3 +
                overall_coverage_score * 0.2 +
                avg_balance_score * 0.1
            )
            
            metrics.append({
                'METRIC_NAME': 'Customer Satisfaction Score',
                'VALUE': customer_satisfaction,
                'DESCRIPTION': '예상 고객 만족도 종합 점수',
                'SCORE': customer_satisfaction,
                'CATEGORY': 'OVERALL'
            })
        
        return pd.DataFrame(metrics)
    
    def _calculate_store_coverage(self, store_id: int, store_allocations: pd.DataFrame) -> Tuple[float, float]:
        """매장별 색상/사이즈 커버리지 계산"""
        total_colors = sum(len(self.K_s[style]) for style in self.styles)
        total_sizes = sum(len(self.L_s[style]) for style in self.styles)
        
        covered_colors = store_allocations['COLOR_CD'].nunique()
        covered_sizes = store_allocations['SIZE_CD'].nunique()
        
        color_coverage = covered_colors / total_colors if total_colors > 0 else 0
        size_coverage = covered_sizes / total_sizes if total_sizes > 0 else 0
        
        return color_coverage, size_coverage
    
    def _calculate_gini_coefficient(self, values: np.ndarray) -> float:
        """Gini 계수 계산"""
        if len(values) == 0:
            return 0
        
        # 정렬
        sorted_values = np.sort(values)
        n = len(sorted_values)
        
        # Gini 계수 공식
        index = np.arange(1, n + 1)
        gini = (2 * np.sum(index * sorted_values)) / (n * np.sum(sorted_values)) - (n + 1) / n
        
        return max(0, min(1, gini))  # 0-1 범위로 제한
    
    def _get_store_name(self, store_id: int) -> str:
        """매장 ID로부터 매장명 추출"""
        store_row = self.df_store[self.df_store['SHOP_ID'] == store_id]
        if not store_row.empty and 'SHOP_NM' in store_row.columns:
            return store_row['SHOP_NM'].iloc[0]
        return f"Store_{store_id}"
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """요약 통계 반환"""
        if self.allocation_df.empty:
            return {}
        
        return {
            'total_allocations': len(self.allocation_df),
            'total_quantity': self.allocation_df['ALLOCATED_QTY'].sum(),
            'stores_covered': self.allocation_df['SHOP_ID'].nunique(),
            'skus_allocated': self.allocation_df['SKU'].nunique(),
            'scarce_skus_allocated': len(self.allocation_df[self.allocation_df['SKU_TYPE'] == 'scarce']),
            'styles_covered': self.allocation_df['PART_CD'].nunique(),
            'avg_qty_per_allocation': self.allocation_df['ALLOCATED_QTY'].mean(),
            'allocation_efficiency': self.allocation_df['ALLOCATED_QTY'].sum() / sum(self.A.values())
        }
    
    def _analyze_sku_distribution(self) -> pd.DataFrame:
        """SKU 분산 분석 (새로 추가)"""
        if self.allocation_df.empty:
            return pd.DataFrame()
        
        distribution_results = []
        
        for sku in self.SKUs:
            sku_allocations = self.allocation_df[self.allocation_df['SKU'] == sku]
            
            if sku_allocations.empty:
                continue
            
            # 기본 정보
            part_cd, color_cd, size_cd = sku.split('_')
            supply_qty = self.A[sku]
            allocated_qty = sku_allocations['ALLOCATED_QTY'].sum()
            stores_covered = len(sku_allocations)
            
            # 분산 지표들
            distribution_variance = self._calculate_sku_distribution_variance(sku_allocations)
            max_concentration = sku_allocations['ALLOCATED_QTY'].max() / supply_qty if supply_qty > 0 else 0
            min_allocation = sku_allocations['ALLOCATED_QTY'].min()
            max_allocation = sku_allocations['ALLOCATED_QTY'].max()
            allocation_range = max_allocation - min_allocation
            
            # Gini 계수 (SKU별)
            allocation_values = sku_allocations['ALLOCATED_QTY'].values
            gini_coefficient = self._calculate_gini_coefficient(allocation_values)
            
            # 균등성 지수 (0에 가까울수록 균등)
            expected_per_store = supply_qty / len(self.stores)
            evenness_score = 1 - (distribution_variance / expected_per_store if expected_per_store > 0 else 0)
            
            distribution_results.append({
                'SKU': sku,
                'PART_CD': part_cd,
                'COLOR_CD': color_cd,
                'SIZE_CD': size_cd,
                'SKU_TYPE': 'scarce' if sku in self.scarce else 'abundant',
                'SUPPLY_QTY': supply_qty,
                'ALLOCATED_QTY': allocated_qty,
                'STORES_COVERED': stores_covered,
                'DISTRIBUTION_VARIANCE': distribution_variance,
                'MAX_CONCENTRATION': max_concentration,
                'MIN_ALLOCATION': min_allocation,
                'MAX_ALLOCATION': max_allocation,
                'ALLOCATION_RANGE': allocation_range,
                'GINI_COEFFICIENT': gini_coefficient,
                'EVENNESS_SCORE': max(0, evenness_score),
                'AVG_PER_STORE': allocated_qty / stores_covered if stores_covered > 0 else 0
            })
        
        distribution_df = pd.DataFrame(distribution_results)
        
        if not distribution_df.empty:
            # 균등성 점수순으로 정렬 (높을수록 좋음)
            distribution_df = distribution_df.sort_values('EVENNESS_SCORE', ascending=False)
            distribution_df['EVENNESS_RANK'] = range(1, len(distribution_df) + 1)
        
        return distribution_df
    
    def _calculate_sku_distribution_variance(self, sku_allocations: pd.DataFrame) -> float:
        """SKU 분산도 계산 (새로 추가)"""
        if sku_allocations.empty:
            return 0
        
        allocations = sku_allocations['ALLOCATED_QTY'].values
        return np.var(allocations) if len(allocations) > 1 else 0 