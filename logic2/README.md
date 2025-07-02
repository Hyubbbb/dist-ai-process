# SKU Distribution Optimization System

## 📋 개요

이 시스템은 소매 매장에 대한 SKU(Stock Keeping Unit) 분배를 최적화하는 2단계 접근 방식을 구현합니다:

1. **Step 1: Coverage MILP** - 희소 SKU의 커버리지 최적화
2. **Step 2: Quantity ILP** - 전체 SKU 수량 최적화

## 🏗️ 시스템 구조

```
logic2/
├── modules/
│   ├── __init__.py                 # 모듈 패키지 초기화
│   ├── data_loader.py             # 데이터 로딩 및 전처리
│   ├── experiment_config.py       # 실험 시나리오 설정
│   ├── file_manager.py            # 실험 결과 저장 관리
│   ├── optimizer.py               # SKU 최적화 엔진
│   ├── analyzer.py                # 결과 분석 (구현 예정)
│   ├── visualizer.py              # 시각화 (구현 예정)
│   └── experiment_runner.py       # 실험 실행 관리 (구현 예정)
├── main.py                        # 메인 실행 스크립트
├── config.yaml                    # 설정 파일
├── requirements.txt               # 의존성 패키지
└── README.md                      # 이 파일
```

## 📦 설치

### 1. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 주요 의존성
- pandas
- numpy
- pulp (선형 프로그래밍)
- matplotlib
- seaborn
- pyyaml
- openpyxl

## 🚀 사용법

### 기본 실행

```bash
# 단일 실험 실행
python main.py --sku_file ../data_real/발주수량.csv --store_file ../data_real/매장데이터.csv --scenario baseline

# 설정 파일 사용
python main.py --sku_file ../data_real/발주수량.csv --store_file ../data_real/매장데이터.csv --config config.yaml --scenario hybrid
```

### 배치 실험 실행

```bash
# 모든 시나리오 실행
python main.py --sku_file ../data_real/발주수량.csv --store_file ../data_real/매장데이터.csv --mode batch

# 특정 시나리오들만 실행
python main.py --sku_file ../data_real/발주수량.csv --store_file ../data_real/매장데이터.csv --mode batch --scenarios baseline hybrid coverage_focused
```

### 민감도 분석

```bash
# 하이브리드 시나리오 기준 민감도 분석
python main.py --sku_file ../data_real/발주수량.csv --store_file ../data_real/매장데이터.csv --mode sensitivity --scenario hybrid
```

### 실험 결과 비교

```bash
# 특정 실험들 비교
python main.py --mode compare --compare_experiments baseline_20241220_143052 hybrid_20241220_143127
```

## ⚙️ 실험 시나리오

### 기본 제공 시나리오

| 시나리오 | 설명 | 커버리지 가중치 | 균형 페널티 | 배분 페널티 | 비례 배분 범위 |
|----------|------|----------------|------------|------------|----------------|
| `baseline` | 기본 수요 기반 분배 | 0.0 | 0.0 | 0.0 | 0.5x ~ 1.5x |
| `coverage_focused` | 커버리지 최우선 | 1.0 | 0.0 | 0.0 | 0.3x ~ 2.0x |
| `balance_focused` | 균형 최우선 | 0.1 | 1.0 | 2.0 | 0.8x ~ 1.2x |
| `hybrid` | 균형잡힌 접근 | 0.5 | 0.3 | 0.1 | 0.6x ~ 1.4x |
| `extreme_coverage` | 극단적 커버리지 | 5.0 | 1.0 | 0.1 | 0.1x ~ 3.0x |
| `practical` | 실용적 비즈니스 | 0.8 | 0.5 | 0.3 | 0.7x ~ 1.3x |
| `distribution_focused` | SKU 분산 중심 | 0.3 | 0.5 | 0.2 | 0.8x ~ 1.2x |
| `proportional_focused` | QTY_SUM 비례 중심 | 0.4 | 0.2 | 0.1 | 0.9x ~ 1.1x |
| `max_dispersion` | 최대 분산 추구 | 0.2 | 0.8 | 0.5 | 0.95x ~ 1.05x |

