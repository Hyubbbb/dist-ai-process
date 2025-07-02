"""시각화 모듈"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, Any
import os
import logging


class ResultVisualizer:
    """결과 시각화 클래스"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        
        # 한글 폰트 설정
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False
        sns.set_style("whitegrid")
    
    def create_plots(self, analysis_results: Dict[str, pd.DataFrame], 
                    scenario_name: str = "experiment") -> Dict[str, str]:
        """분석 결과를 바탕으로 시각화 생성"""
        self.logger.info("시각화 생성 시작...")
        
        plot_files = {}
        
        # 1. 스타일 분석 차트
        if 'style_analysis' in analysis_results and not analysis_results['style_analysis'].empty:
            plot_files['style_analysis'] = self._plot_style_analysis(
                analysis_results['style_analysis'], scenario_name
            )
        
        # 2. 매장 성과 차트
        if 'top_performers' in analysis_results and not analysis_results['top_performers'].empty:
            plot_files['top_performers'] = self._plot_top_performers(
                analysis_results['top_performers'], scenario_name
            )
        
        # 3. 희소 SKU 효과성 차트
        if 'scarce_effectiveness' in analysis_results and not analysis_results['scarce_effectiveness'].empty:
            plot_files['scarce_effectiveness'] = self._plot_scarce_effectiveness(
                analysis_results['scarce_effectiveness'], scenario_name
            )
        
        self.logger.info(f"시각화 생성 완료: {len(plot_files)}개 파일")
        return plot_files
    
    def _plot_style_analysis(self, style_df: pd.DataFrame, scenario_name: str) -> str:
        """스타일별 분석 차트"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Style Analysis - {scenario_name}', fontsize=14, fontweight='bold')
        
        # 1. 활용률 막대 차트
        axes[0, 0].bar(style_df['STYLE'], style_df['UTILIZATION_RATE'], alpha=0.7, color='skyblue')
        axes[0, 0].set_title('Utilization Rate by Style')
        axes[0, 0].set_ylabel('Utilization Rate')
        plt.setp(axes[0, 0].get_xticklabels(), rotation=45)
        
        # 2. 색상 커버리지
        axes[0, 1].bar(style_df['STYLE'], style_df['COLOR_COVERAGE_RATE'], alpha=0.7, color='lightcoral')
        axes[0, 1].set_title('Color Coverage Rate by Style')
        axes[0, 1].set_ylabel('Coverage Rate')
        plt.setp(axes[0, 1].get_xticklabels(), rotation=45)
        
        # 3. 사이즈 커버리지
        axes[1, 0].bar(style_df['STYLE'], style_df['SIZE_COVERAGE_RATE'], alpha=0.7, color='lightgreen')
        axes[1, 0].set_title('Size Coverage Rate by Style')
        axes[1, 0].set_ylabel('Coverage Rate')
        plt.setp(axes[1, 0].get_xticklabels(), rotation=45)
        
        # 4. 할당량
        axes[1, 1].bar(style_df['STYLE'], style_df['TOTAL_ALLOCATED_QTY'], alpha=0.7, color='orange')
        axes[1, 1].set_title('Total Allocated Quantity by Style')
        axes[1, 1].set_ylabel('Quantity')
        plt.setp(axes[1, 1].get_xticklabels(), rotation=45)
        
        plt.tight_layout()
        
        filename = f"{scenario_name}_style_analysis.png"
        filepath = self._save_plot(fig, filename)
        plt.close(fig)
        
        return filepath
    
    def _plot_top_performers(self, performers_df: pd.DataFrame, scenario_name: str) -> str:
        """최고 성과 매장 차트"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Top Performing Stores - {scenario_name}', fontsize=14, fontweight='bold')
        
        top_df = performers_df.head(15)
        
        # 1. 성과 점수
        axes[0, 0].barh(range(len(top_df)), top_df['PERFORMANCE_SCORE'], alpha=0.7, color='steelblue')
        axes[0, 0].set_yticks(range(len(top_df)))
        axes[0, 0].set_yticklabels([f"#{rank}" for rank in top_df['RANK']])
        axes[0, 0].set_xlabel('Performance Score')
        axes[0, 0].set_title('Performance Score Ranking')
        axes[0, 0].invert_yaxis()
        
        # 2. 커버리지 산점도
        axes[0, 1].scatter(top_df['COLOR_COVERAGE'], top_df['SIZE_COVERAGE'], 
                          s=60, alpha=0.7, color='coral')
        axes[0, 1].set_xlabel('Color Coverage')
        axes[0, 1].set_ylabel('Size Coverage')
        axes[0, 1].set_title('Coverage Analysis')
        
        # 3. 할당량 분포
        axes[1, 0].hist(top_df['TOTAL_QTY'], bins=10, alpha=0.7, color='lightgreen', edgecolor='black')
        axes[1, 0].set_xlabel('Total Quantity')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].set_title('Quantity Distribution')
        
        # 4. 다양성 지표
        diversity_data = [top_df['STYLES_COUNT'].mean(), top_df['COLORS_COUNT'].mean(), top_df['SIZES_COUNT'].mean()]
        axes[1, 1].bar(['Styles', 'Colors', 'Sizes'], diversity_data, 
                      color=['skyblue', 'lightcoral', 'lightgreen'], alpha=0.7)
        axes[1, 1].set_title('Average Diversity Metrics')
        axes[1, 1].set_ylabel('Count')
        
        plt.tight_layout()
        
        filename = f"{scenario_name}_top_performers.png"
        filepath = self._save_plot(fig, filename)
        plt.close(fig)
        
        return filepath
    
    def _plot_scarce_effectiveness(self, scarce_df: pd.DataFrame, scenario_name: str) -> str:
        """희소 SKU 효과성 차트"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Scarce SKU Effectiveness - {scenario_name}', fontsize=14, fontweight='bold')
        
        # 1. 효과성 점수 분포
        axes[0, 0].hist(scarce_df['EFFECTIVENESS_SCORE'], bins=15, alpha=0.7, 
                       color='steelblue', edgecolor='black')
        axes[0, 0].axvline(scarce_df['EFFECTIVENESS_SCORE'].mean(), color='red', 
                          linestyle='--', linewidth=2, label='Mean')
        axes[0, 0].set_xlabel('Effectiveness Score')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('Effectiveness Score Distribution')
        axes[0, 0].legend()
        
        # 2. 활용률 vs 커버리지
        axes[0, 1].scatter(scarce_df['UTILIZATION_RATE'], scarce_df['COVERAGE_EFFECTIVENESS'], 
                          alpha=0.7, color='orange')
        axes[0, 1].set_xlabel('Utilization Rate')
        axes[0, 1].set_ylabel('Coverage Effectiveness')
        axes[0, 1].set_title('Utilization vs Coverage')
        
        # 3. 상위 10개 희소 SKU
        top_10 = scarce_df.head(10)
        axes[1, 0].bar(range(len(top_10)), top_10['EFFECTIVENESS_SCORE'], 
                      alpha=0.7, color='lightgreen')
        axes[1, 0].set_xlabel('Top 10 Scarce SKUs')
        axes[1, 0].set_ylabel('Effectiveness Score')
        axes[1, 0].set_title('Top 10 Most Effective Scarce SKUs')
        axes[1, 0].set_xticks(range(len(top_10)))
        axes[1, 0].set_xticklabels([f"#{rank}" for rank in top_10['RANK']])
        
        # 4. 스타일별 평균 효과성
        if 'PART_CD' in scarce_df.columns:
            style_avg = scarce_df.groupby('PART_CD')['EFFECTIVENESS_SCORE'].mean()
            axes[1, 1].bar(style_avg.index, style_avg.values, alpha=0.7, color='purple')
            axes[1, 1].set_xlabel('Style')
            axes[1, 1].set_ylabel('Average Effectiveness Score')
            axes[1, 1].set_title('Effectiveness by Style')
            plt.setp(axes[1, 1].get_xticklabels(), rotation=45)
        
        plt.tight_layout()
        
        filename = f"{scenario_name}_scarce_effectiveness.png"
        filepath = self._save_plot(fig, filename)
        plt.close(fig)
        
        return filepath
    
    def _save_plot(self, fig, filename: str) -> str:
        """플롯을 파일로 저장"""
        if self.output_dir:
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = filename
        
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        fig.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        
        self.logger.info(f"플롯 저장 완료: {filepath}")
        return filepath 