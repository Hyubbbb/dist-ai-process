# Logic4_oneStyle: 통합 MILP SKU 분배 최적화

## 🚀 **주요 개선사항**

Logic3의 **Step1 (Coverage) + Step2 (Greedy)** 구조를 **통합 MILP** 하나로 통합하여 근본적인 최적성을 보장합니다.

### ⚡ **통합 MILP의 핵심 차이점**

| 구분 | Logic3 (기존) | Logic4 (통합 MILP) |
|------|---------------|-------------------|
| **알고리즘** | Step1 MILP + Step2 Greedy | **통합 MILP 하나** |
| **변수 타입** | 바이너리 (0/1) + 휴리스틱 | **정수 변수 (실제 수량)** |
| **최적성** | 국소 최적해 (Greedy 한계) | **수학적 전역 최적해** |
| **목적함수** | 커버리지 중심 | **커버리지 + Tier균형 + 수량효율성** |
| **커버리지** | Step2에서 고려 안됨 | **전 과정에서 동시 고려** |

## 🎯 **통합 목적함수**

```python
목적함수 = 커버리지_최대화 + 배분량_최대화 + Tier_균형_보너스 + 매장효율성_보너스 + 희소SKU_우선보너스
```

### 📊 **목적함수 구성요소:**

1. **🎨 커버리지 최대화** (가중치: scenario별 설정)
   - 색상 커버리지 + 사이즈 커버리지
   - 매장별 상품 다양성 극대화

2. **📦 배분량 최대화** (가중치: 0.1)
   - 공급량 활용도 극대화
   - 재고 효율성 향상

3. **⚖️ Tier 균형 최적화** (페널티: scenario별 설정)
   - Tier 내 매장별 배분량 편차 최소화
   - 공평한 분배 보장

4. **🏪 매장 효율성 보너스** (가중치: 0.05)
   - 매장 크기(QTY_SUM) 대비 적정 배분
   - 매장별 성과 최적화

5. **💎 희소 SKU 우선 보너스** (가중치: 0.2)
   - 희소 자원의 전략적 배치
   - 높은 부가가치 실현

## 🏗️ **모듈 구조**

```mermaid
graph TD
    A[main.py] --> B[IntegratedOptimizer]
    B --> C[통합 MILP 최적화]
    C --> D[ResultAnalyzer]
    D --> E[ResultVisualizer]
    E --> F[ExperimentManager]
    
    B --> G[변수 정의<br/>정수 변수 x[i][j]]
    B --> H[목적함수<br/>5개 구성요소 통합]
    B --> I[제약조건<br/>공급량+용량+커버리지+Tier균형]
```

## 📁 **주요 파일**

### 🆕 **새로 추가된 모듈**
- `modules/integrated_optimizer.py`: **통합 MILP 최적화 엔진**

### 🔧 **수정된 모듈**
- `main.py`: Step1+Step2 → IntegratedOptimizer로 워크플로우 단순화
- `modules/__init__.py`: IntegratedOptimizer 임포트 추가

### 🔄 **기존 모듈 (재사용)**
- `modules/data_loader.py`: 데이터 로딩 및 전처리
- `modules/store_tier_system.py`: 3-Tier 매장 관리
- `modules/sku_classifier.py`: 희소/충분 SKU 분류
- `modules/analyzer.py`: 결과 분석 및 평가
- `modules/visualizer.py`: 종합 시각화
- `modules/experiment_manager.py`: 실험 관리

## 🚀 **실행 방법**

### 1. **기본 실행**
```bash
python main.py
```

### 2. **Python에서 직접 실행**
```python
from main import run_optimization

# 통합 MILP로 최적화 실행
result = run_optimization(
    target_style="DWLG42044",
    scenario="extreme_coverage",
    create_visualizations=True
)
```

### 3. **배치 실험**
```python
from main import run_batch_experiments

# 여러 시나리오 동시 실행
results = run_batch_experiments(
    target_styles=["DWLG42044"],
    scenarios=["hybrid", "extreme_coverage"],
    create_visualizations=True
)
```

## 📊 **시나리오 설정**

`config.py`에서 통합 MILP의 목적함수 가중치를 조정할 수 있습니다:

```python
"extreme_coverage": {
    "coverage_weight": 5.0,      # 커버리지 극대화
    "balance_penalty": 0.1,      # Tier 균형 낮은 우선순위
    "allocation_penalty": 0.05,  # 배분 효율성
}

"balance_focused": {
    "coverage_weight": 0.5,      # 커버리지 중간 우선순위
    "balance_penalty": 1.0,      # Tier 균형 극대화
    "allocation_penalty": 0.5,   # 배분 효율성 향상
}
```

## ⚡ **성능 특성**

### 🔥 **장점**
- ✅ **수학적 최적해 보장** (국소 최적해 탈피)
- ✅ **커버리지 + Tier 균형 동시 고려**
- ✅ **일관된 최적화 기준**
- ✅ **시나리오별 유연한 가중치 조정**

### ⚠️ **고려사항**
- 📊 **계산 시간 증가** (5분 제한 설정)
- 🔧 **메모리 사용량 증가** (더 많은 변수/제약조건)
- 📈 **복잡도 증가** (하지만 더 나은 결과)

## 📈 **Logic3 vs Logic4 비교**

| 메트릭 | Logic3 | Logic4 (예상) |
|--------|--------|---------------|
| **Tier 균형성** | 낮음 | **높음** |
| **커버리지 일관성** | 중간 | **높음** |
| **전체 최적성** | 국소 최적 | **전역 최적** |
| **계산 시간** | 빠름 | 중간 |
| **결과 안정성** | 중간 | **높음** |

## 🎉 **기대 효과**

1. **🎯 더 균형잡힌 배분**: Tier 내 매장별 편차 최소화
2. **🎨 일관된 커버리지**: 전 과정에서 색상/사이즈 다양성 보장
3. **⚡ 수학적 최적성**: 휴리스틱 한계 극복
4. **📊 투명한 의사결정**: 명확한 목적함수 기반

---

## 🛠️ **요구사항**

```bash
pip install -r requirements.txt
```

### 주요 패키지:
- `pulp`: MILP 최적화
- `pandas`: 데이터 처리
- `matplotlib`: 시각화
- `numpy`: 수치 계산

---

**📝 개발자**: Claude Sonnet 4  
**📅 개발일**: 2025-07-02  
**🔖 버전**: Logic4 (통합 MILP) 