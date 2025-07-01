#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SKU Distribution Optimizer
==========================
SKU를 여러 상점에 최적으로 배분하는 최적화 시스템

작성자: AI Assistant
날짜: 2024
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
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def print_section(title):
    """서브섹션 헤더 출력"""
    print(f"\n🔹 {title}")
    print("-" * 40)

def create_dummy_data():
    """더미 데이터 생성 및 저장"""
    print_header("데이터 생성")
    
    # data 디렉토리 생성
    if not os.path.exists('data'):
        os.makedirs('data')
        print("📁 data 디렉토리 생성됨")
    
    np.random.seed(42)
    num_skus = 20
    num_stores = 100
    
    colors = ['black', 'gray', 'white', 'navy', 'red', 'green', 'blue', 'yellow']
    sizes = ['S', 'M', 'L', 'XS', 'XL', 'XXL', 'XXS']
    
    print_section("SKU 데이터 생성")
    sku_list = []
    for i in range(num_skus):
        sku_list.append({
            'sku_id': f'SKU_{i+1}',
            'color': np.random.choice(colors),
            'size': np.random.choice(sizes),
            'supply': np.random.randint(50, 200)
        })
    df_skus = pd.DataFrame(sku_list)
    df_skus.to_csv('data/sku.csv', index=False)
    print(f"✅ SKU 데이터 생성 완료: {len(df_skus)}개")
    
    print_section("상점 데이터 생성")
    store_list = []
    for j in range(num_stores):
        store_list.append({
            'store_id': f'ST_{j+1}',
            'cap': np.random.randint(100, 500)
        })
    df_stores = pd.DataFrame(store_list)
    df_stores.to_csv('data/store.csv', index=False)
    print(f"✅ 상점 데이터 생성 완료: {len(df_stores)}개")
    
    print_section("수요 데이터 생성")
    demand_rows = []
    for _, sku in df_skus.iterrows():
        for _, store in df_stores.iterrows():
            demand_rows.append({
                'sku_id': sku['sku_id'],
                'store_id': store['store_id'],
                'demand': np.random.randint(0, store['cap'] // 5)
            })
    df_demand = pd.DataFrame(demand_rows)
    df_demand.to_csv('data/demand.csv', index=False)
    print(f"✅ 수요 데이터 생성 완료: {len(df_demand):,}개 조합")
    
    return df_skus, df_stores, df_demand

def load_data():
    """데이터 로드 및 전처리"""
    print_header("데이터 로드 및 전처리")
    
    # 데이터 불러오기
    skus = pd.read_csv('data/sku.csv')
    stores = pd.read_csv('data/store.csv')
    demand = pd.read_csv('data/demand.csv')
    
    print(f"📊 데이터 로드 완료:")
    print(f"   - SKUs: {len(skus)}개")
    print(f"   - Stores: {len(stores)}개")
    print(f"   - Demand combinations: {len(demand):,}개")
    
    # 집합 정의
    C_color = skus[~skus['color'].isin(['black','gray','white','navy'])]['sku_id'].tolist()
    S_size = skus[~skus['size'].isin(['S','M','L'])]['sku_id'].tolist()
    
    print(f"\n🎨 색상 집합 (특수 색상): {len(C_color)}개")
    print(f"📏 사이즈 집합 (특수 사이즈): {len(S_size)}개")
    
    # 글로벌 비율 계산 (demand 기반)
    merged = demand.merge(stores, on='store_id').merge(skus[['sku_id','color','size']], on='sku_id')
    
    r_color_max = merged[~merged['color'].isin(['black','gray','white','navy'])]['demand'].sum() / merged['demand'].sum()
    r_color_min = 0.1  # 도메인 전문가 지정
    
    r_size_max = merged[~merged['size'].isin(['S','M','L'])]['demand'].sum() / merged['demand'].sum()
    r_size_min = 0.05  # 도메인 전문가 지정
    
    print(f"\n📈 비율 제약:")
    print(f"   - 색상 비율 범위: {r_color_min:.2f} - {r_color_max:.2f}")
    print(f"   - 사이즈 비율 범위: {r_size_min:.2f} - {r_size_max:.2f}")
    
    return skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max

def analyze_system():
    """시스템 정보 분석"""
    print_header("시스템 정보 분석")
    
    # CPU 정보 확인
    logical_cores = psutil.cpu_count(logical=True)
    physical_cores = psutil.cpu_count(logical=False)
    
    print(f"💻 CPU 정보:")
    print(f"   - 물리 코어: {physical_cores}개")
    print(f"   - 논리 코어: {logical_cores}개 (하이퍼스레딩)")
    
    # 메모리 정보
    memory = psutil.virtual_memory()
    print(f"\n💾 메모리 정보:")
    print(f"   - 총 메모리: {memory.total / (1024**3):.1f} GB")
    print(f"   - 사용 가능: {memory.available / (1024**3):.1f} GB")
    print(f"   - 사용률: {memory.percent}%")
    
    print(f"\n⚙️ 권장 스레드 설정:")
    print(f"   - 소규모 문제: 1~2 스레드")
    print(f"   - 중간 문제: 4 스레드")
    print(f"   - 대규모 문제: {logical_cores-1} 스레드")
    print(f"   - 최대 성능: {logical_cores} 스레드")
    
    return logical_cores, physical_cores

def create_optimization_problem(skus, stores, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max):
    """최적화 문제 정의"""
    print_header("최적화 문제 정의")
    
    # 문제 정의
    prob = LpProblem("SKU_Distribution", LpMaximize)
    x = LpVariable.dicts("x", (skus['sku_id'], stores['store_id']), lowBound=0, cat=LpInteger)
    
    print(f"📊 문제 규모:")
    print(f"   - 변수 수: {len(skus) * len(stores):,}개")
    print(f"   - SKUs: {len(skus)}개")
    print(f"   - Stores: {len(stores)}개")
    
    # 목적함수
    prob += lpSum(x[i][j] for i in skus['sku_id'] for j in stores['store_id'])
    print("✅ 목적함수: 총 할당량 최대화")
    
    # 제약조건 추가
    constraint_count = 0
    
    # 1. 각 SKU의 공급량 제약
    for _, sku in skus.iterrows():
        prob += lpSum(x[sku['sku_id']][j] for j in stores['store_id']) <= sku['supply']
        constraint_count += 1
    print(f"✅ SKU 공급량 제약: {constraint_count}개")
    
    # 2. 각 store의 용량 및 비율 제약
    store_constraints = 0
    for _, store in stores.iterrows():
        j = store['store_id']
        all_alloc = lpSum(x[i][j] for i in skus['sku_id'])
        color_alloc = lpSum(x[i][j] for i in C_color)
        size_alloc = lpSum(x[i][j] for i in S_size)
        
        # 용량 제약
        prob += all_alloc <= store['cap']
        store_constraints += 1
        
        # 색상 비율 제약
        prob += color_alloc >= r_color_min * all_alloc
        prob += color_alloc <= r_color_max * all_alloc
        store_constraints += 2
        
        # 사이즈 비율 제약
        prob += size_alloc >= r_size_min * all_alloc
        prob += size_alloc <= r_size_max * all_alloc
        store_constraints += 2
    
    print(f"✅ 상점별 제약조건: {store_constraints}개")
    print(f"📋 총 제약조건: {constraint_count + store_constraints}개")
    
    return prob, x

def solve_optimization(prob, max_threads=None, time_limit=300):
    """최적화 실행"""
    print_header("최적화 실행")
    
    if max_threads is None:
        max_threads = psutil.cpu_count(logical=True)
    
    print(f"🚀 최적화 시작: {datetime.now().strftime('%H:%M:%S')}")
    print(f"💻 시스템 정보: 물리 코어 {psutil.cpu_count(logical=False)}개, 논리 코어 {psutil.cpu_count(logical=True)}개")
    
    start_time = time.time()
    
    # 솔버 설정
    solver_options = {
        'msg': True,              # 실시간 콘솔 출력
        'timeLimit': time_limit,  # 시간 제한
        'threads': max_threads    # 최대 스레드 사용
    }
    
    print(f"\n⚙️ 솔버 설정:")
    for key, value in solver_options.items():
        print(f"   {key}: {value}")
    
    print(f"\n🔥 최대 성능으로 최적화 시작! (스레드: {max_threads}개)")
    print("=" * 60)
    
    # 최적화 실행
    try:
        solution_status = prob.solve(PULP_CBC_CMD(**solver_options))
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print("=" * 60)
        print(f"\n⏱️ 총 소요 시간: {elapsed_time:.2f}초")
        print(f"🏁 완료 시각: {datetime.now().strftime('%H:%M:%S')}")
        
        return solution_status, elapsed_time
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None, None

def analyze_results(prob, x, skus, stores, solution_status, elapsed_time):
    """결과 분석 및 출력"""
    print_header("결과 분석")
    
    status_dict = {
        1: "최적해 발견",
        0: "시간 제한으로 중단",
        -1: "실행 불가능한 문제",
        -2: "무한대 해",
        -3: "정의되지 않음"
    }
    
    print(f"📊 최적화 결과:")
    if solution_status is not None:
        print(f"   상태: {status_dict.get(solution_status, '알 수 없음')} (코드: {solution_status})")
        print(f"   소요 시간: {elapsed_time:.2f}초")
        
        if solution_status == 1:
            # 성공적인 해결
            objective_value = prob.objective.value()
            print(f"   목적함수 값: {objective_value:.0f}")
            
            # 결과 데이터 수집
            result_data = []
            for i in skus['sku_id']:
                for j in stores['store_id']:
                    value = x[i][j].value()
                    if value and value > 0:
                        result_data.append({
                            'sku_id': i,
                            'store_id': j,
                            'allocation': int(value)
                        })
            
            if result_data:
                result_df = pd.DataFrame(result_data)
                
                print(f"\n📈 결과 요약:")
                print(f"   총 할당량: {result_df['allocation'].sum():,}")
                print(f"   할당된 조합: {len(result_df):,}개")
                print(f"   평균 할당량: {result_df['allocation'].mean():.1f}")
                
                # 상위 결과 출력
                print(f"\n🔝 할당량 상위 10개:")
                top_results = result_df.nlargest(10, 'allocation')
                print(top_results.to_string(index=False))
                
                # 결과 저장
                result_df.to_csv('data/allocation_result.csv', index=False)
                print(f"\n💾 결과 저장: data/allocation_result.csv")
                
                # 상세 분석
                analyze_detailed_results(result_df)
                
                return result_df
            else:
                print("❌ 할당된 결과가 없습니다.")
                
        elif solution_status == 0:
            print("💡 시간 제한으로 중단되었습니다. time_limit을 늘려보세요.")
            
        else:
            print("💡 문제를 해결할 수 없습니다. 제약조건을 확인해보세요.")
    else:
        print("❌ 최적화가 실행되지 않았습니다.")
    
    return None

def analyze_detailed_results(result_df):
    """상세 결과 분석"""
    print_section("상세 분석")
    
    # SKU별 할당 현황
    sku_summary = result_df.groupby('sku_id')['allocation'].agg(['sum', 'count', 'mean']).round(1)
    sku_summary.columns = ['총할당량', '할당상점수', '평균할당량']
    print(f"\n📦 SKU별 할당 현황 (상위 5개):")
    print(sku_summary.nlargest(5, '총할당량').to_string())
    
    # 상점별 할당 현황
    store_summary = result_df.groupby('store_id')['allocation'].agg(['sum', 'count']).round(1)
    store_summary.columns = ['총할당량', '할당SKU수']
    print(f"\n🏪 상점별 할당 현황 (상위 5개):")
    print(store_summary.nlargest(5, '총할당량').to_string())

def print_solver_info():
    """솔버 정보 출력"""
    print_section("CBC 솔버 매개변수 참고")
    print("✅ 지원 매개변수:")
    print("   • msg=True: 실시간 진행상황 출력")
    print("   • timeLimit=300: 시간 제한 (초)")
    print("   • threads=16: 병렬 처리 스레드 수")
    print("   • logPath='log.txt': 로그 파일 저장 (msg 출력 비활성화됨)")
    
    print("\n❌ 미지원 매개변수:")
    print("   • fracGap: 자동처리")
    print("   • presolve: 자동활성화")
    print("   • cuts: 자동활성화")

def main():
    """메인 실행 함수"""
    print("🚀 SKU Distribution Optimizer")
    print("=" * 60)
    print(f"실행 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 데이터 생성
        df_skus, df_stores, df_demand = create_dummy_data()
        
        # 2. 데이터 로드 및 전처리
        skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max = load_data()
        
        # 3. 시스템 분석
        logical_cores, physical_cores = analyze_system()
        
        # 4. 최적화 문제 정의
        prob, x = create_optimization_problem(skus, stores, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max)
        
        # 5. 최적화 실행
        solution_status, elapsed_time = solve_optimization(prob, max_threads=logical_cores, time_limit=300)
        
        # 6. 결과 분석
        result_df = analyze_results(prob, x, skus, stores, solution_status, elapsed_time)
        
        # 7. 솔버 정보 출력
        print_solver_info()
        
        print_header("실행 완료")
        print(f"총 실행 시간: {time.time() - start_time:.2f}초")
        print(f"완료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("✅ 모든 작업이 완료되었습니다!")
        
        if result_df is not None:
            print(f"\n📁 생성된 파일:")
            print(f"   - data/sku.csv")
            print(f"   - data/store.csv") 
            print(f"   - data/demand.csv")
            print(f"   - data/allocation_result.csv")
        
    except Exception as e:
        print(f"\n❌ 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    start_time = time.time()
    main() 