"""
SKU 분배 최적화 설정
"""

# 기본 경로 설정
DATA_PATH = '../data_real'
OUTPUT_PATH = './output'

# 매장 Tier 설정
TIER_CONFIG = {
    'TIER_1_HIGH': {
        'name': 'TIER_1_HIGH',
        'display': '🥇 T1 (HIGH)',
        'ratio': 0.3,
        'max_sku_limit': 3
    },
    'TIER_2_MEDIUM': {
        'name': 'TIER_2_MEDIUM', 
        'display': '🥈 T2 (MED)',
        'ratio': 0.2,
        'max_sku_limit': 2
    },
    'TIER_3_LOW': {
        'name': 'TIER_3_LOW',
        'display': '🥉 T3 (LOW)', 
        'ratio': 0.5,
        'max_sku_limit': 1
    }
}

# 배분 우선순위 옵션 설정 (6개로 확장: 기존 3개 + 개선된 3개)
ALLOCATION_PRIORITY_OPTIONS = {
    # 기존 방식 (현재 로직 유지)
    "sequential": {
        "name": "상위 매장 순차적 배분",
        "description": "QTY_SUM 높은 매장부터 순차적으로 우선 배분",
        "weight_function": "linear_descending",  # 상위 매장일수록 높은 가중치
        "randomness": 0.0,  # 랜덤성 0%
        "priority_unfilled": False  # 기존 방식
    },
    "random": {
        "name": "완전 랜덤 배분",
        "description": "모든 매장에 동일한 확률로 랜덤 배분",
        "weight_function": "uniform",  # 모든 매장 동일 가중치
        "randomness": 1.0,  # 랜덤성 100%
        "priority_unfilled": False  # 기존 방식
    },
    "balanced": {
        "name": "균형 배분",
        "description": "상위 매장 우선하되 중간 매장도 기회 제공",
        "weight_function": "log_descending",  # 로그 스케일 가중치
        "randomness": 0.3,  # 랜덤성 30%
        "priority_unfilled": False  # 기존 방식
    },
    
    # 개선된 방식 (미배분 매장 우선)
    "sequential_unfilled": {
        "name": "미배분 매장 우선 + 순차적 배분",
        "description": "아직 받지 못한 매장 우선, 그 다음 상위 매장부터 순차적",
        "weight_function": "linear_descending",
        "randomness": 0.0,
        "priority_unfilled": True  # 미배분 매장 우선
    },
    "random_unfilled": {
        "name": "미배분 매장 우선 + 랜덤 배분",
        "description": "아직 받지 못한 매장 우선, 그 다음 랜덤 배분",
        "weight_function": "uniform",
        "randomness": 1.0,
        "priority_unfilled": True  # 미배분 매장 우선
    },
    "balanced_unfilled": {
        "name": "미배분 매장 우선 + 균형 배분",
        "description": "아직 받지 못한 매장 우선, 그 다음 균형 배분",
        "weight_function": "log_descending",
        "randomness": 0.3,
        "priority_unfilled": True  # 미배분 매장 우선
    }
}

# 커버리지 최적화 방식 설정 (매장 가중치 방식 제거, 정규화 방식만 유지)
COVERAGE_OPTIMIZATION_METHODS = {
    "original": {
        "name": "원래 방식",
        "description": "색상 + 사이즈 커버리지 단순 합산 (불균등 가중치)",
        "function": "_set_coverage_objective_original",
        "pros": "기존 방식과 동일, 빠른 계산",
        "cons": "사이즈 커버리지가 색상보다 중요하게 계산됨 (스타일별 색상/사이즈 개수 차이 미반영)"
    },
    "normalized": {
        "name": "정규화 방식",
        "description": "스타일별 색상/사이즈 개수를 고려한 정규화된 커버리지 계산",
        "function": "_set_coverage_objective",
        "pros": "스타일별 색상/사이즈 개수 반영, 색상과 사이즈 균등한 중요도, 공정한 평가",
        "cons": "기존 결과와 다를 수 있음"
    }
}

# 기본 커버리지 최적화 방식 (정규화 방식으로 설정)
DEFAULT_COVERAGE_METHOD = "normalized"

