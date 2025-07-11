# SKU Distribution Optimization Project

## 🎯 프로젝트 개요

이 프로젝트는 **SKU 분배 최적화 문제**를 해결하기 위한 AI 기반 최적화 솔루션입니다. 여러 SKU(Stock Keeping Unit)를 다양한 매장에 효율적으로 분배하면서 색상 및 사이즈 비율 제약조건을 만족하는 최적의 분배 전략을 찾습니다.

## 🚀 주요 기능

- **최적화 알고리즘**: PuLP(CBC 솔버)를 사용한 선형 최적화
- **제약조건 처리**: 색상/사이즈 비율, 재고량, 매장 용량 제약
- **휴리스틱 비교**: 최적해와 휴리스틱 해법 비교 분석
- **상세 분석**: 분배 결과의 다양한 통계 및 시각화

## 📁 파일 구조

```
dist_ai/
├── data/                              # 데이터 파일들
│   ├── demand.csv                     # 매장별 SKU 수요량
│   ├── sku.csv                        # SKU 정보 (색상, 사이즈, 재고)
│   ├── store.csv                      # 매장 정보 (용량)
│   ├── optimal_result.csv             # 최적화 결과
│   └── heuristic_*.csv               # 휴리스틱 분석 결과들
├── sku_distribution_optimizer.py      # 기본 최적화 솔버
├── sku_distribution_optimizer_premium.py  # 고급 최적화 솔버
├── sku_distribution_optimizer_with_ratios.py  # 비율 제약 최적화
├── dist.ipynb                         # Jupyter 노트북 (분석 및 시각화)
└── README.md                          # 프로젝트 설명서
```

## 🛠️ 사용 기술

- **Python 3.8+**
- **PuLP**: 선형 최적화 라이브러리
- **Pandas**: 데이터 처리 및 분석
- **NumPy**: 수치 계산
- **CBC Solver**: 최적화 엔진

## 📊 문제 정의

### 목적함수
총 분배량 최대화

### 제약조건
1. **재고 제약**: 각 SKU의 분배량 ≤ 재고량
2. **용량 제약**: 각 매장의 총 분배량 ≤ 매장 용량
3. **색상 비율 제약**: 특정 색상(빨강, 파랑 등) 비율 유지
4. **사이즈 비율 제약**: 특정 사이즈(XL, XXL 등) 비율 유지

## 🎮 사용 방법

### 1. 환경 설정
```bash
pip install pulp pandas numpy psutil
```

### 2. 기본 최적화 실행
```bash
python sku_distribution_optimizer.py
```

### 3. 고급 최적화 실행
```bash
python sku_distribution_optimizer_premium.py
```

### 4. 비율 제약 최적화 실행
```bash
python sku_distribution_optimizer_with_ratios.py
```

### 5. Jupyter 노트북 실행
```bash
jupyter notebook dist.ipynb
```

## 📈 결과 분석

프로젝트는 다음과 같은 분석 결과를 제공합니다:

- **최적화 성과**: 목적함수 값, 해결 시간, 메모리 사용량
- **분배 현황**: SKU별, 매장별 분배량 통계
- **제약조건 준수**: 색상/사이즈 비율 준수율
- **휴리스틱 비교**: 최적해 vs 휴리스틱 해법 성능 비교

## 🔧 주요 매개변수

- `num_skus`: SKU 개수 (기본값: 20)
- `num_stores`: 매장 개수 (기본값: 80)
- `r_color_min/max`: 색상 비율 범위
- `r_size_min/max`: 사이즈 비율 범위
- `time_limit`: 최적화 시간 제한 (초)
- `threads`: 병렬 처리 스레드 수

## 📊 성능 최적화

- **멀티스레딩**: 시스템 코어 수에 따른 자동 스레드 조정
- **메모리 관리**: 대용량 데이터 처리를 위한 메모리 최적화
- **점진적 타임아웃**: 해결 시간에 따른 동적 시간 조정

## 🤝 기여하기

1. 이 레포지토리를 Fork하세요
2. 새로운 기능 브랜치를 생성하세요 (`git checkout -b feature/new-feature`)
3. 변경사항을 커밋하세요 (`git commit -am 'Add new feature'`)
4. 브랜치에 푸시하세요 (`git push origin feature/new-feature`)
5. Pull Request를 생성하세요

## 📝 라이센스

이 프로젝트는 MIT 라이센스 하에 제공됩니다.

## 👨‍💻 작성자

**Hyub** - [GitHub](https://github.com/Hyubbbb)

---

⭐ 이 프로젝트가 유용하다면 별표를 눌러주세요! 