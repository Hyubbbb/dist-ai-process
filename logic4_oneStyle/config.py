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

# 배분 우선순위 옵션 설정 (3개만 유지)
ALLOCATION_PRIORITY_OPTIONS = {
    "sequential": {
        "name": "상위 매장 순차적 배분",
        "description": "QTY_SUM 높은 매장부터 순차적으로 우선 배분",
        "weight_function": "linear_descending",  # 상위 매장일수록 높은 가중치
        "randomness": 0.0  # 랜덤성 0%
    },
    "random": {
        "name": "완전 랜덤 배분",
        "description": "모든 매장에 동일한 확률로 랜덤 배분",
        "weight_function": "uniform",  # 모든 매장 동일 가중치
        "randomness": 1.0  # 랜덤성 100%
    },
    "balanced": {
        "name": "균형 배분",
        "description": "상위 매장 우선하되 중간 매장도 기회 제공",
        "weight_function": "log_descending",  # 로그 스케일 가중치
        "randomness": 0.3  # 랜덤성 30%
    }
}

# 실험 시나리오 설정 (단순화)
EXPERIMENT_SCENARIOS = {
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
    }
}

# 기본 실행 설정
DEFAULT_TARGET_STYLE = "DWLG42044"
DEFAULT_SCENARIO = "baseline"