### 커스텀 시나리오 생성

`config.yaml` 파일에서 새로운 시나리오를 추가할 수 있습니다:

```yaml
scenarios:
  my_custom_scenario:
    description: "나만의 커스텀 시나리오"
    coverage_weight: 1.5
    balance_penalty: 0.8
    allocation_penalty: 0.2
    allocation_range_min: 0.6
    allocation_range_max: 1.8
    min_coverage_threshold: 0.15
    
    # QTY_SUM 기반 비례 배분 파라미터
    use_proportional_allocation: true
    min_allocation_multiplier: 0.6
    max_allocation_multiplier: 1.4
    
    # 희소 SKU 특별 제약
    enforce_scarce_distribution: true
    scarce_min_allocation_multiplier: 0.4
    scarce_max_allocation_multiplier: 1.3
    
    # 매장 크기별 차등 제약
    apply_store_size_constraints: true
    large_store_max_multiplier: 1.8
    small_store_max_multiplier: 1.2
```

## 📊 출력 결과

각 실험은 고유한 타임스탬프가 포함된 폴더에 저장됩니다:

```
output/
└── {scenario}_{YYYYMMDD_HHMMSS}/
    ├── {scenario}_{timestamp}_allocation_results.csv      # 할당 결과
    ├── {scenario}_{timestamp}_store_summary.csv           # 매장별 요약
    ├── {scenario}_{timestamp}_style_analysis.csv          # 스타일 분석
    ├── {scenario}_{timestamp}_top_performers.csv          # 최고 성과 매장
    ├── {scenario}_{timestamp}_scarce_effectiveness.csv    # 희소 SKU 효과
    ├── {scenario}_{timestamp}_experiment_params.json      # 실험 파라미터
    └── {scenario}_{timestamp}_experiment_summary.txt      # 실험 요약
```

## 🔧 고급 사용법

### 로깅 레벨 설정

```bash
python main.py --log_level DEBUG --sku_file ... --store_file ...
```

### 출력 디렉토리 변경

```bash
python main.py --output_dir /my/custom/output --sku_file ... --store_file ...
```

### 타임아웃 설정

`config.yaml`에서 최적화 타임아웃을 조정할 수 있습니다:

```yaml
optimization:
  step1_timeout: 60   # Step1 타임아웃 (초)
  step2_timeout: 300  # Step2 타임아웃 (초)
```

## 📈 성과 메트릭

시스템은 다음과 같은 메트릭을 계산합니다:

### 커버리지 메트릭
- 평균 색상 커버리지 비율
- 평균 사이즈 커버리지 비율
- 커버리지 0인 매장 수
- 완전 커버리지(100%) 매장 수

### 균형 메트릭
- 색상-사이즈 커버리지 불균형 평균
- 매장별 배분량 표준편차
- 매장별 배분 비율 상관계수
- Gini 계수 (분배 불평등)

### 비즈니스 메트릭
- 총 할당 효율성
- 희소 SKU 활용률
- 매장별 상품 다양성 지수
- 예상 고객 만족도 점수

## 🔧 문제 해결

### 일반적인 오류

1. **메모리 부족 오류**
   - 매장 수나 SKU 수가 많을 때 발생 가능
   - 배치 크기를 줄이거나 더 많은 메모리가 있는 환경에서 실행

2. **최적화 실패**
   - 제약조건이 너무 엄격할 때 발생
   - `allocation_range_min/max` 값을 조정하여 해결

3. **파일 경로 오류**
   - 상대 경로를 절대 경로로 변경
   - 파일 존재 여부 확인

### 로그 파일 확인

실행 중 발생하는 모든 로그는 `optimization.log` 파일에 저장됩니다.

## 📝 라이센스

