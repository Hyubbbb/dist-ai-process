# SKU 분배 최적화 시스템 (모듈화 버전)

단일 스타일 SKU의 매장별 최적 분배를 위한 2단계 최적화 시스템입니다.

## 📁 프로젝트 구조

```
logic3_oneStyle/
├── main.py                 # 메인 실행 파일
├── config.py               # 설정 파일
├── README.md              # 사용법 안내
└── modules/               # 모듈 패키지
    ├── __init__.py
    ├── data_loader.py      # 데이터 로드 및 전처리
    ├── store_tier_system.py # 매장 tier 관리
    ├── sku_classifier.py   # SKU 분류 (희소/충분)
    ├── coverage_optimizer.py # Step1: Coverage MILP
    ├── greedy_allocator.py # Step2: 결정론적 배분
    ├── analyzer.py         # 결과 분석
    ├── visualizer.py       # 시각화
    └── experiment_manager.py # 실험 관리
```

## 🚀 빠른 시작

### 1. 기본 실행

```python
python main.py
```

### 2. Python에서 직접 실행

```python
from main import run_optimization

# 기본 설정으로 실행
result = run_optimization()

# 특정 스타일과 시나리오로 실행
result = run_optimization(
    target_style='DWLG42044',
    scenario='extreme_coverage',
    show_detailed_output=True,
    create_visualizations=True
)
```

## ⚙️ 주요 기능

### 1. 2단계 최적화 알고리즘

- **Step1 (Coverage 최적화)**: MILP를 통한 희소 SKU 전략적 배치
- **Step2 (결정론적 배분)**: 그리디 알고리즘을 통한 추가 배분

### 2. 매장 Tier 시스템

- **Tier 1 (상위 30%)**: SKU당 최대 3개 배분
- **Tier 2 (다음 20%)**: SKU당 최대 2개 배분  
- **Tier 3 (나머지 50%)**: SKU당 최대 1개 배분

### 3. 실험 시나리오

| 시나리오 | 설명 | 특징 |
|---------|------|------|
| `baseline` | 기본 시나리오 | 수요 기반 분배, 최소 제약 |
| `coverage_focused` | 커버리지 중심 | 매장별 상품 다양성 극대화 |
| `balance_focused` | 균형 중심 | 색상-사이즈 균형 및 공평 분배 |
| `hybrid` | 하이브리드 | 커버리지와 균형의 조합 |
| `extreme_coverage` | 극단적 커버리지 | 최대한 많은 다양성 확보 |

## 📊 분석 메트릭

### 커버리지 메트릭
- **색상 커버리지**: 매장별 커버하는 색상 비율
- **사이즈 커버리지**: 매장별 커버하는 사이즈 비율

### 배분 효율성
- **배분 비율**: 총 배분량 / 총 공급량
- **배분 적정성**: 매장별 배분량 / QTY_SUM
- **배분 균형성**: 매장간 배분 편차

### 종합 평가
- **A급 (0.8+)**: 우수한 배분 결과
- **B급 (0.7-0.8)**: 양호한 배분 결과
- **C급 (0.6-0.7)**: 보통 수준
- **D급 (0.5-0.6)**: 개선 필요
- **F급 (0.5-)**: 재검토 필요

## 🔧 설정 변경

### config.py에서 수정 가능한 항목

```python
# 기본 스타일 및 시나리오
DEFAULT_TARGET_STYLE = "DWLG42044"
DEFAULT_SCENARIO = "extreme_coverage"

# 매장 Tier 비율 및 제한
TIER_CONFIG = {
    'TIER_1_HIGH': {'ratio': 0.3, 'max_sku_limit': 3},
    'TIER_2_MEDIUM': {'ratio': 0.2, 'max_sku_limit': 2},
    'TIER_3_LOW': {'ratio': 0.5, 'max_sku_limit': 1}
}
```

## 📈 배치 실험

### 여러 시나리오 동시 실행

```python
from main import run_batch_experiments

# 모든 시나리오로 실험
results = run_batch_experiments(
    target_styles=['DWLG42044'],
    scenarios=['baseline', 'extreme_coverage', 'hybrid']
)

# 여러 스타일로 실험
results = run_batch_experiments(
    target_styles=['DWLG42044', 'DMDJ85046'],
    scenarios=['extreme_coverage']
)
```

## 💾 결과 관리

### 자동 저장 파일들

- `allocation_results.csv`: 상세 할당 결과
- `store_summary.csv`: 매장별 성과 요약
- `style_analysis.csv`: 스타일별 커버리지 분석
- `top_performers.csv`: 최고 성과 매장
- `scarce_effectiveness.csv`: 희소 SKU 효과성
- `experiment_params.json`: 실험 파라미터
- `experiment_summary.txt`: 실험 요약

### 실험 목록 확인

```python
from main import list_saved_experiments

list_saved_experiments()
```

## 🎨 시각화

자동 생성되는 시각화:

1. **색상/사이즈 커버리지 비교**: 평균, 최대, 최소값
2. **매장별 배분 적정성 분포**: 히스토그램
3. **매장 규모 vs 할당량**: 산점도 및 상관관계
4. **성과 분석 히트맵**: 상위 매장 성과
5. **커버리지 vs 배분량**: 관계 분석
6. **통계 요약**: 종합 성과 지표

## 🛠️ 모듈별 사용법

### 개별 모듈 사용

```python
# 데이터 로드만
from modules import DataLoader
data_loader = DataLoader()
data_loader.load_data()
data_loader.filter_by_style('DWLG42044')

# SKU 분류만
from modules import SKUClassifier
classifier = SKUClassifier(data_loader.df_sku_filtered)
scarce, abundant = classifier.classify_skus(A, target_stores)

# 결과 분석만
from modules import ResultAnalyzer
analyzer = ResultAnalyzer('DWLG42044')
analysis = analyzer.analyze_results(...)
```

## 🔍 문제 해결

### 자주 발생하는 오류

1. **ModuleNotFoundError**: `sys.path.append()` 확인
2. **파일 경로 오류**: `config.py`의 경로 설정 확인
3. **메모리 부족**: 큰 데이터셋의 경우 배치 크기 조정
4. **MILP 최적화 실패**: 제약조건 완화 또는 데이터 확인

### 성능 최적화

- 시각화 비활성화: `create_visualizations=False`
- 상세 출력 비활성화: `show_detailed_output=False`
- 배치 실험에서 시각화 자동 비활성화

## 📋 요구사항

- Python 3.7+
- pandas
- numpy
- pulp (MILP 솔버)
- matplotlib
- seaborn

## 🤝 기여 방법

1. 새로운 시나리오 추가: `config.py`의 `EXPERIMENT_SCENARIOS`에 추가
2. 새로운 분석 메트릭: `analyzer.py`에 메서드 추가
3. 새로운 시각화: `visualizer.py`에 메서드 추가
4. 새로운 배분 알고리즘: `greedy_allocator.py` 수정

## 📞 지원

문제가 발생하거나 개선 제안이 있으시면 이슈를 등록해주세요.

---

**최적화 완료된 SKU 분배로 매장별 상품 다양성과 배분 효율성을 동시에 달성하세요! 🎯** 