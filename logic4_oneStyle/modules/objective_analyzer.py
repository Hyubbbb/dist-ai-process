"""
목적함수 분해 분석 및 가중치 민감도 분석 모듈

Logic4_oneStyle의 통합 MILP 최적화에서 목적함수 구성요소별 기여도를 분석하고
가중치 변화에 따른 목적함수 값의 민감도를 시각화합니다.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager
import json
import os
from datetime import datetime

# 한글 폰트 설정 (Windows 호환)
try:
    # Windows에서 사용 가능한 한글 폰트 시도
    available_fonts = [font.name for font in font_manager.fontManager.ttflist]
    korean_fonts = ['Malgun Gothic', 'Microsoft YaHei', 'NanumGothic', 'Arial Unicode MS', 'DejaVu Sans']
    
    for font in korean_fonts:
        if font in available_fonts:
            plt.rcParams['font.family'] = font
            break
    else:
        plt.rcParams['font.family'] = 'DejaVu Sans'
    
    plt.rcParams['axes.unicode_minus'] = False
    print(f"✅ 폰트 설정: {plt.rcParams['font.family']}")
except:
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False

class ObjectiveAnalyzer:
    """목적함수 분석 및 시각화 클래스"""
    
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        self.scenario_data = {}
        
    def collect_scenario_data(self, scenario_name, objective_breakdown, experiment_params):
        """시나리오별 데이터 수집"""
        self.scenario_data[scenario_name] = {
            'objective_breakdown': objective_breakdown,
            'params': experiment_params,
            'timestamp': datetime.now()
        }
        
    def create_objective_decomposition_chart(self, save_path=None):
        """목적함수 분해 분석 차트 생성"""
        if not self.scenario_data:
            print("❌ 분석할 데이터가 없습니다.")
            return
            
        # 데이터 준비
        scenarios = []
        coverage_terms = []
        allocation_terms = []
        balance_penalties = []
        efficiency_terms = []
        scarce_bonuses = []
        total_objectives = []
        coverage_weights = []
        
        for scenario_name, data in self.scenario_data.items():
            breakdown = data['objective_breakdown']
            if not breakdown:
                continue
                
            scenarios.append(scenario_name.replace('_DWLG42044', '').replace('_', ' ').title())
            coverage_terms.append(breakdown.get('coverage_term', 0))
            allocation_terms.append(breakdown.get('allocation_term', 0))
            balance_penalties.append(breakdown.get('balance_penalty', 0))
            efficiency_terms.append(breakdown.get('efficiency_term', 0))
            scarce_bonuses.append(breakdown.get('scarce_bonus', 0))
            total_objectives.append(breakdown.get('total_objective', 0))
            coverage_weights.append(breakdown.get('coverage_weight', 0))
        
        if not scenarios:
            print("❌ 유효한 목적함수 분해 데이터가 없습니다.")
            return
            
        # 차트 생성
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
        
        # 1. 목적함수 분해 스택 바차트
        x_pos = np.arange(len(scenarios))
        
        # 양수와 음수 항목 분리
        positive_coverage = np.maximum(coverage_terms, 0)
        positive_allocation = np.maximum(allocation_terms, 0)
        positive_efficiency = np.maximum(efficiency_terms, 0)
        positive_scarce = np.maximum(scarce_bonuses, 0)
        negative_balance = np.minimum(balance_penalties, 0)
        
        # 스택 바차트
        bars1 = ax1.bar(x_pos, positive_coverage, label='Coverage Term', color='#2E86AB', alpha=0.8)
        bars2 = ax1.bar(x_pos, positive_allocation, bottom=positive_coverage, 
                       label='Allocation Term', color='#A23B72', alpha=0.8)
        bars3 = ax1.bar(x_pos, positive_efficiency, 
                       bottom=np.array(positive_coverage) + np.array(positive_allocation),
                       label='Efficiency Term', color='#F18F01', alpha=0.8)
        bars4 = ax1.bar(x_pos, positive_scarce,
                       bottom=np.array(positive_coverage) + np.array(positive_allocation) + np.array(positive_efficiency),
                       label='Scarce Bonus', color='#C73E1D', alpha=0.8)
        bars5 = ax1.bar(x_pos, negative_balance, label='Balance Penalty', color='#8B8B8B', alpha=0.6)
        
        # 총 목적함수 값 라인
        ax1_twin = ax1.twinx()
        line1 = ax1_twin.plot(x_pos, total_objectives, 'ko-', linewidth=2, markersize=8, 
                             label='Total Objective', color='black')
        
        ax1.set_title('Objective Function Decomposition Analysis', fontsize=16, fontweight='bold', pad=20)
        ax1.set_xlabel('Optimization Scenarios', fontsize=12)
        ax1.set_ylabel('Objective Component Values', fontsize=12)
        ax1_twin.set_ylabel('Total Objective Value', fontsize=12)
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(scenarios, rotation=45, ha='right')
        
        # 범례 통합
        handles1, labels1 = ax1.get_legend_handles_labels()
        handles2, labels2 = ax1_twin.get_legend_handles_labels()
        ax1.legend(handles1 + handles2, labels1 + labels2, loc='upper left', bbox_to_anchor=(0, 1))
        
        # 그리드
        ax1.grid(True, alpha=0.3, axis='y')
        ax1_twin.grid(True, alpha=0.3, axis='y', linestyle='--')
        
        # 값 라벨 추가
        for i, total in enumerate(total_objectives):
            ax1_twin.annotate(f'{total:.0f}', (i, total), textcoords="offset points", 
                             xytext=(0,10), ha='center', fontweight='bold')
        
        # 2. 가중치 민감도 분석
        # 커버리지 가중치 vs 총 목적함수 값
        ax2.scatter(coverage_weights, total_objectives, s=150, alpha=0.7, 
                   c=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#8B8B8B'][:len(scenarios)])
        
        # 트렌드 라인
        if len(coverage_weights) > 1:
            z = np.polyfit(coverage_weights, total_objectives, 1)
            p = np.poly1d(z)
            ax2.plot(sorted(coverage_weights), p(sorted(coverage_weights)), "r--", alpha=0.8, linewidth=2)
            
            # 기울기 표시
            slope = z[0]
            ax2.text(0.05, 0.95, f'Sensitivity: {slope:.1f} per unit weight', 
                    transform=ax2.transAxes, fontsize=12, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
        
        # 시나리오 라벨
        for i, (weight, objective, scenario) in enumerate(zip(coverage_weights, total_objectives, scenarios)):
            ax2.annotate(scenario, (weight, objective), textcoords="offset points", 
                        xytext=(5, 5), ha='left', fontsize=10)
        
        ax2.set_title('Coverage Weight Sensitivity Analysis', fontsize=16, fontweight='bold', pad=20)
        ax2.set_xlabel('Coverage Weight', fontsize=12)
        ax2.set_ylabel('Total Objective Value', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # 레이아웃 조정
        plt.tight_layout()
        
        # 저장
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(self.output_dir, f"objective_analysis_{timestamp}.png")
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()  # 메모리 절약을 위해 차트 닫기
        print(f"✅ 목적함수 분석 차트 저장: {save_path}")
        
        return save_path
        
    def create_sensitivity_heatmap(self, save_path=None):
        """가중치 민감도 히트맵 생성"""
        if len(self.scenario_data) < 3:
            print("❌ 히트맵 생성을 위해서는 최소 3개 시나리오가 필요합니다.")
            return
            
        # 데이터 준비
        scenarios = []
        metrics = []
        
        for scenario_name, data in self.scenario_data.items():
            breakdown = data['objective_breakdown']
            if not breakdown:
                continue
                
            scenario_clean = scenario_name.replace('_DWLG42044', '').replace('_', ' ').title()
            scenarios.append(scenario_clean)
            
            metrics.append([
                breakdown.get('coverage_term', 0),
                breakdown.get('allocation_term', 0),
                breakdown.get('efficiency_term', 0),
                breakdown.get('scarce_bonus', 0),
                abs(breakdown.get('balance_penalty', 0)),  # 절댓값으로 표시
                breakdown.get('total_objective', 0)
            ])
        
        # DataFrame 생성
        metric_names = ['Coverage\nTerm', 'Allocation\nTerm', 'Efficiency\nTerm', 
                       'Scarce\nBonus', 'Balance\nPenalty', 'Total\nObjective']
        df_heatmap = pd.DataFrame(metrics, index=scenarios, columns=metric_names)
        
        # 히트맵 생성
        plt.figure(figsize=(12, 8))
        
        # 정규화 (0-1 스케일)
        df_normalized = df_heatmap.div(df_heatmap.max(axis=0), axis=1)
        
        sns.heatmap(df_normalized, annot=True, fmt='.2f', cmap='RdYlBu_r', 
                   cbar_kws={'label': 'Normalized Value (0-1)'}, 
                   linewidths=0.5, square=True)
        
        plt.title('Objective Components Sensitivity Heatmap', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Objective Components', fontsize=12)
        plt.ylabel('Optimization Scenarios', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        
        # 레이아웃 조정
        plt.tight_layout()
        
        # 저장
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(self.output_dir, f"sensitivity_heatmap_{timestamp}.png")
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()  # 메모리 절약을 위해 차트 닫기
        print(f"✅ 민감도 히트맵 저장: {save_path}")
        
        return save_path
        
    def generate_analysis_report(self, save_path=None):
        """분석 리포트 생성"""
        if not self.scenario_data:
            print("❌ 분석할 데이터가 없습니다.")
            return
            
        report = []
        report.append("=" * 80)
        report.append("📊 LOGIC4_ONESTYLE 목적함수 분석 리포트")
        report.append("=" * 80)
        report.append(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"분석 시나리오 수: {len(self.scenario_data)}개")
        report.append("")
        
        # 시나리오별 상세 분석
        for scenario_name, data in self.scenario_data.items():
            breakdown = data['objective_breakdown']
            if not breakdown:
                continue
                
            report.append(f"🎯 시나리오: {scenario_name}")
            report.append("-" * 50)
            report.append(f"커버리지 가중치: {breakdown.get('coverage_weight', 0):.1f}")
            report.append(f"균형 페널티: {breakdown.get('balance_penalty_weight', 0):.1f}")
            report.append("")
            report.append("목적함수 구성요소별 기여도:")
            report.append(f"  • 커버리지 항: {breakdown.get('coverage_term', 0):,.1f}")
            report.append(f"  • 배분량 항: {breakdown.get('allocation_term', 0):,.1f}")
            report.append(f"  • 효율성 항: {breakdown.get('efficiency_term', 0):,.1f}")
            report.append(f"  • 희소 보너스: {breakdown.get('scarce_bonus', 0):,.1f}")
            report.append(f"  • 균형 페널티: {breakdown.get('balance_penalty', 0):,.1f}")
            report.append(f"  → 총 목적함수: {breakdown.get('total_objective', 0):,.1f}")
            report.append("")
        
        # 민감도 분석
        if len(self.scenario_data) > 1:
            weights = [data['objective_breakdown'].get('coverage_weight', 0) 
                      for data in self.scenario_data.values() 
                      if data['objective_breakdown']]
            objectives = [data['objective_breakdown'].get('total_objective', 0) 
                         for data in self.scenario_data.values() 
                         if data['objective_breakdown']]
            
            if len(weights) > 1:
                sensitivity = np.corrcoef(weights, objectives)[0, 1]
                report.append("📈 민감도 분석 결과:")
                report.append(f"커버리지 가중치-목적함수 상관계수: {sensitivity:.3f}")
                
                if sensitivity > 0.9:
                    report.append("  → 강한 양의 상관관계: 가중치 증가 시 목적함수 크게 증가")
                elif sensitivity > 0.5:
                    report.append("  → 중간 양의 상관관계: 가중치 증가 시 목적함수 증가")
                else:
                    report.append("  → 약한 상관관계: 다른 요인들의 영향이 큼")
                report.append("")
        
        # 권장사항
        report.append("💡 최적화 권장사항:")
        max_objective_scenario = max(self.scenario_data.items(), 
                                   key=lambda x: x[1]['objective_breakdown'].get('total_objective', 0) 
                                   if x[1]['objective_breakdown'] else 0)
        report.append(f"  • 최고 성능 시나리오: {max_objective_scenario[0]}")
        report.append(f"  • 목적함수 값: {max_objective_scenario[1]['objective_breakdown'].get('total_objective', 0):,.1f}")
        report.append("")
        report.append("=" * 80)
        
        # 저장
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(self.output_dir, f"objective_analysis_report_{timestamp}.txt")
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"✅ 분석 리포트 저장: {save_path}")
        print('\n'.join(report))
        
        return save_path

    def analyze_experiments(self, experiment_results, output_dir="output/objective_analysis"):
        """
        실험 결과들을 종합 분석하고 시각화
        
        Args:
            experiment_results: List of dict with keys 'scenario', 'objective', 'breakdown', 'coverage_weight'
            output_dir: 결과 저장 디렉토리
            
        Returns:
            dict: 분석 결과 요약
        """
        if len(experiment_results) < 2:
            print("⚠️ 분석을 위해서는 최소 2개 이상의 실험 결과가 필요합니다.")
            return None
            
        print("📊 목적함수 분석 시작...")
        
        # 결과 정렬 (커버리지 가중치 기준)
        experiment_results = sorted(experiment_results, 
                                  key=lambda x: x.get('coverage_weight', 0))
        
        # 1. 목적함수 분해 분석 차트
        decomp_path = self.create_experiment_decomposition_chart(experiment_results, output_dir)
        
        # 2. 민감도 히트맵 (3개 이상 시나리오일 때만)
        heatmap_path = None
        if len(experiment_results) >= 3:
            heatmap_path = self.create_experiment_sensitivity_heatmap(experiment_results, output_dir)
        
        # 3. 정규화 분석 차트 추가
        normalized_path = self.create_normalized_comparison_chart(experiment_results, output_dir)
        
        # 4. 분석 리포트 (개선된 해석 포함)
        report_path = self.create_enhanced_analysis_report(experiment_results, output_dir)
        
        analysis_summary = {
            'num_scenarios': len(experiment_results),
            'decomposition_chart': decomp_path,
            'sensitivity_heatmap': heatmap_path,
            'normalized_chart': normalized_path,
            'analysis_report': report_path,
            'scenarios': [r['scenario'] for r in experiment_results]
        }
        
        return analysis_summary

    def create_normalized_comparison_chart(self, experiment_results, output_dir):
        """
        정규화된 목적함수 구성요소 비교 차트 생성
        """
        # 데이터 준비
        scenarios = [r['scenario'].replace('_DWLG42044', '') for r in experiment_results]
        breakdowns = [r['breakdown'] for r in experiment_results]
        
        # 커버리지 항을 제외한 나머지 구성요소들만 추출 (공정한 비교)
        components = ['allocation_term', 'efficiency_term', 'scarce_bonus', 'balance_penalty']
        component_names = ['Allocation', 'Efficiency', 'Scarce Bonus', 'Balance Penalty']
        
        # 각 구성요소별 값 추출
        data = {}
        for comp in components:
            data[comp] = [breakdown.get(comp, 0) for breakdown in breakdowns]
        
        # 커버리지 항은 별도로 정규화 (가중치로 나누기)
        coverage_normalized = []
        for i, r in enumerate(experiment_results):
            coverage_weight = r.get('coverage_weight', 1.0)
            coverage_value = breakdowns[i].get('coverage_term', 0)
            normalized_value = coverage_value / coverage_weight if coverage_weight > 0 else 0
            coverage_normalized.append(normalized_value)
        
        # 그래프 생성
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
        
        # 상단: 커버리지 정규화 비교
        bars1 = ax1.bar(scenarios, coverage_normalized, color='skyblue', alpha=0.7, edgecolor='navy')
        ax1.set_title('Normalized Coverage Performance\n(Coverage Term ÷ Coverage Weight)', 
                     fontsize=14, fontweight='bold', pad=15)
        ax1.set_xlabel('Scenarios', fontsize=12)
        ax1.set_ylabel('Normalized Coverage Value', fontsize=12)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        
        # 값 표시
        for bar, val in zip(bars1, coverage_normalized):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(coverage_normalized)*0.01,
                    f'{val:.1f}', ha='center', va='bottom', fontweight='bold')
        
        # 하단: 기타 구성요소 비교 (스택 바)
        bottom = np.zeros(len(scenarios))
        colors = ['lightcoral', 'lightgreen', 'gold', 'plum']
        
        for i, (comp, name, color) in enumerate(zip(components, component_names, colors)):
            values = data[comp]
            bars2 = ax2.bar(scenarios, values, bottom=bottom, label=name, 
                           color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
            bottom += values
        
        ax2.set_title('Other Objective Components Comparison\n(Allocation, Efficiency, Scarce, Balance)', 
                     fontsize=14, fontweight='bold', pad=15)
        ax2.set_xlabel('Scenarios', fontsize=12)
        ax2.set_ylabel('Component Values', fontsize=12)
        ax2.legend(loc='upper right', framealpha=0.9)
        ax2.grid(axis='y', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        # 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(output_dir, f"normalized_comparison_{timestamp}.png")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"✅ 정규화 비교 차트 저장: {save_path}")
        
        return save_path

    def create_enhanced_analysis_report(self, experiment_results, output_dir):
        """
        개선된 분석 리포트 생성 (올바른 해석 포함)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_path = os.path.join(output_dir, f"enhanced_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        # 정규화된 커버리지 성능 계산
        normalized_coverage = []
        for r in experiment_results:
            coverage_weight = r.get('coverage_weight', 1.0)
            coverage_value = r['breakdown'].get('coverage_term', 0)
            normalized = coverage_value / coverage_weight if coverage_weight > 0 else 0
            normalized_coverage.append(normalized)
        
        # 실제 성과 일관성 체크
        allocation_terms = [r['breakdown'].get('allocation_term', 0) for r in experiment_results]
        efficiency_terms = [r['breakdown'].get('efficiency_term', 0) for r in experiment_results]
        
        allocation_consistent = len(set(allocation_terms)) == 1
        efficiency_consistent = len(set(efficiency_terms)) == 1
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("📊 LOGIC4_ONESTYLE 개선된 목적함수 분석 리포트\n")
            f.write("="*80 + "\n")
            f.write(f"생성 시간: {timestamp}\n")
            f.write(f"분석 시나리오 수: {len(experiment_results)}개\n\n")
            
            # ⚠️ 중요한 해석 경고
            f.write("⚠️ 목적함수 해석 주의사항\n")
            f.write("-"*50 + "\n")
            f.write("❌ 목적함수 값이 높다고 해서 무조건 '더 좋은' 성능이 아닙니다!\n")
            f.write("📊 각 시나리오마다 가중치가 다르므로 절대값 비교는 무의미합니다.\n")
            f.write("🎯 비즈니스 목표가 다르므로 정규화된 비교가 필요합니다.\n\n")
            
            # 정규화된 성과 분석
            f.write("📈 정규화된 성과 분석\n")
            f.write("-"*50 + "\n")
            for i, r in enumerate(experiment_results):
                scenario = r['scenario'].replace('_DWLG42044', '')
                normalized_val = normalized_coverage[i]
                f.write(f"🎯 {scenario}:\n")
                f.write(f"   정규화된 커버리지 성능: {normalized_val:.1f}\n")
                f.write(f"   (원값: {r['breakdown'].get('coverage_term', 0):.1f} ÷ 가중치: {r.get('coverage_weight', 1.0)})\n\n")
            
            # 실제 할당 일관성 분석
            f.write("🔍 실제 할당 일관성 분석\n")
            f.write("-"*50 + "\n")
            f.write(f"배분량 일관성: {'✅ 모든 시나리오 동일' if allocation_consistent else '❌ 시나리오별 차이'}\n")
            f.write(f"효율성 일관성: {'✅ 모든 시나리오 동일' if efficiency_consistent else '❌ 시나리오별 차이'}\n")
            
            if allocation_consistent and efficiency_consistent:
                f.write("\n🎯 핵심 발견:\n")
                f.write("   모든 시나리오에서 동일한 최적해가 도출되었습니다.\n")
                f.write("   이는 현재 제약 조건 하에서 수학적으로 유일한 최적해가 존재함을 의미합니다.\n")
                f.write("   가중치 변화는 목적함수 값만 변경하고 실제 할당에는 영향을 주지 않았습니다.\n\n")
            
            # 시나리오별 상세 분석
            f.write("📋 시나리오별 상세 분석\n")
            f.write("-"*50 + "\n")
            for r in experiment_results:
                scenario = r['scenario'].replace('_DWLG42044', '')
                f.write(f"🎯 시나리오: {scenario}\n")
                f.write(f"   커버리지 가중치: {r.get('coverage_weight', 'N/A')}\n")
                f.write(f"   균형 페널티: {r.get('balance_penalty_weight', 'N/A')}\n\n")
                f.write("   목적함수 구성요소별 기여도:\n")
                for comp, value in r['breakdown'].items():
                    comp_name = comp.replace('_', ' ').title()
                    f.write(f"     • {comp_name}: {value:.1f}\n")
                f.write(f"   → 총 목적함수: {r['objective']:.1f}\n\n")
            
            # 올바른 의사결정 가이드
            f.write("💡 올바른 의사결정 가이드\n")
            f.write("-"*50 + "\n")
            f.write("1. 목적함수 절대값이 아닌 '비즈니스 목표 달성도'로 평가하세요\n")
            f.write("2. 각 시나리오는 서로 다른 비즈니스 전략을 나타냅니다:\n")
            f.write("   • extreme_coverage: 최대 매장 노출 전략\n")
            f.write("   • balance_focused: 균형잡힌 배분 전략\n")
            f.write("   • baseline: 안정적 운영 전략\n")
            f.write("3. 현재 모든 시나리오에서 동일한 할당 결과가 나온다면,\n")
            f.write("   제약 조건 완화나 목적함수 재설계를 고려하세요\n\n")
            
            # 추천사항
            best_normalized_idx = np.argmax(normalized_coverage)
            best_scenario = experiment_results[best_normalized_idx]['scenario'].replace('_DWLG42044', '')
            
            f.write("🏆 추천사항\n")
            f.write("-"*50 + "\n")
            f.write(f"• 정규화된 성능 기준 최고 시나리오: {best_scenario}\n")
            f.write(f"• 정규화된 커버리지 성능: {max(normalized_coverage):.1f}\n")
            if allocation_consistent:
                f.write("• 주의: 모든 시나리오에서 동일한 할당 → 시스템 개선 필요\n")
            
            f.write("\n" + "="*80 + "\n")
        
        print(f"✅ 개선된 분석 리포트 저장: {report_path}")
        return report_path

    def create_experiment_decomposition_chart(self, experiment_results, output_dir):
        """
        실험 결과를 기반으로 목적함수 분해 분석 차트 생성
        """
        # 데이터 준비
        scenarios = [r['scenario'].replace('_DWLG42044', '') for r in experiment_results]
        breakdowns = [r['breakdown'] for r in experiment_results]
        total_objectives = [r['objective'] for r in experiment_results]
        coverage_weights = [r.get('coverage_weight', 1.0) for r in experiment_results]
        
        # 구성요소별 값 추출
        coverage_terms = [breakdown.get('coverage_term', 0) for breakdown in breakdowns]
        allocation_terms = [breakdown.get('allocation_term', 0) for breakdown in breakdowns]
        efficiency_terms = [breakdown.get('efficiency_term', 0) for breakdown in breakdowns]
        scarce_bonuses = [breakdown.get('scarce_bonus', 0) for breakdown in breakdowns]
        balance_penalties = [breakdown.get('balance_penalty', 0) for breakdown in breakdowns]
        
        # 차트 생성
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
        
        # 1. 목적함수 분해 스택 바차트
        x_pos = np.arange(len(scenarios))
        
        # 양수와 음수 항목 분리
        positive_coverage = np.maximum(coverage_terms, 0)
        positive_allocation = np.maximum(allocation_terms, 0)
        positive_efficiency = np.maximum(efficiency_terms, 0)
        positive_scarce = np.maximum(scarce_bonuses, 0)
        negative_balance = np.minimum(balance_penalties, 0)
        
        # 스택 바차트
        bars1 = ax1.bar(x_pos, positive_coverage, label='Coverage Term', color='#2E86AB', alpha=0.8)
        bars2 = ax1.bar(x_pos, positive_allocation, bottom=positive_coverage, 
                       label='Allocation Term', color='#A23B72', alpha=0.8)
        bars3 = ax1.bar(x_pos, positive_efficiency, 
                       bottom=np.array(positive_coverage) + np.array(positive_allocation),
                       label='Efficiency Term', color='#F18F01', alpha=0.8)
        bars4 = ax1.bar(x_pos, positive_scarce,
                       bottom=np.array(positive_coverage) + np.array(positive_allocation) + np.array(positive_efficiency),
                       label='Scarce Bonus', color='#C73E1D', alpha=0.8)
        bars5 = ax1.bar(x_pos, negative_balance, label='Balance Penalty', color='#8B8B8B', alpha=0.6)
        
        # 총 목적함수 값 라인
        ax1_twin = ax1.twinx()
        line1 = ax1_twin.plot(x_pos, total_objectives, 'ko-', linewidth=2, markersize=8, 
                             label='Total Objective', color='black')
        
        ax1.set_title('Objective Function Decomposition Analysis', fontsize=16, fontweight='bold', pad=20)
        ax1.set_xlabel('Optimization Scenarios', fontsize=12)
        ax1.set_ylabel('Objective Component Values', fontsize=12)
        ax1_twin.set_ylabel('Total Objective Value', fontsize=12)
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(scenarios, rotation=45, ha='right')
        
        # 범례 통합
        handles1, labels1 = ax1.get_legend_handles_labels()
        handles2, labels2 = ax1_twin.get_legend_handles_labels()
        ax1.legend(handles1 + handles2, labels1 + labels2, loc='upper left', bbox_to_anchor=(0, 1))
        
        # 그리드
        ax1.grid(True, alpha=0.3, axis='y')
        ax1_twin.grid(True, alpha=0.3, axis='y', linestyle='--')
        
        # 값 라벨 추가
        for i, total in enumerate(total_objectives):
            ax1_twin.annotate(f'{total:.0f}', (i, total), textcoords="offset points", 
                             xytext=(0,10), ha='center', fontweight='bold')
        
        # 2. 가중치 민감도 분석
        ax2.scatter(coverage_weights, total_objectives, s=150, alpha=0.7, 
                   c=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#8B8B8B'][:len(scenarios)])
        
        # 트렌드 라인
        if len(coverage_weights) > 1:
            z = np.polyfit(coverage_weights, total_objectives, 1)
            p = np.poly1d(z)
            ax2.plot(sorted(coverage_weights), p(sorted(coverage_weights)), "r--", alpha=0.8, linewidth=2)
            
            # 기울기 표시
            slope = z[0]
            ax2.text(0.05, 0.95, f'Sensitivity: {slope:.1f} per unit weight', 
                    transform=ax2.transAxes, fontsize=12, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
        
        # 시나리오 라벨
        for i, (weight, objective, scenario) in enumerate(zip(coverage_weights, total_objectives, scenarios)):
            ax2.annotate(scenario, (weight, objective), textcoords="offset points", 
                        xytext=(5, 5), ha='left', fontsize=10)
        
        ax2.set_title('Coverage Weight Sensitivity Analysis', fontsize=16, fontweight='bold', pad=20)
        ax2.set_xlabel('Coverage Weight', fontsize=12)
        ax2.set_ylabel('Total Objective Value', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # 레이아웃 조정
        plt.tight_layout()
        
        # 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(output_dir, f"objective_analysis_{timestamp}.png")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"✅ 목적함수 분석 차트 저장: {save_path}")
        
        return save_path

    def create_experiment_sensitivity_heatmap(self, experiment_results, output_dir):
        """
        실험 결과를 기반으로 민감도 히트맵 생성
        """
        if len(experiment_results) < 3:
            print("❌ 히트맵 생성을 위해서는 최소 3개 시나리오가 필요합니다.")
            return None
            
        # 데이터 준비
        scenarios = [r['scenario'].replace('_DWLG42044', '') for r in experiment_results]
        
        # 각 구성요소별 값 수집
        metrics = []
        for r in experiment_results:
            breakdown = r['breakdown']
            metrics.append([
                breakdown.get('coverage_term', 0),
                breakdown.get('allocation_term', 0),
                breakdown.get('efficiency_term', 0),
                breakdown.get('scarce_bonus', 0),
                breakdown.get('balance_penalty', 0)
            ])
        
        # DataFrame 생성
        component_names = ['Coverage', 'Allocation', 'Efficiency', 'Scarce Bonus', 'Balance Penalty']
        df_heatmap = pd.DataFrame(metrics, index=scenarios, columns=component_names)
        
        # 정규화 (0-1 스케일)
        df_normalized = df_heatmap.div(df_heatmap.abs().max(axis=1), axis=0).fillna(0)
        
        # 히트맵 생성
        plt.figure(figsize=(10, 8))
        sns.heatmap(df_normalized, annot=True, cmap='RdYlBu_r', center=0, 
                   fmt='.2f', cbar_kws={'label': 'Normalized Contribution'}, 
                   linewidths=0.5, square=True)
        
        plt.title('Objective Components Sensitivity Heatmap', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Objective Components', fontsize=12)
        plt.ylabel('Optimization Scenarios', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        # 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(output_dir, f"sensitivity_heatmap_{timestamp}.png")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"✅ 민감도 히트맵 저장: {save_path}")
        
        return save_path 