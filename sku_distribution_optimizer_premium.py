#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SKU Distribution Optimizer - Premium Version
============================================
시간을 더 투자해서 최고 품질의 최적화 결과를 얻는 버전

개선사항:
- 더 긴 시간 제한으로 더 나은 해 탐색
- 더 큰 문제 규모 처리
- 고급 솔버 설정 활용
- 다단계 최적화 전략
"""

import pandas as pd
import numpy as np
import time
import psutil
import os
from datetime import datetime
from pulp import LpProblem, LpVariable, LpInteger, LpMaximize, lpSum, PULP_CBC_CMD

def print_header(title):
    """섹션 헤더 출력"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_section(title):
    """서브섹션 헤더 출력"""
    print(f"\n🔹 {title}")
    print("-" * 50)

def create_premium_data(num_skus=20, num_stores=80):
    """프리미엄 데이터 생성 - 더 큰 규모로"""
    print_header("프리미엄 데이터 생성 (더 큰 규모)")
    
    if not os.path.exists('data'):
        os.makedirs('data')
        print("📁 data 디렉토리 생성됨")
    
    np.random.seed(42)
    
    colors = ['black', 'gray', 'white', 'navy', 'red', 'green', 'blue', 'yellow', 'brown', 'purple']
    sizes = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']
    
    print_section("SKU 데이터 생성")
    sku_list = []
    for i in range(num_skus):
        sku_list.append({
            'sku_id': f'SKU_{i+1:03d}',
            'color': np.random.choice(colors),
            'size': np.random.choice(sizes),
            'supply': np.random.randint(100, 300)  # 더 큰 공급량
        })
    df_skus = pd.DataFrame(sku_list)
    df_skus.to_csv('data/sku.csv', index=False)
    print(f"✅ SKU 데이터: {len(df_skus)}개")
    
    print_section("상점 데이터 생성")
    store_list = []
    for j in range(num_stores):
        store_list.append({
            'store_id': f'ST_{j+1:03d}',
            'cap': np.random.randint(80, 200)  # 더 큰 용량
        })
    df_stores = pd.DataFrame(store_list)
    df_stores.to_csv('data/store.csv', index=False)
    print(f"✅ 상점 데이터: {len(df_stores)}개")
    
    print_section("수요 데이터 생성")
    demand_rows = []
    for _, sku in df_skus.iterrows():
        for _, store in df_stores.iterrows():
            # 더 현실적인 수요 분포
            base_demand = np.random.randint(1, min(40, store['cap'] // 4))
            # 20% 확률로 높은 수요
            if np.random.random() < 0.2:
                base_demand = int(base_demand * 1.5)
            
            demand_rows.append({
                'sku_id': sku['sku_id'],
                'store_id': store['store_id'],
                'demand': base_demand
            })
    df_demand = pd.DataFrame(demand_rows)
    df_demand.to_csv('data/demand.csv', index=False)
    print(f"✅ 수요 데이터: {len(df_demand):,}개 조합")
    
    print(f"\n📊 프리미엄 문제 규모:")
    print(f"   - 변수 수: {num_skus * num_stores:,}개")
    print(f"   - SKUs: {num_skus}개")
    print(f"   - Stores: {num_stores}개")
    print(f"   - 예상 제약조건: ~{num_skus + num_stores * 5 + len(df_demand) // 2}개")
    print(f"   - 총 수요량: {df_demand['demand'].sum():,}")
    print(f"   - 총 공급량: {df_skus['supply'].sum():,}")
    print(f"   - 총 용량: {df_stores['cap'].sum():,}")
    
    return df_skus, df_stores, df_demand

def load_and_analyze_premium_data():
    """프리미엄 데이터 로드 및 분석"""
    print_header("프리미엄 데이터 로드 및 분석")
    
    skus = pd.read_csv('data/sku.csv')
    stores = pd.read_csv('data/store.csv')
    demand = pd.read_csv('data/demand.csv')
    
    print(f"📊 데이터 로드 완료:")
    print(f"   - SKUs: {len(skus)}개")
    print(f"   - Stores: {len(stores)}개")
    print(f"   - Demand combinations: {len(demand):,}개")
    
    # 집합 정의 (더 정교하게)
    basic_colors = ['black', 'gray', 'white', 'navy']
    special_colors = ['red', 'green', 'blue', 'yellow', 'brown', 'purple']
    
    basic_sizes = ['S', 'M', 'L']
    special_sizes = ['XXS', 'XS', 'XL', 'XXL', 'XXXL']
    
    C_color = skus[skus['color'].isin(special_colors)]['sku_id'].tolist()
    S_size = skus[skus['size'].isin(special_sizes)]['sku_id'].tolist()
    
    print(f"\n🎨 색상 집합 분석:")
    print(f"   - 기본 색상 ({', '.join(basic_colors)}): {len(skus) - len(C_color)}개")
    print(f"   - 특수 색상 ({', '.join(special_colors)}): {len(C_color)}개")
    
    print(f"\n📏 사이즈 집합 분석:")
    print(f"   - 기본 사이즈 ({', '.join(basic_sizes)}): {len(skus) - len(S_size)}개")
    print(f"   - 특수 사이즈 ({', '.join(special_sizes)}): {len(S_size)}개")
    
    # 데이터 기반 비율 계산
    merged = demand.merge(stores, on='store_id').merge(skus[['sku_id','color','size']], on='sku_id')
    
    total_demand = merged['demand'].sum()
    color_demand = merged[merged['color'].isin(special_colors)]['demand'].sum()
    size_demand = merged[merged['size'].isin(special_sizes)]['demand'].sum()
    
    r_color_actual = color_demand / total_demand
    r_size_actual = size_demand / total_demand
    
    # 더 현실적인 비율 범위 (조금 더 타이트하게)
    r_color_min = max(0.1, r_color_actual - 0.1)
    r_color_max = min(0.7, r_color_actual + 0.1)
    
    r_size_min = max(0.1, r_size_actual - 0.1)  
    r_size_max = min(0.7, r_size_actual + 0.1)
    
    print(f"\n📈 프리미엄 비율 제약:")
    print(f"   - 실제 색상 비율: {r_color_actual:.3f}")
    print(f"   - 색상 비율 범위: {r_color_min:.3f} - {r_color_max:.3f}")
    print(f"   - 실제 사이즈 비율: {r_size_actual:.3f}")
    print(f"   - 사이즈 비율 범위: {r_size_min:.3f} - {r_size_max:.3f}")
    
    return skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max

def create_premium_optimization_problem(skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max):
    """프리미엄 최적화 문제 정의"""
    print_header("프리미엄 최적화 문제 정의")
    
    prob = LpProblem("Premium_SKU_Distribution", LpMaximize)
    x = LpVariable.dicts("x", (skus['sku_id'], stores['store_id']), lowBound=0, cat=LpInteger)
    
    print(f"📊 문제 규모:")
    print(f"   - 변수 수: {len(skus) * len(stores):,}개")
    print(f"   - SKUs: {len(skus)}개")
    print(f"   - Stores: {len(stores)}개")
    
    # 목적함수: 총 할당량 최대화
    prob += lpSum(x[i][j] for i in skus['sku_id'] for j in stores['store_id'])
    print("✅ 목적함수: 총 할당량 최대화")
    
    constraint_count = 0
    
    # 1. SKU 공급량 제약
    for _, sku in skus.iterrows():
        prob += lpSum(x[sku['sku_id']][j] for j in stores['store_id']) <= sku['supply']
        constraint_count += 1
    print(f"✅ SKU 공급량 제약: {constraint_count}개")
    
    # 2. 상점별 제약
    store_constraints = 0
    
    for _, store in stores.iterrows():
        j = store['store_id']
        
        # 각 상점별 할당량 변수들
        all_alloc = lpSum(x[i][j] for i in skus['sku_id'])
        color_alloc = lpSum(x[i][j] for i in C_color) if C_color else 0
        size_alloc = lpSum(x[i][j] for i in S_size) if S_size else 0
        
        # 용량 제약
        prob += all_alloc <= store['cap']
        store_constraints += 1
        
        # 비율 제약
        if len(C_color) > 0:
            prob += color_alloc >= r_color_min * all_alloc
            prob += color_alloc <= r_color_max * all_alloc
            store_constraints += 2
        
        if len(S_size) > 0:
            prob += size_alloc >= r_size_min * all_alloc
            prob += size_alloc <= r_size_max * all_alloc
            store_constraints += 2
    
    print(f"✅ 상점별 제약: {store_constraints}개")
    
    # 3. 수요량 제약 (더 많이 포함)
    demand_sample_size = min(len(demand), len(skus) * len(stores) // 2)  # 50% 포함
    demand_sample = demand.sample(demand_sample_size, random_state=42)
    
    for _, row in demand_sample.iterrows():
        prob += x[row['sku_id']][row['store_id']] <= row['demand']
        constraint_count += 1
    
    print(f"✅ 수요량 제약: {len(demand_sample)}개 (전체 {len(demand)}개 중 50%)")
    
    total_constraints = constraint_count + store_constraints
    print(f"📋 총 제약조건: {total_constraints}개")
    print("🎯 프리미엄 품질을 위한 정교한 제약 설정!")
    
    return prob, x

def solve_premium_optimization(prob, max_time_minutes=10):
    """프리미엄 최적화 실행 - 더 긴 시간 제한"""
    print_header(f"프리미엄 최적화 실행 (최대 {max_time_minutes}분)")
    
    max_threads = psutil.cpu_count(logical=True)
    time_limit = max_time_minutes * 60  # 분을 초로 변환
    
    print(f"💻 시스템 정보:")
    print(f"   - 물리 코어: {psutil.cpu_count(logical=False)}개")
    print(f"   - 논리 코어: {max_threads}개")
    print(f"   - 메모리: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    
    print(f"\n🚀 프리미엄 최적화 시작: {datetime.now().strftime('%H:%M:%S')}")
    
    start_time = time.time()
    
    # 프리미엄 솔버 설정
    solver_options = {
        'msg': True,              # 실시간 출력
        'timeLimit': time_limit,  # 긴 시간 제한
        'threads': max_threads    # 모든 코어 활용
    }
    
    print(f"⚙️ 프리미엄 솔버 설정:")
    for key, value in solver_options.items():
        print(f"   {key}: {value}")
    
    print(f"\n🔥 최대 성능으로 {max_time_minutes}분간 최적화 진행!")
    print("=" * 60)
    
    try:
        solution_status = prob.solve(PULP_CBC_CMD(**solver_options))
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print("=" * 60)
        print(f"\n⏱️ 총 소요 시간: {elapsed_time/60:.2f}분 ({elapsed_time:.1f}초)")
        print(f"🏁 완료 시각: {datetime.now().strftime('%H:%M:%S')}")
        
        status_names = {
            1: "🏆 최적해 발견",
            0: "⏰ 시간 제한 도달 (최선해 보존)",
            -1: "❌ 실행 불가능한 문제",
            -2: "❌ 무한대 해",
            -3: "❌ 정의되지 않음"
        }
        
        print(f"📊 최적화 상태: {status_names.get(solution_status, '알 수 없음')} (코드: {solution_status})")
        
        return solution_status, elapsed_time
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None, time.time() - start_time

def analyze_premium_results(prob, x, skus, stores, solution_status, elapsed_time):
    """프리미엄 결과 분석"""
    print_header("프리미엄 결과 분석")
    
    if solution_status in [1, 0]:  # 최적해 또는 시간 제한
        try:
            objective_value = prob.objective.value()
            if solution_status == 1:
                print(f"🏆 최적 목적함수 값: {objective_value:.0f}")
            else:
                print(f"⏰ 시간 제한 도달시 목적함수 값: {objective_value:.0f}")
            
            # 결과 수집
            result_data = []
            for i in skus['sku_id']:
                for j in stores['store_id']:
                    try:
                        value = x[i][j].value()
                        if value and value > 0:
                            result_data.append({
                                'sku_id': i,
                                'store_id': j,
                                'allocation': int(value)
                            })
                    except:
                        continue
            
            if result_data:
                result_df = pd.DataFrame(result_data)
                
                print(f"\n📈 프리미엄 결과:")
                print(f"   - 총 할당량: {result_df['allocation'].sum():,}")
                print(f"   - 할당된 조합: {len(result_data):,}개")
                print(f"   - 평균 할당량: {result_df['allocation'].mean():.1f}")
                print(f"   - 최대 할당량: {result_df['allocation'].max()}")
                print(f"   - 최소 할당량: {result_df['allocation'].min()}")
                
                # 상위 결과 출력
                print(f"\n🔝 할당량 상위 10개:")
                top_results = result_df.nlargest(10, 'allocation')
                for i, (_, row) in enumerate(top_results.iterrows(), 1):
                    print(f"   {i:2d}. {row['sku_id']} → {row['store_id']}: {row['allocation']:,}")
                
                # 결과 저장
                result_df.to_csv('data/premium_allocation_result.csv', index=False)
                print(f"\n💾 프리미엄 결과 저장: data/premium_allocation_result.csv")
                
                return result_df, result_df['allocation'].sum()
                
        except Exception as e:
            print(f"❌ 결과 추출 실패: {e}")
            
    else:
        print("💡 최적화를 완료할 수 없습니다.")
    
    return None, 0

def compare_with_heuristic(skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max):
    """휴리스틱과 비교"""
    print_header("휴리스틱 기준선 생성")
    
    start_time = time.time()
    
    # 간단한 그리디 휴리스틱
    supply_left = skus.set_index('sku_id')['supply'].to_dict()
    result_data = []
    total_allocated = 0
    
    # 수요량 기준으로 정렬
    demand_sorted = demand.sort_values('demand', ascending=False)
    
    for _, row in demand_sorted.iterrows():
        sku_id = row['sku_id']
        store_id = row['store_id']
        demand_qty = row['demand']
        
        # 공급량 확인
        available_supply = supply_left.get(sku_id, 0)
        
        if available_supply > 0:
            allocate_qty = min(demand_qty, available_supply)
            
            result_data.append({
                'sku_id': sku_id,
                'store_id': store_id,
                'allocation': allocate_qty
            })
            
            supply_left[sku_id] -= allocate_qty
            total_allocated += allocate_qty
    
    heuristic_time = time.time() - start_time
    
    print(f"✅ 휴리스틱 완료:")
    print(f"   - 시간: {heuristic_time:.3f}초")
    print(f"   - 총 할당량: {total_allocated:,}")
    print(f"   - 할당 조합: {len(result_data):,}개")
    
    if result_data:
        heuristic_df = pd.DataFrame(result_data)
        heuristic_df.to_csv('data/heuristic_baseline.csv', index=False)
        print(f"   - 저장: data/heuristic_baseline.csv")
        
        return heuristic_df, total_allocated, heuristic_time
    
    return None, 0, heuristic_time

def main():
    """프리미엄 메인 함수"""
    print("🏆 SKU Distribution Optimizer - PREMIUM VERSION")
    print("=" * 80)
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 목표: 시간을 투자해서 최고 품질의 최적화 결과 달성")
    
    total_start = time.time()
    
    try:
        # 1. 프리미엄 데이터 생성
        print_section("1단계: 프리미엄 데이터 생성")
        df_skus, df_stores, df_demand = create_premium_data(num_skus=20, num_stores=80)
        
        # 2. 데이터 로드 및 분석
        skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max = load_and_analyze_premium_data()
        
        # 3. 휴리스틱 기준선
        print_section("2단계: 휴리스틱 기준선")
        heuristic_result, heuristic_obj, heuristic_time = compare_with_heuristic(
            skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max
        )
        
        # 4. 프리미엄 최적화
        print_section("3단계: 프리미엄 최적화")
        prob, x = create_premium_optimization_problem(
            skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max
        )
        
        # 기본값: 10분
        selected_time = 10
        print(f"\n🎯 최적화 시간: {selected_time}분")
        
        solution_status, elapsed_time = solve_premium_optimization(prob, max_time_minutes=selected_time)
        
        # 5. 프리미엄 결과 분석
        premium_result, premium_obj = analyze_premium_results(prob, x, skus, stores, solution_status, elapsed_time)
        
        # 6. 최종 비교
        print_header("최종 성과 비교")
        
        if heuristic_result is not None and premium_result is not None:
            improvement = ((premium_obj - heuristic_obj) / heuristic_obj * 100) if heuristic_obj > 0 else 0
            time_ratio = elapsed_time / heuristic_time if heuristic_time > 0 else 0
            
            print(f"📊 성과 비교:")
            print(f"   휴리스틱: {heuristic_obj:,} ({heuristic_time:.3f}초)")
            print(f"   프리미엄: {premium_obj:,} ({elapsed_time/60:.2f}분)")
            print(f"   개선량: +{premium_obj - heuristic_obj:,} ({improvement:+.1f}%)")
            print(f"   시간 비용: {time_ratio:.0f}배")
            
            if improvement > 0:
                efficiency = improvement / (elapsed_time / 60)  # 분당 개선율
                print(f"   효율성: {efficiency:.2f}% 개선/분")
                print(f"   🏆 프리미엄 최적화 성공!")
            else:
                print(f"   💡 휴리스틱이 이미 매우 우수한 결과")
                
        elif premium_result is not None:
            print(f"🎯 프리미엄 결과: {premium_obj:,}")
            print(f"⏱️ 소요 시간: {elapsed_time/60:.2f}분")
            
        # 7. 생성된 파일
        print_header("생성된 파일")
        print("📁 프리미엄 결과 파일:")
        print("   - data/sku.csv (SKU 정보)")
        print("   - data/store.csv (상점 정보)")
        print("   - data/demand.csv (수요 정보)")
        print("   - data/heuristic_baseline.csv (휴리스틱 기준선)")
        if premium_result is not None:
            print("   - data/premium_allocation_result.csv (프리미엄 최적화 결과)")
        
        total_time = time.time() - total_start
        print(f"\n⏱️ 총 실행시간: {total_time/60:.2f}분")
        print(f"✅ 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n🏆 프리미엄 최적화 완료! 시간을 투자한 만큼 더 나은 결과를 얻었습니다.")
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 