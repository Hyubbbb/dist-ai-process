"""
실험 관리 모듈
"""

import os
import json
import pandas as pd
from datetime import datetime
from config import OUTPUT_PATH


class ExperimentManager:
    """실험 관리 및 결과 저장을 담당하는 클래스"""
    
    def __init__(self):
        self.output_path = OUTPUT_PATH
        
    def create_experiment_output_path(self, scenario_name):
        """실험별 고유한 출력 폴더 및 파일명 생성"""
        
        # 현재 시간 (YYYYMMDD_HHMMSS 형식)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 실험 폴더명: 시나리오_날짜시간
        experiment_folder = f"{scenario_name}_{timestamp}"
        
        # 전체 경로
        experiment_path = os.path.join(self.output_path, experiment_folder)
        
        # 폴더 생성 (존재하지 않으면)
        os.makedirs(experiment_path, exist_ok=True)
        
        # 파일명 패턴 생성
        file_prefix = f"{scenario_name}_{timestamp}"
        
        file_paths = {
            'allocation_results': os.path.join(experiment_path, f"{file_prefix}_allocation_results.csv"),
            'store_summary': os.path.join(experiment_path, f"{file_prefix}_store_summary.csv"),
            'style_analysis': os.path.join(experiment_path, f"{file_prefix}_style_analysis.csv"),
            'top_performers': os.path.join(experiment_path, f"{file_prefix}_top_performers.csv"),
            'scarce_effectiveness': os.path.join(experiment_path, f"{file_prefix}_scarce_effectiveness.csv"),
            'experiment_params': os.path.join(experiment_path, f"{file_prefix}_experiment_params.json"),
            'experiment_summary': os.path.join(experiment_path, f"{file_prefix}_experiment_summary.txt")
        }
        
        return experiment_path, file_paths
    
    def save_experiment_results(self, file_paths, df_results, analysis_results, params, 
                              scenario_name, optimization_summary):
        """실험 결과 저장"""
        
        print(f"\n💾 실험 결과 저장 중...")
        
        try:
            # 1. 할당 결과 CSV 저장
            if len(df_results) > 0:
                df_results.to_csv(file_paths['allocation_results'], index=False, encoding='utf-8-sig')
                print(f"   ✅ 할당 결과: {os.path.basename(file_paths['allocation_results'])}")
            
            # 2. 매장별 요약 저장
            if 'performance_analysis' in analysis_results:
                performance_data = analysis_results['performance_analysis']['all_performance']
                df_store_summary = pd.DataFrame(performance_data)
                df_store_summary.to_csv(file_paths['store_summary'], index=False, encoding='utf-8-sig')
                print(f"   ✅ 매장 요약: {os.path.basename(file_paths['store_summary'])}")
            
            # 3. 스타일 분석 저장
            if 'style_coverage' in analysis_results:
                style_data = self._create_style_analysis_df(analysis_results)
                style_data.to_csv(file_paths['style_analysis'], index=False, encoding='utf-8-sig')
                print(f"   ✅ 스타일 분석: {os.path.basename(file_paths['style_analysis'])}")
            
            # 4. 상위 성과자 저장
            if 'performance_analysis' in analysis_results:
                top_performers = analysis_results['performance_analysis']['top_performers']
                df_top = pd.DataFrame(top_performers)
                df_top.to_csv(file_paths['top_performers'], index=False, encoding='utf-8-sig')
                print(f"   ✅ 상위 성과자: {os.path.basename(file_paths['top_performers'])}")
            
            # 5. 희소 SKU 효과성 저장
            if 'scarce_analysis' in analysis_results:
                df_scarce = pd.DataFrame(analysis_results['scarce_analysis'])
                df_scarce.to_csv(file_paths['scarce_effectiveness'], index=False, encoding='utf-8-sig')
                print(f"   ✅ 희소 SKU 효과성: {os.path.basename(file_paths['scarce_effectiveness'])}")
            
            # 6. 실험 메타데이터 저장
            self._save_experiment_metadata(file_paths, scenario_name, params, optimization_summary, analysis_results)
            
            print(f"📁 실험 '{scenario_name}' 결과 저장 완료!")
            
        except Exception as e:
            print(f"❌ 실험 결과 저장 실패: {str(e)}")
            raise
    
    def _create_style_analysis_df(self, analysis_results):
        """스타일 분석 데이터프레임 생성"""
        style_coverage = analysis_results['style_coverage']
        overall_eval = analysis_results['overall_evaluation']
        
        style_data = [{
            'Metric': 'Color Coverage',
            'Average': style_coverage['color_coverage']['avg_ratio'],
            'Maximum': style_coverage['color_coverage']['max_ratio'],
            'Minimum': style_coverage['color_coverage']['min_ratio'],
            'Total_Count': style_coverage['color_coverage']['total_colors']
        }, {
            'Metric': 'Size Coverage',
            'Average': style_coverage['size_coverage']['avg_ratio'],
            'Maximum': style_coverage['size_coverage']['max_ratio'],
            'Minimum': style_coverage['size_coverage']['min_ratio'],
            'Total_Count': style_coverage['size_coverage']['total_sizes']
        }, {
            'Metric': 'Overall Performance',
            'Average': overall_eval['total_score'],
            'Maximum': None,
            'Minimum': None,
            'Total_Count': None
        }]
        
        return pd.DataFrame(style_data)
    
    def _save_experiment_metadata(self, file_paths, scenario_name, params, optimization_summary, analysis_results):
        """실험 메타데이터 저장"""
        
        # JSON 직렬화 가능하도록 데이터 정리
        def make_json_serializable(obj):
            """JSON 직렬화 가능한 형태로 변환"""
            if isinstance(obj, dict):
                # tuple 키를 문자열로 변환
                return {str(k): make_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [make_json_serializable(item) for item in obj]
            elif isinstance(obj, (int, float, str, bool)) or obj is None:
                return obj
            else:
                return str(obj)  # 기타 객체들은 문자열로 변환
        
        # 1. 실험 파라미터 JSON 저장
        experiment_info = {
            'scenario_name': scenario_name,
            'timestamp': datetime.now().isoformat(),
            'parameters': make_json_serializable(params),
            'optimization_summary': make_json_serializable(optimization_summary),
            'overall_evaluation': make_json_serializable(analysis_results.get('overall_evaluation', {})) if analysis_results else {}
        }
        
        with open(file_paths['experiment_params'], 'w', encoding='utf-8') as f:
            json.dump(experiment_info, f, indent=2, ensure_ascii=False)
        
        # 2. 실험 요약 텍스트 저장
        summary_text = self._create_summary_text(scenario_name, params, optimization_summary, analysis_results)
        
        with open(file_paths['experiment_summary'], 'w', encoding='utf-8') as f:
            f.write(summary_text)
        
        print(f"   ✅ 메타데이터: {os.path.basename(file_paths['experiment_params'])}")
        print(f"   ✅ 요약: {os.path.basename(file_paths['experiment_summary'])}")
    
    def _create_summary_text(self, scenario_name, params, optimization_summary, analysis_results):
        """실험 요약 텍스트 생성"""
        
        summary_text = f"""
========================================
실험 결과 요약 - {scenario_name}
========================================

실험 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
스타일: {params.get('target_style', 'N/A')}
설명: {params.get('description', 'N/A')}

📊 실험 파라미터:
- 커버리지 가중치: {params.get('coverage_weight', 'N/A')}
- 균형 페널티: {params.get('balance_penalty', 'N/A')}
- 배분 페널티: {params.get('allocation_penalty', 'N/A')}
- 배분 범위: {params.get('allocation_range_min', 0)*100:.0f}% ~ {params.get('allocation_range_max', 0)*100:.0f}%
- 최소 커버리지: {params.get('min_coverage_threshold', 0)*100:.0f}%

⚡ 최적화 결과:
- 상태: {optimization_summary.get('status', 'unknown')}
- 총 배분량: {optimization_summary.get('total_allocated', 'N/A')}
- 배분률: {optimization_summary.get('allocation_rate', 0)*100:.1f}%
- 배분 받은 매장: {optimization_summary.get('allocated_stores', 'N/A')}개
"""
        
        # 성과 평가 추가 (있는 경우)
        if analysis_results and 'overall_evaluation' in analysis_results:
            overall_eval = analysis_results['overall_evaluation']
            summary_text += f"""
🏅 성과 평가:
- 색상 커버리지: {overall_eval.get('overall_color_coverage', 0):.3f}
- 사이즈 커버리지: {overall_eval.get('overall_size_coverage', 0):.3f}
- 배분 효율성: {overall_eval.get('overall_allocation_efficiency', 0):.4f}
- 배분 균형성: {overall_eval.get('allocation_balance', 0):.3f}
- 종합 등급: {overall_eval.get('grade', 'N/A')}
- 종합 점수: {overall_eval.get('total_score', 0):.3f}
"""
        
        summary_text += f"""
📁 생성된 파일들:
- allocation_results.csv: 상세 할당 결과
- store_summary.csv: 매장별 성과 요약
- style_analysis.csv: 스타일별 커버리지 분석
- top_performers.csv: 최고 성과 매장
- scarce_effectiveness.csv: 희소 SKU 효과성
- experiment_params.json: 실험 파라미터
- experiment_summary.txt: 실험 요약

========================================
"""
        
        return summary_text
    
    def load_experiment_results(self, experiment_folder):
        """저장된 실험 결과 로드"""
        experiment_path = os.path.join(self.output_path, experiment_folder)
        
        if not os.path.exists(experiment_path):
            raise ValueError(f"실험 폴더를 찾을 수 없습니다: {experiment_folder}")
        
        # 파일 경로 구성
        files = os.listdir(experiment_path)
        base_name = experiment_folder  # 폴더명이 곧 파일 prefix
        
        file_paths = {}
        for file in files:
            if file.endswith('_allocation_results.csv'):
                file_paths['allocation_results'] = os.path.join(experiment_path, file)
            elif file.endswith('_experiment_params.json'):
                file_paths['experiment_params'] = os.path.join(experiment_path, file)
            # ... 다른 파일들도 추가 가능
        
        # 결과 로드
        results = {}
        
        if 'allocation_results' in file_paths:
            results['allocation_results'] = pd.read_csv(file_paths['allocation_results'])
        
        if 'experiment_params' in file_paths:
            with open(file_paths['experiment_params'], 'r', encoding='utf-8') as f:
                results['experiment_params'] = json.load(f)
        
        return results
    
    def list_experiments(self):
        """저장된 실험 목록 반환"""
        if not os.path.exists(self.output_path):
            return []
        
        experiments = []
        for folder in os.listdir(self.output_path):
            folder_path = os.path.join(self.output_path, folder)
            if os.path.isdir(folder_path):
                # 폴더 정보 수집
                experiment_info = {
                    'folder_name': folder,
                    'path': folder_path,
                    'created_time': datetime.fromtimestamp(os.path.getctime(folder_path))
                }
                
                # 파라미터 파일이 있으면 추가 정보 로드
                param_files = [f for f in os.listdir(folder_path) if f.endswith('_experiment_params.json')]
                if param_files:
                    param_file = os.path.join(folder_path, param_files[0])
                    try:
                        with open(param_file, 'r', encoding='utf-8') as f:
                            params = json.load(f)
                            experiment_info['scenario_name'] = params.get('scenario_name', 'Unknown')
                            experiment_info['target_style'] = params.get('parameters', {}).get('target_style', 'Unknown')
                    except:
                        experiment_info['scenario_name'] = 'Unknown'
                        experiment_info['target_style'] = 'Unknown'
                
                experiments.append(experiment_info)
        
        # 생성 시간 순으로 정렬 (최신순)
        experiments.sort(key=lambda x: x['created_time'], reverse=True)
        
        return experiments 