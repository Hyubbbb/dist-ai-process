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
        
        # 3. 매장별 배분 적정성 계산
        allocation_ratio = self._calculate_allocation_ratio(final_allocation, target_stores, QSUM)
        
        # 4. 성과 분석
        performance_analysis = self._analyze_performance(store_coverage, allocation_ratio, target_stores)
        
        # 5. 희소 SKU 효과성 분석
        scarce_analysis = self._analyze_scarce_effectiveness(final_allocation, scarce_skus, 
                                                           data, df_sku_filtered, target_stores)
        
        # 6. 종합 평가
        overall_evaluation = self._evaluate_overall_performance(style_coverage, allocation_ratio)
        
        return {
            'store_coverage': store_coverage,
            'style_coverage': style_coverage,
            'allocation_ratio': allocation_ratio,
            'performance_analysis': performance_analysis,
            'scarce_analysis': scarce_analysis,
            'overall_evaluation': overall_evaluation
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
    
    def _calculate_allocation_ratio(self, final_allocation, target_stores, QSUM):
        """매장별 배분 적정성 계산"""
        allocation_ratio = {}
        
        for j in target_stores:
            total_allocated = sum(qty for (sku, store), qty in final_allocation.items() if store == j)
            qty_sum = QSUM[j]
            ratio = total_allocated / qty_sum if qty_sum > 0 else 0
            
            allocation_ratio[j] = {
                'allocated': total_allocated,
                'qty_sum': qty_sum,
                'ratio': ratio
            }
        
        return allocation_ratio
    
    def _analyze_performance(self, store_coverage, allocation_ratio, target_stores):
        """매장 성과 분석"""
        performance_data = []
        
        for j in target_stores:
            # 커버리지 점수
            color_count = len(store_coverage[j]['colors'])
            size_count = len(store_coverage[j]['sizes'])
            
            # 적정성 점수
            alloc_ratio = allocation_ratio[j]['ratio']
            
            # 종합 성과 점수
            performance_score = (color_count + size_count) * 0.4 + min(alloc_ratio, 1.0) * 0.6
            
            performance_data.append({
                'store_id': j,
                'color_coverage': color_count,
                'size_coverage': size_count,
                'allocation_ratio': alloc_ratio,
                'performance_score': performance_score,
                'total_allocated': store_coverage[j]['total_allocated'],
                'qty_sum': allocation_ratio[j]['qty_sum']
            })
        
        # 성과순으로 정렬된 복사본 생성 (top/bottom performers용)
        performance_data_sorted = sorted(performance_data, key=lambda x: x['performance_score'], reverse=True)
        
        return {
            'top_performers': performance_data_sorted[:10],
            'bottom_performers': performance_data_sorted[-10:],
            'all_performance': performance_data  # 원래 순서 유지 (QTY_SUM 내림차순)
        }
    
    def _analyze_scarce_effectiveness(self, final_allocation, scarce_skus, data, df_sku_filtered, target_stores):
        """희소 SKU 효과성 분석"""
        A = data['A']
        effectiveness_data = []
        
        for sku in scarce_skus:
            # SKU 정보 추출
            sku_color = df_sku_filtered.loc[df_sku_filtered['SKU']==sku, 'COLOR_CD'].iloc[0]
            sku_size = df_sku_filtered.loc[df_sku_filtered['SKU']==sku, 'SIZE_CD'].iloc[0]
            
            # 할당된 매장 수
            allocated_stores = sum(1 for (s, store), qty in final_allocation.items() 
                                 if s == sku and qty > 0)
            
            # 총 할당량
            total_allocated = sum(qty for (s, store), qty in final_allocation.items() if s == sku)
            
            effectiveness_data.append({
                'sku': sku,
                'color': sku_color,
                'size': sku_size,
                'supply_qty': A[sku],
                'allocated_stores': allocated_stores,
                'total_allocated': total_allocated,
                'utilization_rate': total_allocated / A[sku] if A[sku] > 0 else 0
            })
        
        return effectiveness_data
    
    def _evaluate_overall_performance(self, style_coverage, allocation_ratio):
        """종합 성과 평가"""
        # 전체 성과 메트릭 계산
        color_coverage = style_coverage['color_coverage']
        size_coverage = style_coverage['size_coverage']
        
        overall_color_coverage = color_coverage['avg_ratio']
        overall_size_coverage = size_coverage['avg_ratio']
        
        # 배분 효율성 및 균형성
        ratios = [data['ratio'] for data in allocation_ratio.values()]
        overall_allocation_efficiency = np.mean(ratios)
        allocation_balance = 1 - (np.max(ratios) - np.min(ratios)) / np.max(ratios) if np.max(ratios) > 0 else 1.0
        
        # 종합 점수
        total_score = (overall_color_coverage + overall_size_coverage + 
                      min(overall_allocation_efficiency, 1.0) + allocation_balance) / 4
        
        # 등급 판정
        if total_score >= 0.8:
            grade = "A (우수)"
        elif total_score >= 0.7:
            grade = "B (양호)"
        elif total_score >= 0.6:
            grade = "C (보통)"
        elif total_score >= 0.5:
            grade = "D (개선필요)"
        else:
            grade = "F (재검토필요)"
        
        print(f"\n🏅 종합 평가:")
        print(f"   색상 커버리지: {overall_color_coverage:.3f}")
        print(f"   사이즈 커버리지: {overall_size_coverage:.3f}")
        print(f"   배분 효율성: {overall_allocation_efficiency:.4f}")
        print(f"   배분 균형성: {allocation_balance:.3f}")
        print(f"   종합 등급: {grade} (점수: {total_score:.3f})")
        
        return {
            'overall_color_coverage': overall_color_coverage,
            'overall_size_coverage': overall_size_coverage,
            'overall_allocation_efficiency': overall_allocation_efficiency,
            'allocation_balance': allocation_balance,
            'total_score': total_score,
            'grade': grade
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