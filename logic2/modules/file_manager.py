"""
실험 결과 저장 관리 모듈

이 모듈은 실험 결과를 체계적으로 저장하고 관리하는 기능을 제공합니다.
"""

import os
import json
import shutil
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging


class FileManager:
    """실험 결과 파일 관리 클래스"""
    
    def __init__(self, output_base_path: str = "../output"):
        """
        파일 관리자 초기화
        
        Args:
            output_base_path: 출력 기본 경로
        """
        self.output_base_path = output_base_path
        self.logger = logging.getLogger(__name__)
        
        # 출력 폴더 생성
        os.makedirs(output_base_path, exist_ok=True)
    
    def create_experiment_output_path(self, scenario_name: str) -> Tuple[str, Dict[str, str]]:
        """
        실험별 고유한 출력 폴더 및 파일명 생성
        
        Args:
            scenario_name: 실험 시나리오 이름
            
        Returns:
            Tuple[str, Dict[str, str]]: (실험 폴더 경로, 파일 경로 딕셔너리)
        """
        # 현재 시간 (YYYYMMDD_HHMMSS 형식)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 실험 폴더명: 시나리오_날짜시간
        experiment_folder = f"{scenario_name}_{timestamp}"
        
        # 전체 경로
        experiment_path = os.path.join(self.output_base_path, experiment_folder)
        
        # 폴더 생성
        os.makedirs(experiment_path, exist_ok=True)
        
        # 파일명 패턴 생성
        file_prefix = f"{scenario_name}_{timestamp}"
        
        file_paths = {
            'allocation_results': os.path.join(experiment_path, f"{file_prefix}_allocation_results.csv"),
            'store_summary': os.path.join(experiment_path, f"{file_prefix}_store_summary.csv"),
            'style_analysis': os.path.join(experiment_path, f"{file_prefix}_style_analysis.csv"),
            'top_performers': os.path.join(experiment_path, f"{file_prefix}_top_performers.csv"),
            'scarce_effectiveness': os.path.join(experiment_path, f"{file_prefix}_scarce_effectiveness.csv"),
            'sku_distribution': os.path.join(experiment_path, f"{file_prefix}_sku_distribution.csv"),
            'experiment_params': os.path.join(experiment_path, f"{file_prefix}_experiment_params.json"),
            'experiment_summary': os.path.join(experiment_path, f"{file_prefix}_experiment_summary.txt")
        }
        
        self.logger.info(f"실험 출력 경로 생성: {experiment_path}")
        
        return experiment_path, file_paths
    
    def save_experiment_metadata(self, file_paths: Dict[str, str], scenario_name: str, 
                                params: Dict[str, Any], optimization_result: Dict[str, Any]):
        """
        실험 메타데이터 저장
        
        Args:
            file_paths: 파일 경로 딕셔너리
            scenario_name: 시나리오 이름
            params: 실험 파라미터
            optimization_result: 최적화 결과
        """
        try:
            # 1. 실험 파라미터 JSON 저장
            experiment_info = {
                'scenario_name': scenario_name,
                'timestamp': datetime.now().isoformat(),
                'parameters': params,
                'optimization_status': optimization_result.get('status', 'unknown'),
                'objective_value': optimization_result.get('objective_value', None),
                'total_allocated_items': optimization_result.get('total_allocated_items', 0)
            }
            
            with open(file_paths['experiment_params'], 'w', encoding='utf-8') as f:
                json.dump(experiment_info, f, indent=2, ensure_ascii=False)
            
            # 2. 실험 요약 텍스트 저장
            summary_text = self._generate_summary_text(scenario_name, params, optimization_result)
            
            with open(file_paths['experiment_summary'], 'w', encoding='utf-8') as f:
                f.write(summary_text)
            
            self.logger.info(f"실험 메타데이터 저장 완료: {scenario_name}")
            
        except Exception as e:
            self.logger.error(f"메타데이터 저장 실패: {e}")
            raise
    
    def _generate_summary_text(self, scenario_name: str, params: Dict[str, Any], 
                              optimization_result: Dict[str, Any]) -> str:
        """실험 요약 텍스트 생성"""
        return f"""
========================================
실험 결과 요약
========================================

실험 시나리오: {scenario_name}
실험 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
설명: {params.get('description', 'N/A')}

📊 실험 파라미터:
- 커버리지 가중치: {params.get('coverage_weight', 0)}
- 균형 페널티: {params.get('balance_penalty', 0)}
- 배분 페널티: {params.get('allocation_penalty', 0)}
- 배분 범위: {params.get('allocation_range_min', 0)*100:.0f}% ~ {params.get('allocation_range_max', 0)*100:.0f}%
- 최소 커버리지: {params.get('min_coverage_threshold', 0)*100:.0f}%

⚡ 최적화 결과:
- 상태: {optimization_result.get('status', 'unknown')}
- 목적함수 값: {optimization_result.get('objective_value', 'N/A')}
- 총 할당 아이템: {optimization_result.get('total_allocated_items', 0)}
- 총 할당 수량: {optimization_result.get('total_allocated_quantity', 0)}
- 실행 시간: {optimization_result.get('execution_time', 'N/A')}초

📈 성과 메트릭:
- 종합 점수: {optimization_result.get('total_score', 'N/A')}
- 등급: {optimization_result.get('grade', 'N/A')}
- 색상 커버리지: {optimization_result.get('overall_color_coverage', 'N/A')}
- 사이즈 커버리지: {optimization_result.get('overall_size_coverage', 'N/A')}
- 배분 효율성: {optimization_result.get('overall_allocation_efficiency', 'N/A')}
- 배분 균형성: {optimization_result.get('allocation_balance', 'N/A')}

========================================
"""
    
    def save_dataframes(self, file_paths: Dict[str, str], dataframes: Dict[str, pd.DataFrame]):
        """
        DataFrame들을 CSV 파일로 저장
        
        Args:
            file_paths: 파일 경로 딕셔너리
            dataframes: 저장할 DataFrame 딕셔너리
        """
        try:
            saved_files = []
            
            for key, df in dataframes.items():
                if key in file_paths and df is not None and not df.empty:
                    df.to_csv(file_paths[key], index=False, encoding='utf-8-sig')
                    saved_files.append(file_paths[key])
            
            self.logger.info(f"{len(saved_files)}개 CSV 파일 저장 완료")
            return saved_files
            
        except Exception as e:
            self.logger.error(f"DataFrame 저장 실패: {e}")
            raise
    
    def list_experiment_results(self) -> List[Dict[str, Any]]:
        """저장된 모든 실험 결과 폴더 조회"""
        experiment_folders = []
        
        if not os.path.exists(self.output_base_path):
            return experiment_folders
        
        try:
            for folder in os.listdir(self.output_base_path):
                folder_path = os.path.join(self.output_base_path, folder)
                
                if os.path.isdir(folder_path) and '_' in folder:
                    # 폴더명 패턴: scenario_timestamp
                    parts = folder.split('_')
                    if len(parts) >= 2:
                        try:
                            # 타임스탬프 파싱 가능한지 확인
                            timestamp = '_'.join(parts[-2:])  # YYYYMMDD_HHMMSS
                            scenario = '_'.join(parts[:-2])  # 시나리오명
                            
                            # 메타데이터 파일 확인
                            params_file = os.path.join(folder_path, f"{folder}_experiment_params.json")
                            if os.path.exists(params_file):
                                with open(params_file, 'r', encoding='utf-8') as f:
                                    metadata = json.load(f)
                                
                                experiment_folders.append({
                                    'folder_name': folder,
                                    'scenario': scenario,
                                    'timestamp': timestamp,
                                    'status': metadata.get('optimization_status', 'unknown'),
                                    'folder_path': folder_path,
                                    'metadata': metadata
                                })
                        except Exception:
                            continue
            
            # 시간순 정렬 (최신 순)
            experiment_folders.sort(key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"실험 결과 조회 실패: {e}")
        
        return experiment_folders
    
    def load_experiment_data(self, folder_name: str) -> Optional[Dict[str, Any]]:
        """
        특정 실험의 데이터를 로드
        
        Args:
            folder_name: 실험 폴더 이름
            
        Returns:
            Optional[Dict[str, Any]]: 실험 데이터 (메타데이터 + DataFrame들)
        """
        folder_path = os.path.join(self.output_base_path, folder_name)
        
        if not os.path.exists(folder_path):
            self.logger.warning(f"실험 폴더를 찾을 수 없습니다: {folder_name}")
            return None
        
        try:
            # 메타데이터 로드
            params_file = os.path.join(folder_path, f"{folder_name}_experiment_params.json")
            with open(params_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # CSV 파일들 로드
            dataframes = {}
            csv_files = [
                'allocation_results', 'store_summary', 'style_analysis',
                'top_performers', 'scarce_effectiveness', 'sku_distribution'
            ]
            
            for csv_key in csv_files:
                csv_path = os.path.join(folder_path, f"{folder_name}_{csv_key}.csv")
                if os.path.exists(csv_path):
                    dataframes[csv_key] = pd.read_csv(csv_path)
            
            return {
                'metadata': metadata,
                'dataframes': dataframes,
                'folder_path': folder_path
            }
            
        except Exception as e:
            self.logger.error(f"실험 데이터 로드 실패: {folder_name} - {e}")
            return None
    
    def cleanup_old_experiments(self, keep_latest: int = 10) -> int:
        """
        오래된 실험 결과 정리 (최신 N개만 유지)
        
        Args:
            keep_latest: 유지할 최신 실험 수
            
        Returns:
            int: 삭제된 실험 수
        """
        experiments = self.list_experiment_results()
        
        if len(experiments) <= keep_latest:
            self.logger.info(f"실험 결과가 {len(experiments)}개로 정리 기준({keep_latest}개) 이하입니다.")
            return 0
        
        # 오래된 실험들 선택
        to_delete = experiments[keep_latest:]
        
        deleted_count = 0
        for exp in to_delete:
            try:
                shutil.rmtree(exp['folder_path'])
                self.logger.info(f"삭제 완료: {exp['folder_name']}")
                deleted_count += 1
            except Exception as e:
                self.logger.warning(f"삭제 실패: {exp['folder_name']} - {e}")
        
        self.logger.info(f"정리 완료: {deleted_count}개 실험 폴더 삭제됨")
        return deleted_count
    
    def export_experiment_comparison(self, experiment_folders: List[str], 
                                   output_file: str) -> str:
        """
        여러 실험 결과를 비교 분석하여 엑셀 파일로 내보내기
        
        Args:
            experiment_folders: 비교할 실험 폴더 이름 리스트
            output_file: 출력 파일 경로
            
        Returns:
            str: 생성된 파일 경로
        """
        try:
            comparison_data = []
            
            for folder_name in experiment_folders:
                experiment_data = self.load_experiment_data(folder_name)
                if experiment_data:
                    metadata = experiment_data['metadata']
                    
                    comparison_data.append({
                        'Experiment': folder_name,
                        'Scenario': metadata.get('scenario_name', ''),
                        'Timestamp': metadata.get('timestamp', ''),
                        'Status': metadata.get('optimization_status', ''),
                        'Objective_Value': metadata.get('objective_value', 0),
                        'Total_Items': metadata.get('total_allocated_items', 0),
                        'Total_Quantity': metadata.get('total_allocated_quantity', 0),
                        'Coverage_Weight': metadata['parameters'].get('coverage_weight', 0),
                        'Balance_Penalty': metadata['parameters'].get('balance_penalty', 0),
                        'Allocation_Penalty': metadata['parameters'].get('allocation_penalty', 0),
                        'Allocation_Range_Min': metadata['parameters'].get('allocation_range_min', 0),
                        'Allocation_Range_Max': metadata['parameters'].get('allocation_range_max', 0),
                        'Min_Coverage_Threshold': metadata['parameters'].get('min_coverage_threshold', 0)
                    })
            
            # DataFrame으로 변환하여 엑셀 저장
            df_comparison = pd.DataFrame(comparison_data)
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df_comparison.to_excel(writer, sheet_name='Experiment_Comparison', index=False)
                
                # 각 실험의 상세 데이터도 별도 시트로 저장
                for folder_name in experiment_folders:
                    experiment_data = self.load_experiment_data(folder_name)
                    if experiment_data and experiment_data['dataframes']:
                        for sheet_name, df in experiment_data['dataframes'].items():
                            if not df.empty:
                                full_sheet_name = f"{folder_name[:10]}_{sheet_name}"[:31]  # 엑셀 시트명 길이 제한
                                df.to_excel(writer, sheet_name=full_sheet_name, index=False)
            
            self.logger.info(f"실험 비교 파일 생성 완료: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"실험 비교 파일 생성 실패: {e}")
            raise
    
    def get_storage_summary(self) -> Dict[str, Any]:
        """저장소 요약 정보 반환"""
        experiments = self.list_experiment_results()
        
        total_size = 0
        scenario_counts = {}
        
        for exp in experiments:
            # 폴더 크기 계산
            folder_size = self._get_folder_size(exp['folder_path'])
            total_size += folder_size
            
            # 시나리오별 카운트
            scenario = exp['scenario']
            scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1
        
        return {
            'total_experiments': len(experiments),
            'total_size_mb': total_size / (1024 * 1024),
            'scenario_counts': scenario_counts,
            'latest_experiment': experiments[0] if experiments else None,
            'storage_path': self.output_base_path
        }
    
    def _get_folder_size(self, folder_path: str) -> int:
        """폴더 크기를 바이트 단위로 계산"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception:
            pass
        return total_size 