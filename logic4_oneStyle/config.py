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

# # 배분 우선순위 옵션 설정 (6개로 확장: 기존 3개 + 개선된 3개)
# ALLOCATION_PRIORITY_OPTIONS = {
#     # 기존 방식 (현재 로직 유지)
#     "sequential": {
#         "name": "상위 매장 순차적 배분",
#         "description": "QTY_SUM 높은 매장부터 순차적으로 우선 배분",
#         "weight_function": "linear_descending",  # 상위 매장일수록 높은 가중치
#         "randomness": 0.0,  # 랜덤성 0%
#         "priority_unfilled": False  # 기존 방식
#     },
#     "random": {
#         "name": "완전 랜덤 배분",
#         "description": "모든 매장에 동일한 확률로 랜덤 배분",
#         "weight_function": "uniform",  # 모든 매장 동일 가중치
#         "randomness": 1.0,  # 랜덤성 100%
#         "priority_unfilled": False  # 기존 방식
#     },
#     "balanced": {
#         "name": "균형 배분",
#         "description": "상위 매장 우선하되 중간 매장도 기회 제공",
#         "weight_function": "log_descending",  # 로그 스케일 가중치
#         "randomness": 0.3,  # 랜덤성 30%
#         "priority_unfilled": False  # 기존 방식
#     },
    
#     # 개선된 방식 (미배분 매장 우선)
#     "sequential_unfilled": {
#         "name": "미배분 매장 우선 + 순차적 배분",
#         "description": "아직 받지 못한 매장 우선, 그 다음 상위 매장부터 순차적",
#         "weight_function": "linear_descending",
#         "randomness": 0.0,
#         "priority_unfilled": True  # 미배분 매장 우선
#     },
#     "random_unfilled": {
#         "name": "미배분 매장 우선 + 랜덤 배분",
#         "description": "아직 받지 못한 매장 우선, 그 다음 랜덤 배분",
#         "weight_function": "uniform",
#         "randomness": 1.0,
#         "priority_unfilled": True  # 미배분 매장 우선
#     },
#     "balanced_unfilled": {
#         "name": "미배분 매장 우선 + 균형 배분",
#         "description": "아직 받지 못한 매장 우선, 그 다음 균형 배분",
#         "weight_function": "log_descending",
#         "randomness": 0.3,
#         "priority_unfilled": True  # 미배분 매장 우선
#     }
# }

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
DEFAULT_SCENARIO = "deterministic"

# 실험 시나리오 설정 (고급 방식 관련 시나리오 제거)
EXPERIMENT_SCENARIOS = {    
    # 추가 3-Step 시나리오들 (정규화 방식 적용)
    "deterministic": {
        "description": "결정론적 배분",
        "coverage_weight": 1.0,
        "priority_temperature": 0.0,
        "coverage_method": "normalized"
    },
    
    "temperature_0.5": {
        "description": "temperature 0.5",
        "coverage_weight": 1.0,
        "priority_temperature": 0.5,
        "coverage_method": "normalized"
    },
    
    "random": {
        "description": "랜덤 배분",
        "coverage_weight": 1.0,
        "priority_temperature": 1.0,
        "coverage_method": "normalized"
    },
    
    # coverage_method 비교 시나리오
    "original_coverage": {
        "description": "기존 커버리지 방식 테스트 (색상 + 사이즈 커버리지 단순 합산)",
        "coverage_weight": 1.0,
        "priority_temperature": 0.0,
        "coverage_method": "original"
    },
    
    "normalized_coverage": {
        "description": "정규화 커버리지 방식 테스트 (스타일별 색상/사이즈 개수 반영)",
        "coverage_weight": 1.0,
        "priority_temperature": 0.0,
        "coverage_method": "normalized"
    }
}