# 기본 실행 설정
DEFAULT_TARGET_STYLE = "DWLG42044"
DEFAULT_SCENARIO = "baseline"

# 실험 시나리오 설정 (고급 방식 관련 시나리오 제거)
EXPERIMENT_SCENARIOS = {
    # 기존 시나리오들 (현재 방식)
    "baseline": {
        "description": "기본 시나리오: 상위 매장 순차적 배분",
        "coverage_weight": 1.0,
        "allocation_priority": "sequential"
    },
    "balanced": {
        "description": "균형 시나리오: 상위 매장 우선하되 중간 매장도 기회 제공",
        "coverage_weight": 1.0,
        "allocation_priority": "balanced"
    },
    "random": {
        "description": "랜덤 시나리오: 모든 매장에 동일한 확률로 배분",
        "coverage_weight": 1.0,
        "allocation_priority": "random"
    },
    "high_coverage": {
        "description": "고커버리지 시나리오: 커버리지 우선 + 상위 매장 순차적",
        "coverage_weight": 5.0,
        "allocation_priority": "sequential"
    },
    "high_coverage_balanced": {
        "description": "고커버리지 균형 시나리오: 커버리지 우선 + 균형 배분",
        "coverage_weight": 5.0,
        "allocation_priority": "balanced"
    },
    
    # 새로운 시나리오들 (미배분 매장 우선)
    "fair_sequential": {
        "description": "공평한 순차적 배분: 미배분 매장 우선 + 순차적",
        "coverage_weight": 1.0,
        "allocation_priority": "sequential_unfilled"
    },
    "fair_balanced": {
        "description": "공평한 균형 배분: 미배분 매장 우선 + 균형 배분",
        "coverage_weight": 1.0,
        "allocation_priority": "balanced_unfilled"
    },
    "fair_random": {
        "description": "공평한 랜덤 배분: 미배분 매장 우선 + 랜덤",
        "coverage_weight": 1.0,
        "allocation_priority": "random_unfilled"
    },
    "high_coverage_fair": {
        "description": "고커버리지 + 공평한 순차적: 커버리지 우선 + 미배분 매장 우선",
        "coverage_weight": 5.0,
        "allocation_priority": "sequential_unfilled"
    },
    "my_custom": {
        "description": "커스텀 3-Step 시나리오: 정규화된 커버리지 + 균형 배분",
        "coverage_weight": 1.0,
        "allocation_priority_step2": "random_unfilled",
        "allocation_priority_step3": "sequential",
        "allocation_priority": "balanced",  # 백업용
        "coverage_method": "normalized"  # 정규화된 커버리지 방식 사용
    },
    
    # 추가 3-Step 시나리오들 (정규화 방식 적용)
    "three_step_fair": {
        "description": "공평한 3-Step: Step2/3 모두 미배분 매장 우선",
        "coverage_weight": 1.0,
        "allocation_priority_step2": "balanced_unfilled",
        "allocation_priority_step3": "balanced_unfilled",
        "allocation_priority": "balanced_unfilled",
        "coverage_method": "normalized"
    },
    
    "three_step_performance": {
        "description": "성능 중심 3-Step: Step2는 순차적, Step3는 균형",
        "coverage_weight": 1.0,
        "allocation_priority_step2": "sequential",
        "allocation_priority_step3": "balanced",
        "allocation_priority": "balanced",
        "coverage_method": "normalized"  # 정규화 방식 사용
    },
    
    # 커버리지 방식 비교 시나리오들 (고급 방식 제거)
    "original_coverage": {
        "description": "원래 커버리지 방식 테스트",
        "coverage_weight": 1.0,
        "allocation_priority_step2": "balanced",
        "allocation_priority_step3": "balanced", 
        "allocation_priority": "balanced",
        "coverage_method": "original"
    },
    
    "normalized_coverage": {
        "description": "정규화 커버리지 방식 테스트 (스타일별 색상/사이즈 개수 반영)",
        "coverage_weight": 1.0,
        "allocation_priority_step2": "balanced",
        "allocation_priority_step3": "balanced",
        "allocation_priority": "balanced", 
        "coverage_method": "normalized"
    }
}