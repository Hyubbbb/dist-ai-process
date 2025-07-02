"""
실험 시나리오 및 파라미터 설정 모듈

이 모듈은 다양한 실험 시나리오의 파라미터를 정의하고 관리합니다.
"""

from typing import Dict, List, Any
import yaml
import json


class ExperimentConfig:
    """실험 설정 관리 클래스"""
    
    def __init__(self, config_file: str = None):
        """
        실험 설정 초기화
        
        Args:
            config_file: 설정 파일 경로 (YAML 또는 JSON)
        """
        self.config_file = config_file
        self.scenarios = self._get_default_scenarios()
        self.evaluation_metrics = self._get_evaluation_metrics()
        self.experiment_plan = self._get_experiment_plan()
        
        if config_file:
            self.load_config(config_file)
    
    def _get_default_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """기본 실험 시나리오 정의"""
        return {
            "baseline": {
                "description": "기본 수요 기반 분배 (커버리지 최적화 없음)",
                "coverage_weight": 0.0,
                "balance_penalty": 0.0,
                "allocation_penalty": 0.0,
                "allocation_range_min": 0.3,
                "allocation_range_max": 3.0,
                "min_coverage_threshold": 0.0
            },
            
            "coverage_focused": {
                "description": "커버리지 최우선 (매장별 상품 다양성 극대화)",
                "coverage_weight": 1.0,
                "balance_penalty": 0.0,
                "allocation_penalty": 0.0,
                "allocation_range_min": 0.2,
                "allocation_range_max": 5.0,
                "min_coverage_threshold": 0.0
            },
            
            "balance_focused": {
                "description": "균형 최우선 (색상-사이즈 균형 + 공정한 배분)",
                "coverage_weight": 0.1,
                "balance_penalty": 1.0,
                "allocation_penalty": 2.0,
                "allocation_range_min": 0.8,
                "allocation_range_max": 1.2,
                "min_coverage_threshold": 0.1
            },
            
            "hybrid": {
                "description": "균형잡힌 접근 (커버리지 + 균형 + 효율성)",
                "coverage_weight": 0.5,
                "balance_penalty": 0.3,
                "allocation_penalty": 0.1,
                "allocation_range_min": 0.5,
                "allocation_range_max": 2.0,
                "min_coverage_threshold": 0.05
            },
            
            "extreme_coverage": {
                "description": "극단적 커버리지 추구 (시스템 한계 테스트)",
                "coverage_weight": 5.0,
                "balance_penalty": 1.0,
                "allocation_penalty": 0.1,
                "allocation_range_min": 0.2,
                "allocation_range_max": 5.0,
                "min_coverage_threshold": 0.2
            }
        }
    
    def _get_evaluation_metrics(self) -> Dict[str, List[str]]:
        """평가 메트릭 정의"""
        return {
            "커버리지 메트릭": [
                "평균 색상 커버리지 비율",
                "평균 사이즈 커버리지 비율",
                "커버리지 0인 매장 수",
                "완전 커버리지(100%) 매장 수"
            ],
            
            "균형 메트릭": [
                "색상-사이즈 커버리지 불균형 평균",
                "매장별 배분량 표준편차",
                "매장별 배분 비율 상관계수",
                "Gini 계수 (분배 불평등)"
            ],
            
            "비즈니스 메트릭": [
                "총 할당 효율성",
                "희소 SKU 활용률",
                "매장별 상품 다양성 지수",
                "예상 고객 만족도 점수"
            ]
        }
    
    def _get_experiment_plan(self) -> Dict[str, Dict[str, Any]]:
        """실험 수행 계획 정의"""
        return {
            "Phase 1: 베이스라인 확립": {
                "scenarios": ["baseline"],
                "purpose": "기본 성능 측정, 다른 시나리오와 비교할 기준점 설정",
                "expected_outcome": "수요 기반 분배, 낮은 커버리지, 높은 매장별 편차"
            },
            
            "Phase 2: 단일 목표 최적화": {
                "scenarios": ["coverage_focused", "balance_focused"],
                "purpose": "각 목표를 극대화했을 때의 효과와 부작용 측정",
                "expected_outcome": "특정 메트릭은 높지만 다른 메트릭 희생"
            },
            
            "Phase 3: 균형점 탐색": {
                "scenarios": ["hybrid"],
                "purpose": "실용적인 트레이드오프 지점 찾기",
                "expected_outcome": "모든 메트릭에서 적절한 성능"
            },
            
            "Phase 4: 극단적 케이스": {
                "scenarios": ["extreme_coverage"],
                "purpose": "시스템의 한계 테스트, 실현 가능성 검증",
                "expected_outcome": "최고 커버리지지만 실용성 낮을 수 있음"
            }
        }
    
    def get_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """
        특정 시나리오의 파라미터를 반환
        
        Args:
            scenario_name: 시나리오 이름
            
        Returns:
            Dict[str, Any]: 시나리오 파라미터
        """
        if scenario_name not in self.scenarios:
            raise ValueError(f"시나리오 '{scenario_name}'를 찾을 수 없습니다. "
                           f"사용 가능한 시나리오: {list(self.scenarios.keys())}")
        
        return self.scenarios[scenario_name].copy()
    
    def get_all_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """모든 시나리오 반환"""
        return self.scenarios.copy()
    
    def add_scenario(self, scenario_name: str, params: Dict[str, Any]):
        """
        새 시나리오 추가
        
        Args:
            scenario_name: 시나리오 이름
            params: 시나리오 파라미터
        """
        required_params = [
            'description', 'coverage_weight', 'balance_penalty', 
            'allocation_penalty', 'allocation_range_min', 
            'allocation_range_max', 'min_coverage_threshold'
        ]
        
        missing_params = [p for p in required_params if p not in params]
        if missing_params:
            raise ValueError(f"필수 파라미터가 누락되었습니다: {missing_params}")
        
        self.scenarios[scenario_name] = params
    
    def generate_sensitivity_scenarios(self, base_scenario: str = "hybrid") -> Dict[str, Dict[str, Any]]:
        """
        민감도 분석용 시나리오 생성
        
        Args:
            base_scenario: 기준 시나리오
            
        Returns:
            Dict[str, Dict[str, Any]]: 민감도 분석 시나리오들
        """
        if base_scenario not in self.scenarios:
            raise ValueError(f"기준 시나리오 '{base_scenario}'를 찾을 수 없습니다.")
        
        base_params = self.scenarios[base_scenario].copy()
        sensitivity_scenarios = {}
        
        # Coverage Weight 민감도 (0.1, 0.3, 0.5, 1.0, 2.0)
        for weight in [0.1, 0.3, 0.5, 1.0, 2.0]:
            params = base_params.copy()
            params['coverage_weight'] = weight
            params['description'] = f"커버리지 가중치 민감도 테스트: {weight}"
            sensitivity_scenarios[f"sensitivity_coverage_{weight}"] = params
        
        # Balance Penalty 민감도 (0.01, 0.05, 0.1, 0.5, 1.0)
        for penalty in [0.01, 0.05, 0.1, 0.5, 1.0]:
            params = base_params.copy()
            params['balance_penalty'] = penalty
            params['description'] = f"균형 페널티 민감도 테스트: {penalty}"
            sensitivity_scenarios[f"sensitivity_balance_{penalty}"] = params
        
        # Allocation Range 민감도
        ranges = [(0.3, 2.0), (0.5, 1.5), (0.7, 1.3), (0.8, 1.2), (0.9, 1.1)]
        for min_r, max_r in ranges:
            params = base_params.copy()
            params['allocation_range_min'] = min_r
            params['allocation_range_max'] = max_r
            params['description'] = f"배분 범위 민감도: {min_r*100:.0f}%-{max_r*100:.0f}%"
            sensitivity_scenarios[f"sensitivity_range_{min_r}_{max_r}"] = params
        
        return sensitivity_scenarios
    
    def validate_scenario(self, params: Dict[str, Any]) -> List[str]:
        """
        시나리오 파라미터 유효성 검증
        
        Args:
            params: 시나리오 파라미터
            
        Returns:
            List[str]: 검증 오류 메시지 리스트
        """
        errors = []
        
        # 필수 파라미터 확인
        required_params = [
            'coverage_weight', 'balance_penalty', 'allocation_penalty',
            'allocation_range_min', 'allocation_range_max', 'min_coverage_threshold'
        ]
        
        for param in required_params:
            if param not in params:
                errors.append(f"필수 파라미터 누락: {param}")
            elif not isinstance(params[param], (int, float)):
                errors.append(f"파라미터 {param}는 숫자여야 합니다.")
        
        # 선택적 QTY_SUM 기반 비례 배분 파라미터 확인
        proportional_params = [
            'use_proportional_allocation', 'min_allocation_multiplier', 'max_allocation_multiplier',
            'enforce_scarce_distribution', 'scarce_min_allocation_multiplier', 'scarce_max_allocation_multiplier',
            'apply_store_size_constraints', 'large_store_max_multiplier', 'small_store_max_multiplier',
            'sku_distribution_penalty', 'min_allocation_per_store', 'min_stores_per_sku'
        ]
        
        # 기존 MAX_SKU_CONCENTRATION 관련 파라미터들 (백워드 호환성)
        legacy_params = ['max_sku_concentration']
        
        all_optional_params = proportional_params + legacy_params
        
        for param in all_optional_params:
            if param in params:
                if param in ['use_proportional_allocation', 'enforce_scarce_distribution', 'apply_store_size_constraints']:
                    # 부울 타입 확인
                    if not isinstance(params[param], bool):
                        errors.append(f"파라미터 {param}는 부울(True/False)이어야 합니다.")
                elif param in ['min_allocation_per_store', 'min_stores_per_sku']:
                    # 정수 타입 확인
                    if not isinstance(params[param], int):
                        errors.append(f"파라미터 {param}는 정수여야 합니다.")
                else:
                    # 숫자 타입 확인
                    if not isinstance(params[param], (int, float)):
                        errors.append(f"파라미터 {param}는 숫자여야 합니다.")
        
        # 범위 유효성 확인
        if 'allocation_range_min' in params and 'allocation_range_max' in params:
            if params['allocation_range_min'] >= params['allocation_range_max']:
                errors.append("allocation_range_min이 allocation_range_max보다 크거나 같습니다.")
        
        # 비례 배분 승수 범위 확인
        if 'min_allocation_multiplier' in params and 'max_allocation_multiplier' in params:
            if params['min_allocation_multiplier'] >= params['max_allocation_multiplier']:
                errors.append("min_allocation_multiplier가 max_allocation_multiplier보다 크거나 같습니다.")
        
        if 'scarce_min_allocation_multiplier' in params and 'scarce_max_allocation_multiplier' in params:
            if params['scarce_min_allocation_multiplier'] >= params['scarce_max_allocation_multiplier']:
                errors.append("scarce_min_allocation_multiplier가 scarce_max_allocation_multiplier보다 크거나 같습니다.")
        
        # 비음수 확인
        non_negative_params = [
            'coverage_weight', 'balance_penalty', 'allocation_penalty',
            'sku_distribution_penalty', 'min_allocation_per_store', 'min_stores_per_sku',
            'min_allocation_multiplier', 'max_allocation_multiplier',
            'scarce_min_allocation_multiplier', 'scarce_max_allocation_multiplier',
            'large_store_max_multiplier', 'small_store_max_multiplier'
        ]
        for param in non_negative_params:
            if param in params and params[param] < 0:
                errors.append(f"파라미터 {param}는 0 이상이어야 합니다.")
        
        # 비율 파라미터 확인 (0-1 범위)
        ratio_params = ['min_coverage_threshold', 'max_sku_concentration']
        for param in ratio_params:
            if param in params and not (0 <= params[param] <= 1):
                errors.append(f"파라미터 {param}는 0-1 범위여야 합니다.")
        
        # QTY_SUM 기반 비례 배분 관련 논리적 일관성 확인
        if 'use_proportional_allocation' in params and params['use_proportional_allocation']:
            # 비례 배분 활성화 시 필수 파라미터 확인
            required_proportional_params = ['min_allocation_multiplier', 'max_allocation_multiplier']
            for param in required_proportional_params:
                if param not in params:
                    errors.append(f"use_proportional_allocation이 True일 때 {param} 파라미터가 필요합니다.")
        
        if 'enforce_scarce_distribution' in params and params['enforce_scarce_distribution']:
            # 희소 SKU 분산 제약 활성화 시 관련 파라미터들 확인
            required_scarce_params = ['scarce_min_allocation_multiplier', 'scarce_max_allocation_multiplier']
            for param in required_scarce_params:
                if param not in params:
                    errors.append(f"enforce_scarce_distribution이 True일 때 {param} 파라미터가 필요합니다.")
        
        if 'apply_store_size_constraints' in params and params['apply_store_size_constraints']:
            # 매장 크기별 차등 제약 활성화 시 관련 파라미터들 확인
            required_store_params = ['large_store_max_multiplier', 'small_store_max_multiplier']
            for param in required_store_params:
                if param not in params:
                    errors.append(f"apply_store_size_constraints가 True일 때 {param} 파라미터가 필요합니다.")
        
        # 승수 값의 합리성 확인 (수렴성 디버깅을 위해 완화)
        multiplier_params = [
            'min_allocation_multiplier', 'max_allocation_multiplier',
            'scarce_min_allocation_multiplier', 'scarce_max_allocation_multiplier',
            'large_store_max_multiplier', 'small_store_max_multiplier'
        ]
        for param in multiplier_params:
            if param in params:
                if params[param] <= 0:
                    errors.append(f"파라미터 {param}는 양수여야 합니다.")
                elif params[param] > 10000:  # 10 → 10000 (극단적인 디버깅 값까지 허용)
                    errors.append(f"파라미터 {param}가 너무 큽니다 (10000 이하 권장).")
                elif params[param] > 100:
                    # 경고만 로그로 출력하고 에러는 발생시키지 않음
                    pass  # 큰 값에 대해서는 경고만
        
        # 정수 파라미터 확인
        integer_params = ['min_allocation_per_store', 'min_stores_per_sku']
        for param in integer_params:
            if param in params and not isinstance(params[param], int):
                errors.append(f"파라미터 {param}는 정수여야 합니다.")
            elif param in params and params[param] < 0:
                errors.append(f"파라미터 {param}는 0 이상의 정수여야 합니다.")
        
        return errors
    
    def load_config(self, config_file: str):
        """
        설정 파일에서 시나리오 로드
        
        Args:
            config_file: 설정 파일 경로 (YAML 또는 JSON)
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    config = yaml.safe_load(f)
                elif config_file.endswith('.json'):
                    config = json.load(f)
                else:
                    raise ValueError("지원하지 않는 파일 형식입니다. YAML 또는 JSON 파일을 사용하세요.")
            
            if 'scenarios' in config:
                # 기존 시나리오와 병합
                self.scenarios.update(config['scenarios'])
            
            if 'evaluation_metrics' in config:
                self.evaluation_metrics.update(config['evaluation_metrics'])
                
        except Exception as e:
            raise ValueError(f"설정 파일 로드 실패: {e}")
    
    def save_config(self, config_file: str):
        """
        현재 설정을 파일로 저장
        
        Args:
            config_file: 저장할 파일 경로
        """
        config = {
            'scenarios': self.scenarios,
            'evaluation_metrics': self.evaluation_metrics,
            'experiment_plan': self.experiment_plan
        }
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    yaml.dump(config, f, default_flow_style=False, 
                             allow_unicode=True, sort_keys=False)
                elif config_file.endswith('.json'):
                    json.dump(config, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError("지원하지 않는 파일 형식입니다. YAML 또는 JSON 파일을 사용하세요.")
                    
        except Exception as e:
            raise ValueError(f"설정 파일 저장 실패: {e}")
    
    def print_scenario_summary(self, scenario_name: str = None):
        """
        시나리오 요약 정보 출력
        
        Args:
            scenario_name: 출력할 시나리오 이름 (None이면 전체)
        """
        if scenario_name:
            if scenario_name not in self.scenarios:
                print(f"시나리오 '{scenario_name}'을 찾을 수 없습니다.")
                return
            
            scenarios_to_print = {scenario_name: self.scenarios[scenario_name]}
        else:
            scenarios_to_print = self.scenarios
        
        print("=" * 80)
        print("🎯 실험 시나리오 요약")
        print("=" * 80)
        
        for name, params in scenarios_to_print.items():
            print(f"\n📌 {name}:")
            print(f"   설명: {params.get('description', 'N/A')}")
            print(f"   커버리지 가중치: {params.get('coverage_weight', 0)}")
            print(f"   균형 페널티: {params.get('balance_penalty', 0)}")
            print(f"   배분 페널티: {params.get('allocation_penalty', 0)}")
            print(f"   배분 범위: {params.get('allocation_range_min', 0)*100:.0f}% ~ "
                  f"{params.get('allocation_range_max', 0)*100:.0f}%")
            print(f"   최소 커버리지: {params.get('min_coverage_threshold', 0)*100:.0f}%")
    
    def get_scenario_list(self) -> List[str]:
        """사용 가능한 시나리오 이름 리스트 반환"""
        return list(self.scenarios.keys()) 