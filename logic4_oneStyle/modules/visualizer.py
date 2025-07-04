"""
시각화 모듈
"""

import matplotlib.pyplot as plt
import numpy as np


class ResultVisualizer:
    """배분 매트릭스 히트맵 시각화를 담당하는 클래스"""
    
    def __init__(self):
        # 한글 폰트 설정
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False

    def create_allocation_matrix_heatmap(self, final_allocation, target_stores, SKUs, QSUM,
                                       df_sku_filtered, A, tier_system, save_path=None, max_stores=30, max_skus=20, fixed_max=None):
        """
        배분 결과를 매장 × SKU 매트릭스 히트맵으로 시각화
        """
        print("📊 배분 매트릭스 히트맵 생성 중...")
        
        # 0. Tier 기반 배분 가능량 계산 메서드 정의
        def calculate_max_allocatable_by_tier(sku, target_stores, tier_system, A, QSUM):
            sku_target_stores = tier_system.get_sku_target_stores(sku, target_stores)
            tier_based_capacity = 0
            for store in sku_target_stores:
                tier_info = tier_system.get_store_tier_info(store, sku_target_stores)
                tier_based_capacity += tier_info['max_sku_limit']
            actual_supply = A.get(sku, 0)
            return min(actual_supply, tier_based_capacity)
        
        # 1. 배분이 있는 매장들만 필터링하고 QTY_SUM 기준으로 정렬
        allocated_stores = []
        for store in target_stores:
            store_total = sum(final_allocation.get((sku, store), 0) for sku in SKUs)
            if store_total > 0:
                allocated_stores.append((store, store_total, QSUM[store]))
        
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
                except:
                    parts = sku.split('_')
                    color = parts[1] if len(parts) >= 3 else 'Unknown'
                    size = parts[2] if len(parts) >= 3 else 'Unknown'
                allocated_skus.append((sku, sku_total, color, size))
        
        def get_size_sort_key(size):
            text_sizes = {'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6}
            if size in text_sizes:
                return (0, text_sizes[size])
            try:
                numeric_size = int(size)
                return (1, numeric_size)
            except:
                return (2, size)
        
        allocated_skus.sort(key=lambda x: (x[2], get_size_sort_key(x[3])))
        selected_skus = [sku[0] for sku in allocated_skus[:max_skus]]
        
        # 3. 매트릭스 데이터 생성
        matrix_data = []
        store_labels = []
        for store in selected_stores:
            row = [final_allocation.get((sku, store), 0) for sku in selected_skus]
            matrix_data.append(row)
            store_labels.append(f"{store}\n({QSUM[store]:,})")
        
        # 4. SKU 라벨 생성
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
            total_allocated = sum(final_allocation.get((sku, store), 0) for store in target_stores)
            max_allocatable_qty = calculate_max_allocatable_by_tier(sku, target_stores, tier_system, A, QSUM)
            sku_labels.append(f"{color}-{size}\n({total_allocated}/{max_allocatable_qty})")
        
        # 5. 부가 통계 계산 (빈 셀, 컬러/사이즈 커버리지)

        total_colors_style = df_sku_filtered['COLOR_CD'].nunique()
        total_sizes_style = df_sku_filtered['SIZE_CD'].nunique()

        empty_cells_counts = []
        color_cov_ratios = []
        size_cov_ratios = []

        for row_idx, store in enumerate(selected_stores):
            row_qties = matrix_data[row_idx]
            # row_qties is a list here – use count(0) instead of numpy comparison
            empty_cells_counts.append(row_qties.count(0))

            # 색상/사이즈 커버리지
            allocated_skus_row = [selected_skus[col_idx] for col_idx, qty in enumerate(row_qties) if qty > 0]
            colors = set()
            sizes = set()
            for sku in allocated_skus_row:
                try:
                    sku_info = df_sku_filtered[df_sku_filtered['SKU'] == sku].iloc[0]
                    colors.add(sku_info['COLOR_CD'])
                    sizes.add(sku_info['SIZE_CD'])
                except:
                    parts = sku.split('_')
                    if len(parts) >= 3:
                        colors.add(parts[1])
                        sizes.add(parts[2])

            color_cov_ratios.append(len(colors)/total_colors_style if total_colors_style else 0)
            size_cov_ratios.append(len(sizes)/total_sizes_style if total_sizes_style else 0)

        avg_empty_cells = np.mean(empty_cells_counts) if empty_cells_counts else 0
        avg_color_cov = np.mean(color_cov_ratios) if color_cov_ratios else 0
        avg_size_cov = np.mean(size_cov_ratios) if size_cov_ratios else 0

        # 6. 히트맵 생성
        matrix_data = np.array(matrix_data)
        vmax_val = fixed_max if fixed_max is not None else max(1, matrix_data.max())
        fig, ax = plt.subplots(figsize=(max(12, len(selected_skus)*0.8), max(8, len(selected_stores)*0.4)))
        im = ax.imshow(matrix_data, cmap='Blues', aspect='auto', vmin=0, vmax=vmax_val)
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label('Allocated Quantity', rotation=270, labelpad=15)
        
        ax.set_xticks(range(len(selected_skus)))
        ax.set_yticks(range(len(selected_stores)))
        ax.set_xticklabels(sku_labels, rotation=45, ha='right', fontsize=9)
        ax.set_yticklabels(store_labels, ha='right', fontsize=9)
        
        for i in range(len(selected_stores)):
            for j in range(len(selected_skus)):
                qty = matrix_data[i, j]
                if qty > 0:
                    text_color = 'white' if qty > matrix_data.max()*0.6 else 'black'
                    ax.text(j, i, str(int(qty)), ha='center', va='center', color=text_color, fontweight='bold', fontsize=8)
        
        # ----- Right-side axis showing empty cell count per store -----
        ax_right = ax.twinx()
        ax_right.set_ylim(ax.get_ylim())
        ax_right.set_yticks(np.arange(len(selected_stores)))
        # 빈 셀 수가 0인 경우 라벨을 비워서 표시하지 않음
        right_labels = [str(c) if c > 0 else '' for c in empty_cells_counts]
        ax_right.set_yticklabels(right_labels, fontsize=9)
        # 1 이상 값은 빨간 볼드체로 강조
        for tick, cnt in zip(ax_right.get_yticklabels(), empty_cells_counts):
            if cnt > 0:
                tick.set_color('red')
                tick.set_fontweight('bold')
        ax_right.set_ylabel('Empty SKU Cells', fontsize=12)
        ax_right.tick_params(axis='y', direction='in')

        # Stats box (move to figure upper-right, above colorbar)
        total_allocated = matrix_data.sum()
        filled_combinations = np.count_nonzero(matrix_data)
        stats_text = (
            f"Total Allocated: {total_allocated:,}\n"
            f"Filled Cells: {filled_combinations}\n"
            f"Avg Empty Cells/store: {avg_empty_cells:.1f}\n"
            f"Avg Color Coverage: {avg_color_cov:.2f}\n"
            f"Avg Size Coverage:  {avg_size_cov:.2f}"
        )

        # Figure-level coordinates (transFigure) so it sits above the colorbar area
        fig.text(0.98, 0.98, stats_text, transform=fig.transFigure,
                 fontsize=11, ha='right', va='top',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.85))
        
        ax.set_title(f'SKU Allocation Matrix\n(Top {len(selected_stores)} Stores × Top {len(selected_skus)} SKUs)', fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('SKU (Color-Size)', fontsize=12)
        ax.set_ylabel('Store ID (QTY_SUM)', fontsize=12)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   📊 배분 매트릭스 저장: {save_path}")
            plt.close()
        else:
            plt.show()
        
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
