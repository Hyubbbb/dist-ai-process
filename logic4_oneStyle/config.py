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
        "description": "기본 시나리오: 수요 기반 분배, 최소한의 커버리지/균형 제약",
        "coverage_weight": 0.1,
        "balance_penalty": 0.01,
        "allocation_penalty": 0.01
    },
    "coverage_focused": {
        "description": "커버리지 중심: 매장별 상품 다양성 극대화",
        "coverage_weight": 2.0,
        "balance_penalty": 0.05,
        "allocation_penalty": 0.01
    },
    "balance_focused": {
        "description": "균형 중심: 색상-사이즈 균형 및 매장별 공평 분배",
        "coverage_weight": 0.5,
        "balance_penalty": 1.0,
        "allocation_penalty": 0.5
    },
    "hybrid": {
        "description": "하이브리드: 커버리지와 균형의 적절한 조합",
        "coverage_weight": 1.0,
        "balance_penalty": 0.3,
        "allocation_penalty": 0.2
    },
    "extreme_coverage": {
        "description": "극단적 커버리지: 최대한 많은 다양성 확보",
        "coverage_weight": 5.0,
        "balance_penalty": 0.1,
        "allocation_penalty": 0.05
    }
}

# 기본 실행 설정
DEFAULT_TARGET_STYLE = "DWLG42044"
DEFAULT_SCENARIO = "extreme_coverage"