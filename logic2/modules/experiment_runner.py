"""실험 실행 관리 모듈"""

import pandas as pd
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import traceback
import json
import os

from .data_loader import DataLoader
from .experiment_config import ExperimentConfig
from .file_manager import FileManager
from .optimizer import SKUOptimizer
from .analyzer import ResultAnalyzer
from .visualizer import ResultVisualizer


class ExperimentRunner:
    """실험 실행 관리 클래스"""
    
    def __init__(self, config_file: str = None):
        """
        실험 실행기 초기화
        
        Args:
            config_file: 설정 파일 경로
        """
        self.logger = logging.getLogger(__name__)
        self.config = ExperimentConfig(config_file)
        self.results = {}  # 실험 결과 저장
        
    def run_single_experiment(self, sku_file: str, store_file: str, 
                            scenario_name: str, output_dir: str = None) -> Dict[str, Any]:
        """
        단일 실험 실행
        
        Args:
            sku_file: SKU 데이터 파일 경로
            store_file: 매장 데이터 파일 경로
            scenario_name: 시나리오 이름
            output_dir: 출력 디렉토리
            
        Returns:
            Dict[str, Any]: 실험 결과
        """
        self.logger.info(f"단일 실험 시작: {scenario_name}")
        start_time = time.time()
        
        try:
            # 1. 데이터 로딩
            data_loader = DataLoader()
            data = data_loader.load_and_preprocess(sku_file, store_file)
            
            # 2. 시나리오 파라미터 가져오기
            params = self.config.get_scenario_params(scenario_name)
            if not params:
                raise ValueError(f"시나리오 '{scenario_name}'를 찾을 수 없습니다.")
            
            # 3. 파일 관리자 설정
            file_manager = FileManager(base_output_dir=output_dir or "../output")
            experiment_dir = file_manager.create_experiment_folder(scenario_name)
            
            # 4. 최적화 실행
            optimizer = SKUOptimizer(data, params)
            optimization_result = optimizer.optimize()
            
            if not optimization_result['success']:
                raise RuntimeError(f"최적화 실패: {optimization_result['message']}")
            
            # 5. 결과 분석
            analyzer = ResultAnalyzer(data, optimizer)
            analysis_results = analyzer.analyze()
            
            # 6. 시각화 생성
            visualizer = ResultVisualizer(experiment_dir)
            plot_files = visualizer.create_plots(analysis_results, scenario_name)
            
            # 7. 결과 저장
            allocation_df = optimizer.get_allocation_results()
            store_summary_df = optimizer.get_store_summary()
            
            file_manager.save_experiment_results(
                experiment_dir, 
                scenario_name,
                allocation_df,
                store_summary_df,
                analysis_results,
                params,
                optimization_result
            )
            
            # 8. 실행 시간 계산
            execution_time = time.time() - start_time
            
            # 9. 결과 패키징
            experiment_result = {
                'scenario_name': scenario_name,
                'success': True,
                'execution_time': execution_time,
                'experiment_dir': experiment_dir,
                'optimization_result': optimization_result,
                'analysis_results': analysis_results,
                'plot_files': plot_files,
                'summary_stats': analyzer.get_summary_stats(),
                'params': params,
                'timestamp': datetime.now().isoformat()
            }
            
            self.results[scenario_name] = experiment_result
            
            self.logger.info(f"실험 완료: {scenario_name} (실행시간: {execution_time:.2f}초)")
            return experiment_result
            
        except Exception as e:
            error_msg = f"실험 실행 중 오류 발생: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            
            return {
                'scenario_name': scenario_name,
                'success': False,
                'error': error_msg,
                'execution_time': time.time() - start_time,
                'timestamp': datetime.now().isoformat()
            }
    
    def run_batch_experiments(self, sku_file: str, store_file: str, 
                            scenario_names: List[str] = None, 
                            output_dir: str = None) -> Dict[str, Any]:
        """
        배치 실험 실행
        
        Args:
            sku_file: SKU 데이터 파일 경로
            store_file: 매장 데이터 파일 경로
            scenario_names: 실행할 시나리오 이름 리스트 (None이면 모든 시나리오)
            output_dir: 출력 디렉토리
            
        Returns:
            Dict[str, Any]: 전체 배치 실험 결과
        """
        self.logger.info("배치 실험 시작")
        batch_start_time = time.time()
        
        # 실행할 시나리오 결정
        if scenario_names is None:
            scenario_names = list(self.config.scenarios.keys())
        
        self.logger.info(f"실행할 시나리오: {scenario_names}")
        
        batch_results = {}
        successful_experiments = 0
        failed_experiments = 0
        
        for scenario_name in scenario_names:
            self.logger.info(f"시나리오 실행: {scenario_name}")
            
            result = self.run_single_experiment(sku_file, store_file, scenario_name, output_dir)
            batch_results[scenario_name] = result
            
            if result['success']:
                successful_experiments += 1
            else:
                failed_experiments += 1
        
        # 배치 실험 결과 생성
        total_time = time.time() - batch_start_time
        
        batch_summary = {
            'total_experiments': len(scenario_names),
            'successful_experiments': successful_experiments,
            'failed_experiments': failed_experiments,
            'total_execution_time': total_time,
            'average_execution_time': total_time / len(scenario_names),
            'scenario_results': batch_results,
            'timestamp': datetime.now().isoformat()
        }
        
        # 배치 비교 분석 생성
        if successful_experiments > 1:
            comparison_result = self.compare_experiments(
                [scenario for scenario in scenario_names 
                 if batch_results[scenario]['success']]
            )
            batch_summary['comparison_analysis'] = comparison_result
        
        self.logger.info(f"배치 실험 완료: {successful_experiments}개 성공, {failed_experiments}개 실패")
        return batch_summary
    
    def run_sensitivity_analysis(self, sku_file: str, store_file: str,
                               base_scenario: str = "baseline",
                               param_variations: Dict[str, List[float]] = None,
                               output_dir: str = None) -> Dict[str, Any]:
        """
        민감도 분석 실행
        
        Args:
            sku_file: SKU 데이터 파일 경로
            store_file: 매장 데이터 파일 경로
            base_scenario: 기본 시나리오
            param_variations: 파라미터 변화량 딕셔너리
            output_dir: 출력 디렉토리
            
        Returns:
            Dict[str, Any]: 민감도 분석 결과
        """
        self.logger.info(f"민감도 분석 시작: 기본 시나리오 {base_scenario}")
        
        if param_variations is None:
            param_variations = {
                'balance_penalty': [0.1, 0.5, 1.0, 2.0, 5.0],
                'color_coverage_weight': [0.5, 1.0, 2.0, 3.0],
                'size_coverage_weight': [0.5, 1.0, 2.0, 3.0]
            }
        
        # 기본 시나리오 실행
        base_result = self.run_single_experiment(sku_file, store_file, base_scenario, output_dir)
        if not base_result['success']:
            return {
                'success': False,
                'error': f"기본 시나리오 실행 실패: {base_result.get('error', 'Unknown error')}"
            }
        
        sensitivity_results = {
            'base_scenario': base_scenario,
            'base_result': base_result,
            'parameter_variations': {}
        }
        
        # 각 파라미터별 민감도 분석
        for param_name, values in param_variations.items():
            self.logger.info(f"파라미터 {param_name} 민감도 분석")
            param_results = []
            
            for value in values:
                # 파라미터 변경된 시나리오 생성
                modified_scenario = f"{base_scenario}_sens_{param_name}_{value}"
                modified_params = base_result['params'].copy()
                modified_params[param_name] = value
                
                # 임시 시나리오 추가
                self.config.scenarios[modified_scenario] = modified_params
                
                # 실험 실행
                result = self.run_single_experiment(sku_file, store_file, modified_scenario, output_dir)
                result['parameter_value'] = value
                param_results.append(result)
                
                # 임시 시나리오 제거
                del self.config.scenarios[modified_scenario]
            
            sensitivity_results['parameter_variations'][param_name] = param_results
        
        # 민감도 지표 계산
        sensitivity_metrics = self._calculate_sensitivity_metrics(sensitivity_results)
        sensitivity_results['sensitivity_metrics'] = sensitivity_metrics
        
        self.logger.info("민감도 분석 완료")
        return sensitivity_results
    
    def compare_experiments(self, scenario_names: List[str]) -> pd.DataFrame:
        """
        실험 결과 비교
        
        Args:
            scenario_names: 비교할 시나리오 이름 리스트
            
        Returns:
            pd.DataFrame: 비교 결과 DataFrame
        """
        self.logger.info(f"실험 비교 분석: {scenario_names}")
        
        comparison_data = []
        
        for scenario_name in scenario_names:
            if scenario_name not in self.results:
                self.logger.warning(f"시나리오 '{scenario_name}' 결과를 찾을 수 없습니다.")
                continue
            
            result = self.results[scenario_name]
            if not result['success']:
                continue
            
            # 주요 메트릭 추출
            summary_stats = result.get('summary_stats', {})
            analysis_results = result.get('analysis_results', {})
            
            # 스타일 분석 메트릭
            style_metrics = {}
            if 'style_analysis' in analysis_results and not analysis_results['style_analysis'].empty:
                style_df = analysis_results['style_analysis']
                style_metrics = {
                    'avg_utilization_rate': style_df['UTILIZATION_RATE'].mean(),
                    'avg_color_coverage': style_df['COLOR_COVERAGE_RATE'].mean(),
                    'avg_size_coverage': style_df['SIZE_COVERAGE_RATE'].mean(),
                    'total_styles': len(style_df)
                }
            
            # 매장 성과 메트릭
            store_metrics = {}
            if 'top_performers' in analysis_results and not analysis_results['top_performers'].empty:
                performers_df = analysis_results['top_performers']
                store_metrics = {
                    'avg_performance_score': performers_df['PERFORMANCE_SCORE'].mean(),
                    'best_performance_score': performers_df['PERFORMANCE_SCORE'].max(),
                    'avg_color_coverage': performers_df['COLOR_COVERAGE'].mean(),
                    'avg_size_coverage': performers_df['SIZE_COVERAGE'].mean()
                }
            
            # 희소 SKU 메트릭
            scarce_metrics = {}
            if 'scarce_effectiveness' in analysis_results and not analysis_results['scarce_effectiveness'].empty:
                scarce_df = analysis_results['scarce_effectiveness']
                scarce_metrics = {
                    'avg_effectiveness_score': scarce_df['EFFECTIVENESS_SCORE'].mean(),
                    'best_effectiveness_score': scarce_df['EFFECTIVENESS_SCORE'].max(),
                    'total_scarce_skus': len(scarce_df)
                }
            
            # 종합 데이터
            comparison_row = {
                'scenario_name': scenario_name,
                'execution_time': result['execution_time'],
                'total_allocations': summary_stats.get('total_allocations', 0),
                'total_quantity': summary_stats.get('total_quantity', 0),
                'stores_covered': summary_stats.get('stores_covered', 0),
                'allocation_efficiency': summary_stats.get('allocation_efficiency', 0),
                **style_metrics,
                **store_metrics,
                **scarce_metrics
            }
            
            comparison_data.append(comparison_row)
        
        comparison_df = pd.DataFrame(comparison_data)
        
        if not comparison_df.empty:
            # 순위 계산 (주요 지표별)
            ranking_columns = [
                'avg_performance_score', 'allocation_efficiency', 
                'avg_utilization_rate', 'avg_effectiveness_score'
            ]
            
            for column in ranking_columns:
                if column in comparison_df.columns:
                    comparison_df[f'{column}_rank'] = comparison_df[column].rank(ascending=False)
            
            # 종합 점수 계산 (가중 평균)
            if all(col in comparison_df.columns for col in ranking_columns):
                comparison_df['overall_score'] = (
                    comparison_df['avg_performance_score'] * 0.3 +
                    comparison_df['allocation_efficiency'] * 0.3 +
                    comparison_df['avg_utilization_rate'] * 0.2 +
                    comparison_df['avg_effectiveness_score'] * 0.2
                )
                comparison_df['overall_rank'] = comparison_df['overall_score'].rank(ascending=False)
        
        return comparison_df
    
    def _calculate_sensitivity_metrics(self, sensitivity_results: Dict[str, Any]) -> Dict[str, Any]:
        """민감도 지표 계산"""
        metrics = {}
        base_performance = 0
        
        # 기본 성과 점수 추출
        base_result = sensitivity_results['base_result']
        if 'analysis_results' in base_result and 'top_performers' in base_result['analysis_results']:
            performers_df = base_result['analysis_results']['top_performers']
            if not performers_df.empty:
                base_performance = performers_df['PERFORMANCE_SCORE'].mean()
        
        # 각 파라미터별 민감도 계산
        for param_name, param_results in sensitivity_results['parameter_variations'].items():
            performance_changes = []
            
            for result in param_results:
                if result['success'] and 'analysis_results' in result:
                    if 'top_performers' in result['analysis_results']:
                        performers_df = result['analysis_results']['top_performers']
                        if not performers_df.empty:
                            current_performance = performers_df['PERFORMANCE_SCORE'].mean()
                            change_pct = ((current_performance - base_performance) / base_performance * 100
                                        if base_performance > 0 else 0)
                            performance_changes.append({
                                'parameter_value': result['parameter_value'],
                                'performance_score': current_performance,
                                'change_percent': change_pct
                            })
            
            if performance_changes:
                # 민감도 지표 계산
                changes = [pc['change_percent'] for pc in performance_changes]
                metrics[param_name] = {
                    'max_positive_change': max(changes) if changes else 0,
                    'max_negative_change': min(changes) if changes else 0,
                    'volatility': pd.Series(changes).std() if len(changes) > 1 else 0,
                    'performance_changes': performance_changes
                }
        
        return metrics
    
    def get_experiment_summary(self, scenario_name: str) -> str:
        """
        실험 요약 텍스트 생성
        
        Args:
            scenario_name: 시나리오 이름
            
        Returns:
            str: 요약 텍스트
        """
        if scenario_name not in self.results:
            return f"시나리오 '{scenario_name}' 결과를 찾을 수 없습니다."
        
        result = self.results[scenario_name]
        
        if not result['success']:
            return f"시나리오 '{scenario_name}' 실행 실패: {result.get('error', 'Unknown error')}"
        
        summary_lines = [
            f"=== 실험 요약: {scenario_name} ===",
            f"실행 시간: {result['execution_time']:.2f}초",
            f"실험 디렉토리: {result['experiment_dir']}",
            ""
        ]
        
        # 요약 통계
        summary_stats = result.get('summary_stats', {})
        if summary_stats:
            summary_lines.extend([
                "📊 주요 통계:",
                f"• 총 할당 건수: {summary_stats.get('total_allocations', 0):,}",
                f"• 총 할당 수량: {summary_stats.get('total_quantity', 0):,}",
                f"• 커버된 매장 수: {summary_stats.get('stores_covered', 0)}",
                f"• 할당 효율성: {summary_stats.get('allocation_efficiency', 0):.1%}",
                ""
            ])
        
        # 분석 결과 요약
        analysis_results = result.get('analysis_results', {})
        
        if 'style_analysis' in analysis_results and not analysis_results['style_analysis'].empty:
            style_df = analysis_results['style_analysis']
            summary_lines.extend([
                "🎨 스타일 분석:",
                f"• 분석된 스타일 수: {len(style_df)}",
                f"• 평균 활용률: {style_df['UTILIZATION_RATE'].mean():.1%}",
                f"• 평균 색상 커버리지: {style_df['COLOR_COVERAGE_RATE'].mean():.1%}",
                f"• 평균 사이즈 커버리지: {style_df['SIZE_COVERAGE_RATE'].mean():.1%}",
                ""
            ])
        
        if 'top_performers' in analysis_results and not analysis_results['top_performers'].empty:
            performers_df = analysis_results['top_performers']
            summary_lines.extend([
                "🏆 매장 성과:",
                f"• 분석된 상위 매장 수: {len(performers_df)}",
                f"• 평균 성과 점수: {performers_df['PERFORMANCE_SCORE'].mean():.3f}",
                f"• 최고 성과 점수: {performers_df['PERFORMANCE_SCORE'].max():.3f}",
                ""
            ])
        
        if 'scarce_effectiveness' in analysis_results and not analysis_results['scarce_effectiveness'].empty:
            scarce_df = analysis_results['scarce_effectiveness']
            summary_lines.extend([
                "💎 희소 SKU 효과성:",
                f"• 분석된 희소 SKU 수: {len(scarce_df)}",
                f"• 평균 효과성 점수: {scarce_df['EFFECTIVENESS_SCORE'].mean():.3f}",
                f"• 최고 효과성 점수: {scarce_df['EFFECTIVENESS_SCORE'].max():.3f}",
                ""
            ])
        
        # 생성된 파일 정보
        plot_files = result.get('plot_files', {})
        if plot_files:
            summary_lines.extend([
                "📈 생성된 시각화:",
                *[f"• {plot_type}: {os.path.basename(filepath)}" 
                  for plot_type, filepath in plot_files.items()],
                ""
            ])
        
        return "\n".join(summary_lines)
    
    def cleanup_old_experiments(self, days_old: int = 7):
        """오래된 실험 결과 정리"""
        self.logger.info(f"{days_old}일 이상 된 실험 결과 정리 중...")
        
        file_manager = FileManager()
        cleaned_count = file_manager.cleanup_old_experiments(days_old)
        
        self.logger.info(f"{cleaned_count}개의 오래된 실험 폴더를 정리했습니다.")
        return cleaned_count 