이 프로젝트는 MIT 라이센스를 따릅니다.

## 🤝 기여

버그 리포트나 기능 개선 제안은 언제든지 환영합니다!

## 📧 연락처

질문이나 지원이 필요한 경우 개발팀에 문의하세요.

## 🎯 QTY_SUM 기반 비례 배분 시스템

시스템의 핵심 혁신은 **매장별 QTY_SUM(판매량)을 기반으로 한 비례 배분 제약**입니다:

### 핵심 아이디어

1. **매장별 비율 계산**
   ```python
   store_ratio[j] = QTY_SUM[j] / sum(QTY_SUM.values())
   ```

2. **SKU별 기대 배분량 계산**
   ```python
   expected_allocation[i][j] = A[i] * store_ratio[j]
   ```

3. **비례 배분 범위 제약**
   ```python
   min_multiplier * expected ≤ x[i][j] ≤ max_multiplier * expected
   ```

### 비례 배분의 장점

| 구분 | 기존 MAX_SKU_CONCENTRATION | QTY_SUM 기반 비례 배분 |
|------|---------------------------|----------------------|
| **현실성** | 매장 크기 무시 | 매장 크기 직접 반영 |
| **공정성** | 절대적 제한 | 상대적 비례 제한 |
| **유연성** | 고정된 집중도 제한 | 승수 기반 동적 제한 |
| **해석성** | 직관적이지만 단순 | 명확한 비즈니스 의미 |

### 비례 배분 파라미터

| 파라미터 | 설명 | 기본값 | 범위 |
|----------|------|--------|------|
| `use_proportional_allocation` | 비례 배분 활성화 | true | true/false |
| `min_allocation_multiplier` | 최소 배분 승수 | 0.5 | 0.0+ |
| `max_allocation_multiplier` | 최대 배분 승수 | 1.5 | 0.0+ |
| `enforce_scarce_distribution` | 희소 SKU 특별 제약 | true | true/false |
| `scarce_min_allocation_multiplier` | 희소 SKU 최소 승수 | 0.3 | 0.0+ |
| `scarce_max_allocation_multiplier` | 희소 SKU 최대 승수 | 1.2 | 0.0+ |
| `apply_store_size_constraints` | 매장 크기별 차등 제약 | false | true/false |
| `large_store_max_multiplier` | 큰 매장 최대 승수 | 2.0 | 0.0+ |
| `small_store_max_multiplier` | 작은 매장 최대 승수 | 1.2 | 0.0+ |

### 3층 제약 구조

**1단계: 기본 비례 배분 제약**
- 모든 SKU에 대해 QTY_SUM 비례 범위 내 배분 보장

**2단계: 희소 SKU 특별 제약 (선택적)**
- 희소 SKU에 대해 더 엄격한 분산 제약 적용

**3단계: 매장 크기별 차등 제약 (선택적)**
- 큰 매장은 더 많은 변동 허용
- 작은 매장은 더 제한적 배분

### 실용적 예시

**매장 A (QTY_SUM: 1000, 비율: 10%)**
**매장 B (QTY_SUM: 500, 비율: 5%)**
**SKU_X (총량: 100개)**

```python
# 기대 배분량
매장A_기대량 = 100 * 0.10 = 10개
매장B_기대량 = 100 * 0.05 = 5개

# 0.8x ~ 1.2x 범위 제약 시
매장A_범위 = 8 ~ 12개
매장B_범위 = 4 ~ 6개
```

### 비례 배분 분석 메트릭

시스템은 비례 배분 품질을 측정하는 메트릭을 제공합니다:

- **비례성 준수율**: 기대값 범위 내 배분 비율
- **매장별 편차**: 기대값 대비 실제 배분 편차
- **비례 균형 점수**: 전체적인 비례 배분 품질
- **크기별 공정성**: 매장 크기에 따른 배분 공정성
- **희소 SKU 분산 효과**: 희소 상품의 분산 배분 효과 