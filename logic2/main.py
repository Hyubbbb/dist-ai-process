"""
SKU Distribution Optimization System - Main Entry Point

메인 실행 스크립트
"""

import argparse
import logging
import sys
import yaml
import json
from pathlib import Path

# 모듈 import
from modules import (
    DataLoader, ExperimentConfig, FileManager, 
    SKUOptimizer, ResultAnalyzer, ResultVisualizer, ExperimentRunner
)


def setup_logging(level: str = "INFO"):
    """로깅 설정"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('optimization.log')
        ]
    )


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='SKU Distribution Optimization System')
    
    # 필수 인자들
    parser.add_argument('--sku_file', required=True, help='SKU 데이터 파일 경로')
    parser.add_argument('--store_file', required=True, help='매장 데이터 파일 경로')
    
    # 선택적 인자들
    parser.add_argument('--scenario', default='baseline', help='실험 시나리오')
    parser.add_argument('--config', help='설정 파일 경로 (YAML/JSON)')
    parser.add_argument('--output_dir', default='../output', help='출력 디렉토리')
    parser.add_argument('--log_level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    # 실행 모드
    parser.add_argument('--mode', default='single', 
                       choices=['single', 'batch', 'compare', 'sensitivity'],
                       help='실행 모드')
    
    # 배치 실행용
    parser.add_argument('--scenarios', nargs='+', help='배치 실행할 시나리오들')
    
    # 비교 분석용
    parser.add_argument('--compare_experiments', nargs='+', help='비교할 실험 폴더들')
    
    args = parser.parse_args()
    
    # 로깅 설정
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # 1. 데이터 로드
        logger.info("데이터 로딩 시작...")
        data_loader = DataLoader(args.sku_file, args.store_file)
        data = data_loader.preprocess_data()
        
        # 데이터 검증
        issues = data_loader.validate_data()
        if issues:
            logger.warning(f"데이터 검증 경고: {issues}")
        
        logger.info(data_loader.get_data_summary())
        
        # 2. 실험 설정 로드
        logger.info("실험 설정 로딩...")
        config = ExperimentConfig(args.config if args.config else None)
        
        # 3. 파일 관리자 초기화
        file_manager = FileManager(args.output_dir)
        
        # 4. 실행 모드별 처리
        if args.mode == 'single':
            run_single_experiment(data, config, file_manager, args.scenario, logger)
            
        elif args.mode == 'batch':
            scenarios = args.scenarios if args.scenarios else config.get_scenario_list()
            run_batch_experiments(data, config, file_manager, scenarios, logger)
            
        elif args.mode == 'compare':
            if not args.compare_experiments:
                logger.error("비교 모드에서는 --compare_experiments 인자가 필요합니다.")
                return
            compare_experiments(file_manager, args.compare_experiments, logger)
            
        elif args.mode == 'sensitivity':
            base_scenario = args.scenario
            run_sensitivity_analysis(data, config, file_manager, base_scenario, logger)
        
        logger.info("프로그램 실행 완료!")
        
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류 발생: {e}")
        sys.exit(1)


def run_single_experiment(data, config, file_manager, scenario_name, logger):
    """단일 실험 실행"""
    logger.info(f"단일 실험 실행: {scenario_name}")
    
    # 시나리오 파라미터 가져오기
    params = config.get_scenario(scenario_name)
    
    # 파라미터 검증
    errors = config.validate_scenario(params)
    if errors:
        logger.error(f"시나리오 파라미터 오류: {errors}")
        return
    
    # 파라미터 디버깅 로그 추가
    logger.info(f"로딩된 시나리오 파라미터: {scenario_name}")
    logger.info(f"use_proportional_allocation: {params.get('use_proportional_allocation', 'NOT_FOUND')}")
    logger.info(f"min_allocation_multiplier: {params.get('min_allocation_multiplier', 'NOT_FOUND')}")
    logger.info(f"max_allocation_multiplier: {params.get('max_allocation_multiplier', 'NOT_FOUND')}")
    logger.info(f"allocation_range_min: {params.get('allocation_range_min', 'NOT_FOUND')}")
    logger.info(f"allocation_range_max: {params.get('allocation_range_max', 'NOT_FOUND')}")
    
    # 출력 경로 생성
    experiment_path, file_paths = file_manager.create_experiment_output_path(scenario_name)
    
    # 최적화 실행
    optimizer = SKUOptimizer(data)
    result = optimizer.optimize(params)
    
    if result['status'] != 'success':
        logger.error(f"최적화 실패: {result}")
        return
    
    # 결과 분석
    analyzer = ResultAnalyzer(data, optimizer)
    analysis_results = analyzer.analyze()
    
    # 결과 저장
    dataframes = {
        'allocation_results': optimizer.get_allocation_results(),
        'store_summary': optimizer.get_store_summary(),
        'style_analysis': analysis_results.get('style_analysis'),
        'top_performers': analysis_results.get('top_performers'),
        'scarce_effectiveness': analysis_results.get('scarce_effectiveness'),
        'sku_distribution': analysis_results.get('sku_distribution')
    }
    
    file_manager.save_dataframes(file_paths, dataframes)
    file_manager.save_experiment_metadata(file_paths, scenario_name, params, result)
    
    logger.info(f"실험 결과 저장 완료: {experiment_path}")


def run_batch_experiments(data, config, file_manager, scenarios, logger):
    """배치 실험 실행"""
    logger.info(f"배치 실험 실행: {scenarios}")
    
    results = []
    
    for scenario_name in scenarios:
        logger.info(f"시나리오 실행 중: {scenario_name}")
        
        try:
            run_single_experiment(data, config, file_manager, scenario_name, logger)
            results.append({'scenario': scenario_name, 'status': 'success'})
        except Exception as e:
            logger.error(f"시나리오 {scenario_name} 실행 실패: {e}")
            results.append({'scenario': scenario_name, 'status': 'failed', 'error': str(e)})
    
    # 배치 실행 요약
    logger.info("배치 실행 완료!")
    for result in results:
        logger.info(f"  {result['scenario']}: {result['status']}")


def compare_experiments(file_manager, experiment_folders, logger):
    """실험 비교 분석"""
    logger.info(f"실험 비교 분석: {experiment_folders}")
    
    experiments = file_manager.list_experiment_results()
    
    # 요청된 실험들이 존재하는지 확인
    available_folders = [exp['folder_name'] for exp in experiments]
    missing_folders = [folder for folder in experiment_folders if folder not in available_folders]
    
    if missing_folders:
        logger.warning(f"존재하지 않는 실험 폴더들: {missing_folders}")
        experiment_folders = [folder for folder in experiment_folders if folder in available_folders]
    
    if not experiment_folders:
        logger.error("비교할 유효한 실험이 없습니다.")
        return
    
    # 비교 분석 수행
    runner = ExperimentRunner(None, None, file_manager)
    comparison_df = runner.compare_experiments(experiment_folders)
    
    if comparison_df is not None:
        logger.info("실험 비교 결과:")
        print(comparison_df.to_string())
        
        # 엑셀로 내보내기
        output_file = f"experiment_comparison_{len(experiment_folders)}_experiments.xlsx"
        file_manager.export_experiment_comparison(experiment_folders, output_file)
        logger.info(f"비교 결과 파일 생성: {output_file}")


def run_sensitivity_analysis(data, config, file_manager, base_scenario, logger):
    """민감도 분석 실행"""
    logger.info(f"민감도 분석 실행 (기준: {base_scenario})")
    
    # 민감도 분석 시나리오 생성
    sensitivity_scenarios = config.generate_sensitivity_scenarios(base_scenario)
    
    logger.info(f"총 {len(sensitivity_scenarios)}개 민감도 시나리오 생성")
    
    # 각 시나리오에 대해 배치 실행
    scenario_names = list(sensitivity_scenarios.keys())
    
    # 기존 시나리오에 민감도 시나리오 추가
    for name, params in sensitivity_scenarios.items():
        config.add_scenario(name, params)
    
    run_batch_experiments(data, config, file_manager, scenario_names, logger)


if __name__ == "__main__":
    main() 