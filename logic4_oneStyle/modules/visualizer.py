"""
시각화 모듈
"""

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


class ResultVisualizer:
    """배분 결과 시각화를 담당하는 클래스"""
    
    def __init__(self):
        # 한글 폰트 설정
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False
        
    def create_comprehensive_visualization(self, analysis_results, target_style, save_path=None):
        """종합 시각화 생성"""
        print("📈 배분 결과 시각화 생성 중...")
        
        style_coverage = analysis_results['style_coverage']
        allocation_ratio = analysis_results['allocation_ratio']
        performance_analysis = analysis_results['performance_analysis']
        
        # 전체 그래프 설정
        fig = plt.figure(figsize=(20, 15))
        fig.suptitle(f'SKU Distribution Analysis - Style: {target_style}', fontsize=16, fontweight='bold')
        
        # 1. 색상/사이즈 커버리지 비교
        self._plot_coverage_comparison(fig, style_coverage, 1)
        
        # 2. 매장별 배분 적정성 분포
        self._plot_allocation_distribution(fig, allocation_ratio, 2)
        
        # 3. 매장 규모 vs 할당량 관계
        self._plot_store_size_vs_allocation(fig, allocation_ratio, 3)
        
        # 4. 성과 분석 히트맵 (상위 매장)
        self._plot_performance_heatmap(fig, performance_analysis, 4)
        
        # 5. 커버리지 vs 배분량 산점도
        self._plot_coverage_vs_allocation(fig, analysis_results, 5)
        
        # 6. 통계 요약 텍스트
        self._plot_statistics_summary(fig, analysis_results, 6)
        
        plt.tight_layout()
        
        # PNG 파일로 저장
        if save_path:
            # DPI 높게 설정하여 고품질 저장
            plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"📊 시각화 결과 저장: {save_path}")
        else:
            plt.show()
        
        plt.close()  # 메모리 정리
        print("✅ 시각화 완료!")
        
        return fig
    
    def _plot_coverage_comparison(self, fig, style_coverage, subplot_num):
        """색상/사이즈 커버리지 비교 막대 그래프"""
        plt.subplot(2, 3, subplot_num)
        
        color_cov = style_coverage['color_coverage']
        size_cov = style_coverage['size_coverage']
        
        categories = ['Average', 'Maximum', 'Minimum']
        color_values = [color_cov['avg_ratio'], color_cov['max_ratio'], color_cov['min_ratio']]
        size_values = [size_cov['avg_ratio'], size_cov['max_ratio'], size_cov['min_ratio']]
        
        x = np.arange(len(categories))
        width = 0.35
        
        bars1 = plt.bar(x - width/2, color_values, width, label='Color Coverage', alpha=0.8)
        bars2 = plt.bar(x + width/2, size_values, width, label='Size Coverage', alpha=0.8)
        
        plt.title('Color vs Size Coverage Comparison')
        plt.xlabel('Statistics')
        plt.ylabel('Coverage Ratio')
        plt.xticks(x, categories)
        plt.legend()
        plt.grid(axis='y', alpha=0.3)
        
        # 값 표시
        for i, (c_val, s_val) in enumerate(zip(color_values, size_values)):
            plt.text(i - width/2, c_val + 0.01, f'{c_val:.2f}', ha='center', va='bottom', fontsize=8)
            plt.text(i + width/2, s_val + 0.01, f'{s_val:.2f}', ha='center', va='bottom', fontsize=8)
    
    def _plot_allocation_distribution(self, fig, allocation_ratio, subplot_num):
        """매장별 배분 적정성 분포 히스토그램"""
        plt.subplot(2, 3, subplot_num)
        
        ratios = [data['ratio'] for data in allocation_ratio.values()]
        
        plt.hist(ratios, bins=20, color='skyblue', alpha=0.7, edgecolor='black')
        plt.title('Store Allocation Ratio Distribution')
        plt.xlabel('Allocation Ratio (Allocated/QTY_SUM)')
        plt.ylabel('Number of Stores')
        plt.grid(axis='y', alpha=0.3)
        
        # 평균선 표시
        mean_ratio = np.mean(ratios)
        plt.axvline(mean_ratio, color='red', linestyle='--', linewidth=2, 
                   label=f'Mean: {mean_ratio:.4f}')
        plt.legend()
    
    def _plot_store_size_vs_allocation(self, fig, allocation_ratio, subplot_num):
        """매장 규모 vs 할당량 산점도"""
        plt.subplot(2, 3, subplot_num)
        
        qty_sums = [data['qty_sum'] for data in allocation_ratio.values()]
        allocated_amounts = [data['allocated'] for data in allocation_ratio.values()]
        
        plt.scatter(qty_sums, allocated_amounts, alpha=0.6, s=50)
        plt.title('Store Size vs Allocated Amount')
        plt.xlabel('QTY_SUM (Store Sales Volume)')
        plt.ylabel('Allocated Amount')
        plt.grid(True, alpha=0.3)
        
        # 추세선 추가
        z = np.polyfit(qty_sums, allocated_amounts, 1)
        p = np.poly1d(z)
        plt.plot(qty_sums, p(qty_sums), "r--", alpha=0.8, linewidth=2)
        
        # 상관계수 표시
        correlation = np.corrcoef(qty_sums, allocated_amounts)[0, 1]
        plt.text(0.05, 0.95, f'Correlation: {correlation:.3f}', 
                transform=plt.gca().transAxes, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
    
    def _plot_performance_heatmap(self, fig, performance_analysis, subplot_num):
        """성과 분석 히트맵 (상위 매장)"""
        plt.subplot(2, 3, subplot_num)
        
        top_performers = performance_analysis['top_performers'][:15]  # 상위 15개 매장
        
        # 데이터 준비
        store_ids = [str(p['store_id']) for p in top_performers]
        metrics = ['Color\nCoverage', 'Size\nCoverage', 'Allocation\nRatio']
        
        heatmap_data = []
        for perf in top_performers:
            row = [
                perf['color_coverage'],
                perf['size_coverage'], 
                min(perf['allocation_ratio'], 1.0)  # 1.0으로 캡핑
            ]
            heatmap_data.append(row)
        
        heatmap_data = np.array(heatmap_data).T
        
        im = plt.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')
        plt.title('Top Performers Heatmap')
        plt.xlabel('Store ID')
        plt.ylabel('Metrics')
        plt.xticks(range(len(store_ids)), [s[:8] for s in store_ids], rotation=45)
        plt.yticks(range(len(metrics)), metrics)
        
        # 컬러바 추가
        plt.colorbar(im, fraction=0.046, pad=0.04)
    
    def _plot_coverage_vs_allocation(self, fig, analysis_results, subplot_num):
        """커버리지 vs 배분량 산점도"""  
        plt.subplot(2, 3, subplot_num)
        
        performance_data = analysis_results['performance_analysis']['all_performance']
        
        # 총 커버리지 (색상 + 사이즈)
        total_coverage = [p['color_coverage'] + p['size_coverage'] for p in performance_data]
        allocated_amounts = [p['total_allocated'] for p in performance_data]
        
        plt.scatter(total_coverage, allocated_amounts, alpha=0.6, s=50, color='green')
        plt.title('Total Coverage vs Allocated Amount')
        plt.xlabel('Total Coverage (Color + Size)')
        plt.ylabel('Allocated Amount')
        plt.grid(True, alpha=0.3)
        
        # 추세선
        if len(total_coverage) > 1:
            z = np.polyfit(total_coverage, allocated_amounts, 1)
            p = np.poly1d(z)
            plt.plot(total_coverage, p(total_coverage), "r--", alpha=0.8, linewidth=2)
    
    def _plot_statistics_summary(self, fig, analysis_results, subplot_num):
        """통계 요약 텍스트"""
        plt.subplot(2, 3, subplot_num)
        plt.axis('off')
        
        overall_eval = analysis_results['overall_evaluation']
        
        summary_text = f"""
Performance Summary

📊 Overall Metrics:
• Color Coverage: {overall_eval['overall_color_coverage']:.3f}
• Size Coverage: {overall_eval['overall_size_coverage']:.3f}
• Allocation Efficiency: {overall_eval['overall_allocation_efficiency']:.4f}
• Allocation Balance: {overall_eval['allocation_balance']:.3f}

🏅 Final Grade: {overall_eval['grade']}
📈 Total Score: {overall_eval['total_score']:.3f}

📈 Store Performance:
• Total Stores Analyzed: {len(analysis_results['performance_analysis']['all_performance'])}
• Top Performer Score: {analysis_results['performance_analysis']['top_performers'][0]['performance_score']:.3f}
• Average Performance: {np.mean([p['performance_score'] for p in analysis_results['performance_analysis']['all_performance']]):.3f}
"""
        
        plt.text(0.05, 0.95, summary_text, transform=plt.gca().transAxes, 
                fontsize=10, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))
    
    def create_simple_summary_chart(self, analysis_results, save_path=None):
        """간단한 요약 차트 생성"""
        overall_eval = analysis_results['overall_evaluation']
        
        # 간단한 막대 차트
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        metrics = ['Color\nCoverage', 'Size\nCoverage', 'Allocation\nEfficiency', 'Allocation\nBalance']
        values = [
            overall_eval['overall_color_coverage'],
            overall_eval['overall_size_coverage'],
            overall_eval['overall_allocation_efficiency'],
            overall_eval['allocation_balance']
        ]
        
        bars = ax.bar(metrics, values, color=['skyblue', 'lightgreen', 'orange', 'pink'], alpha=0.8)
        ax.set_title('Overall Performance Metrics', fontsize=14, fontweight='bold')
        ax.set_ylabel('Score')
        ax.set_ylim(0, 1.0)
        ax.grid(axis='y', alpha=0.3)
        
        # 값 표시
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                   f'{value:.3f}', ha='center', va='bottom', fontweight='bold')
        
        # 평균선 표시
        avg_score = overall_eval['total_score']
        ax.axhline(y=avg_score, color='red', linestyle='--', linewidth=2, 
                  label=f'Average: {avg_score:.3f}')
        ax.legend()
        
        plt.tight_layout()
        
        # PNG 파일로 저장
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"📊 요약 차트 저장: {save_path}")
        else:
            plt.show()
        
        plt.close()  # 메모리 정리
        
        return fig 
    
    def create_allocation_matrix_heatmap(self, final_allocation, target_stores, SKUs, QSUM, 
                                       df_sku_filtered, A, tier_system, save_path=None, max_stores=30, max_skus=20, fixed_max=None):
        """
        배분 결과를 매장 × SKU 매트릭스 히트맵으로 시각화
        
        Args:
            final_allocation: 최종 배분 결과 딕셔너리
            target_stores: 배분 대상 매장 리스트 (QTY_SUM 내림차순 정렬됨)
            SKUs: SKU 리스트
            QSUM: 매장별 QTY_SUM 딕셔너리
            df_sku_filtered: 필터링된 SKU 데이터프레임  
            A: SKU별 공급량 딕셔너리
            tier_system: 매장 tier 시스템
            save_path: 저장 경로 (None이면 화면 표시)  
            max_stores: 표시할 최대 매장 수
            max_skus: 표시할 최대 SKU 수
            fixed_max: 고정된 최대 배분량 (None이면 자동 계산)
        """
        print("📊 배분 매트릭스 히트맵 생성 중...")
        
        # 0. Tier 기반 배분 가능량 계산 메서드 정의
        def calculate_max_allocatable_by_tier(sku, target_stores, tier_system, A, QSUM):
            """Tier별 배분 한도를 고려한 해당 SKU의 최대 배분 가능량 계산"""
            # 현재는 모든 SKU가 같은 target_stores를 사용
            # 향후 SKU별로 다른 매장 리스트가 지정되면 tier_system.get_sku_target_stores(sku) 활용
            sku_target_stores = tier_system.get_sku_target_stores(sku, target_stores)
            
            tier_based_capacity = 0
            for store in sku_target_stores:
                # 기본 tier 시스템 사용
                tier_info = tier_system.get_store_tier_info(store, sku_target_stores)
                tier_based_capacity += tier_info['max_sku_limit']
            
            # 실제 공급량과 tier 기반 용량 중 작은 값
            actual_supply = A.get(sku, 0)
            return min(actual_supply, tier_based_capacity)
        
        def get_sku_target_stores(sku, default_target_stores):
            """SKU별 배분 대상 매장 결정"""
            # 현재는 모든 SKU가 같은 매장을 사용
            # 향후 tier_system에 SKU별 매장 지정 정보가 있으면 그것을 사용
            sku_stores = tier_system.get_sku_target_stores(sku)
            if sku_stores:
                return sku_stores
            else:
                return default_target_stores
        
        def get_sku_store_tier_info(sku, store, sku_target_stores, tier_system):
            """SKU별 매장 tier 정보 가져오기"""
            # 현재는 기본 tier 시스템 사용
            # 향후 SKU별로 다른 tier 정보가 필요하면 확장 가능
            try:
                return tier_system.get_store_tier_info(store, sku_target_stores)
            except:
                # 기본값 반환 (안전장치)
                return {
                    'store_id': store,
                    'tier_name': 'TIER_3_LOW',
                    'max_sku_limit': 1,
                    'tier_ratio': 0.5
                }
        
        # 1. 배분이 있는 매장들만 필터링하고 QTY_SUM 기준으로 정렬
        allocated_stores = []
        for store in target_stores:
            store_total = sum(final_allocation.get((sku, store), 0) for sku in SKUs)
            if store_total > 0:
                allocated_stores.append((store, store_total, QSUM[store]))
        
        # QTY_SUM 기준 내림차순 정렬
        allocated_stores.sort(key=lambda x: x[2], reverse=True)
        selected_stores = [store[0] for store in allocated_stores[:max_stores]]
        
        # 2. 배분이 있는 SKU들만 필터링하고 컬러-사이즈 기준으로 정렬
        allocated_skus = []
        for sku in SKUs:
            sku_total = sum(final_allocation.get((sku, store), 0) for store in selected_stores)
            if sku_total > 0:
                try:
                    sku_info = df_sku_filtered[df_sku_filtered['SKU'] == sku].iloc[0]
                    color = sku_info['COLOR_CD']
                    size = sku_info['SIZE_CD']
                    allocated_skus.append((sku, sku_total, color, size))
                except:
                    parts = sku.split('_')
                    color = parts[1] if len(parts) >= 3 else 'Unknown'
                    size = parts[2] if len(parts) >= 3 else 'Unknown'
                    allocated_skus.append((sku, sku_total, color, size))
        
        # 사이즈 정렬 순서 정의
        def get_size_sort_key(size):
            """사이즈를 정렬 가능한 키로 변환"""
            # 문자 사이즈 우선순위
            text_sizes = {'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6}
            
            # 문자 사이즈인 경우
            if size in text_sizes:
                return (0, text_sizes[size])  # 문자 사이즈가 숫자 사이즈보다 우선
            
            # 숫자 사이즈인 경우
            try:
                numeric_size = int(size)
                return (1, numeric_size)  # 숫자 사이즈는 두 번째 그룹
            except:
                return (2, size)  # 알 수 없는 사이즈는 마지막
        
        # 컬러 오름차순, 같은 컬러 내에서 사이즈 순서로 정렬
        allocated_skus.sort(key=lambda x: (x[2], get_size_sort_key(x[3])))
        selected_skus = [sku[0] for sku in allocated_skus[:max_skus]]
        
        # 3. 매트릭스 데이터 생성
        matrix_data = []
        store_labels = []
        
        for store in selected_stores:
            row = []
            for sku in selected_skus:
                qty = final_allocation.get((sku, store), 0)
                row.append(qty)
            matrix_data.append(row)
            
            # 매장 라벨 (매장ID + QTY_SUM)
            store_labels.append(f"{store}\n({QSUM[store]:,})")
        
        # 4. SKU 라벨에 배분 정보 포함 생성
        sku_labels = []
        for sku in selected_skus:
            try:
                sku_info = df_sku_filtered[df_sku_filtered['SKU'] == sku].iloc[0]
                color = sku_info['COLOR_CD']
                size = sku_info['SIZE_CD'] 
            except:
                parts = sku.split('_')
                color = parts[1] if len(parts) >= 3 else 'Unknown'
                size = parts[2] if len(parts) >= 3 else 'Unknown'
            
            # 실제 배분된 총량 계산
            total_allocated = sum(final_allocation.get((sku, store), 0) for store in target_stores)
            # Tier 기반 배분 가능량 계산
            max_allocatable_qty = calculate_max_allocatable_by_tier(sku, target_stores, tier_system, A, QSUM)
            
            # 라벨에 배분 정보 포함 (실제배분량/Tier기반최대배분가능량)
            sku_labels.append(f"{color}-{size}\n({total_allocated}/{max_allocatable_qty})")
        
        # 5. 히트맵 생성
        fig, ax = plt.subplots(figsize=(max(12, len(selected_skus) * 0.8), 
                                       max(8, len(selected_stores) * 0.4)))
        
        # 컬러맵: 0은 흰색, 배분량에 따라 색상 진해짐
        matrix_data = np.array(matrix_data)
        # 고정된 색상 스케일 고정: fixed_max가 주어지면 그것을 vmax로 사용
        if fixed_max is not None:
            vmax_val = fixed_max
        else:
            vmax_val = matrix_data.max() if matrix_data.max() > 0 else 1  # 최소 1
        
        im = ax.imshow(matrix_data, cmap='Blues', aspect='auto', vmin=0, vmax=vmax_val)
        
        # 컬러바 추가
        if fixed_max is not None and fixed_max <= 5:
            cbar = plt.colorbar(im, ax=ax, shrink=0.8, ticks=list(range(0, fixed_max + 1)))
        else:
            cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label('Allocated Quantity', rotation=270, labelpad=15)
        
        # 축 설정
        ax.set_xticks(np.arange(len(selected_skus)))
        ax.set_yticks(np.arange(len(selected_stores)))
        ax.set_xticklabels(sku_labels, rotation=45, ha='right', fontsize=9)
        ax.set_yticklabels(store_labels, ha='right', fontsize=9)
        
        # 텍스트 추가 (배분량 표시)
        for i in range(len(selected_stores)):
            for j in range(len(selected_skus)):
                qty = matrix_data[i, j]
                if qty > 0:
                    # 배분량에 따라 텍스트 색상 조정
                    text_color = 'white' if qty > matrix_data.max() * 0.6 else 'black'
                    ax.text(j, i, str(int(qty)), ha='center', va='center', 
                           color=text_color, fontweight='bold', fontsize=8)
        
        # 제목 및 라벨
        ax.set_title(f'SKU Allocation Matrix\n(Top {len(selected_stores)} Stores × Top {len(selected_skus)} SKUs)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('SKU (Color-Size)', fontsize=12)
        ax.set_ylabel('Store ID (QTY_SUM)', fontsize=12)
        
        # 간단한 통계 정보만 추가
        total_allocated = matrix_data.sum()
        filled_combinations = np.count_nonzero(matrix_data)
        
        stats_text = f"Total Allocated: {total_allocated:,}\nFilled Cells: {filled_combinations}"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        
        # 저장 또는 표시
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"   📊 배분 매트릭스 저장: {save_path}")
            plt.close()
        else:
            plt.show()
        
        # 요약 정보 출력
        print(f"   📋 매트릭스 요약:")
        print(f"      표시된 매장: {len(selected_stores)}개")
        print(f"      표시된 SKU: {len(selected_skus)}개")
        print(f"      총 배분량: {total_allocated:,}개")
        
        return {
            'selected_stores': selected_stores,
            'selected_skus': selected_skus,
            'matrix_data': matrix_data,
            'total_allocated': total_allocated
        }