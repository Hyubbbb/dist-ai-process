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

# 실험 시나리오 설정
EXPERIMENT_SCENARIOS = {
    "baseline": {
        "description": "기본 시나리오: 낮은 커버리지 가중치로 기본적인 배분",
        "coverage_weight": 0.1
    },
    "coverage_focused": {
        "description": "커버리지 중심: 매장별 상품 다양성 극대화 (순수 커버리지)",
        "coverage_weight": 2.0
    },
    "balance_focused": {
        "description": "중간 커버리지: 적절한 다양성 확보",
        "coverage_weight": 1.0
    },
    "hybrid": {
        "description": "하이브리드: 적절한 커버리지 확보 (권장)",
        "coverage_weight": 1.5
    },
    "extreme_coverage": {
        "description": "극단적 커버리지: 최대한 다양성 우선 (순수 커버리지만)",
        "coverage_weight": 5.0
    }
}

# 기본 실행 설정
DEFAULT_TARGET_STYLE = "DWLG42044"
DEFAULT_SCENARIO = "extreme_coverage"