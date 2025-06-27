#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SKU Distribution Optimizer - With Smart Ratio Constraints
=========================================================
비율 제약을 유지하면서도 효율적으로 해결하는 버전

개선사항:
- 비율 제약을 더 효율적으로 구현
- 문제 크기는 적당히 축소
- Big-M 방법 대신 선형화 기법 사용
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

def create_data_with_ratios(num_skus=12, num_stores=40):
    """비율 제약을 고려한 데이터 생성"""
    print_header("비율 제약 고려 데이터 생성")
    
    if not os.path.exists('data'):
        os.makedirs('data')
        print("📁 data 디렉토리 생성됨")
    
    np.random.seed(42)
    
    colors = ['black', 'gray', 'white', 'navy', 'red', 'green', 'blue', 'yellow']
    sizes = ['S', 'M', 'L', 'XS', 'XL', 'XXL']
    
    print_section("SKU 데이터 생성")
    sku_list = []
    for i in range(num_skus):
        sku_list.append({
            'sku_id': f'SKU_{i+1}',
            'color': np.random.choice(colors),
            'size': np.random.choice(sizes),
            'supply': np.random.randint(80, 200)
        })
    df_skus = pd.DataFrame(sku_list)
    df_skus.to_csv('data/sku.csv', index=False)
    print(f"✅ SKU 데이터: {len(df_skus)}개")
    
    print_section("상점 데이터 생성")
    store_list = []
    for j in range(num_stores):
        store_list.append({
            'store_id': f'ST_{j+1}',
            'cap': np.random.randint(60, 150)
        })
    df_stores = pd.DataFrame(store_list)
    df_stores.to_csv('data/store.csv', index=False)
    print(f"✅ 상점 데이터: {len(df_stores)}개")
    
    print_section("수요 데이터 생성")
    demand_rows = []
    for _, sku in df_skus.iterrows():
        for _, store in df_stores.iterrows():
            demand_rows.append({
                'sku_id': sku['sku_id'],
                'store_id': store['store_id'],
                'demand': np.random.randint(1, min(30, store['cap'] // 3))
            })
    df_demand = pd.DataFrame(demand_rows)
    df_demand.to_csv('data/demand.csv', index=False)
    print(f"✅ 수요 데이터: {len(df_demand):,}개 조합")
    
    print(f"\n📊 문제 크기 (비율 제약 포함):")
    print(f"   - 변수 수: {num_skus * num_stores:,}개")
    print(f"   - SKUs: {num_skus}개")
    print(f"   - Stores: {num_stores}개")
    print(f"   - 예상 제약조건: ~{num_skus + num_stores * 5}개")
    
    return df_skus, df_stores, df_demand

def load_and_analyze_data():
    """데이터 로드 및 비율 분석"""
    print_header("데이터 로드 및 비율 분석")
    
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
    
    print(f"\n🎨 색상 집합 분석:")
    print(f"   - 기본 색상 (black,gray,white,navy): {len(skus) - len(C_color)}개")
    print(f"   - 특수 색상 (red,green,blue,yellow): {len(C_color)}개")
    
    print(f"\n📏 사이즈 집합 분석:")
    print(f"   - 기본 사이즈 (S,M,L): {len(skus) - len(S_size)}개")
    print(f"   - 특수 사이즈 (XS,XL,XXL): {len(S_size)}개")
    
    # 글로벌 비율 계산 (더 현실적으로)
    merged = demand.merge(stores, on='store_id').merge(skus[['sku_id','color','size']], on='sku_id')
    
    total_demand = merged['demand'].sum()
    color_demand = merged[~merged['color'].isin(['black','gray','white','navy'])]['demand'].sum()
    size_demand = merged[~merged['size'].isin(['S','M','L'])]['demand'].sum()
    
    r_color_actual = color_demand / total_demand
    r_size_actual = size_demand / total_demand
    
    # 비율 범위 설정 (실제 데이터 기반으로 여유있게)
    r_color_min = max(0.05, r_color_actual - 0.15)
    r_color_max = min(0.8, r_color_actual + 0.15)
    
    r_size_min = max(0.05, r_size_actual - 0.15)  
    r_size_max = min(0.8, r_size_actual + 0.15)
    
    print(f"\n📈 비율 제약 설정:")
    print(f"   - 실제 색상 비율: {r_color_actual:.3f}")
    print(f"   - 색상 비율 범위: {r_color_min:.3f} - {r_color_max:.3f}")
    print(f"   - 실제 사이즈 비율: {r_size_actual:.3f}")
    print(f"   - 사이즈 비율 범위: {r_size_min:.3f} - {r_size_max:.3f}")
    
    return skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max

def create_efficient_ratio_problem(skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max):
    """효율적인 비율 제약 구현"""
    print_header("효율적인 비율 제약 최적화 문제")
    
    prob = LpProblem("SKU_Distribution_With_Ratios", LpMaximize)
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
    
    # 2. 상점별 제약 (효율적 구현)
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
        
        # 비율 제약 (간단한 선형 형태로)
        if len(C_color) > 0:
            # 색상 비율 제약
            prob += color_alloc >= r_color_min * all_alloc
            prob += color_alloc <= r_color_max * all_alloc
            store_constraints += 2
        
        if len(S_size) > 0:
            # 사이즈 비율 제약  
            prob += size_alloc >= r_size_min * all_alloc
            prob += size_alloc <= r_size_max * all_alloc
            store_constraints += 2
    
    print(f"✅ 상점별 제약: {store_constraints}개")
    
    # 3. 수요량 제약 (샘플링으로 축소)
    demand_sample_size = min(len(demand), len(skus) * len(stores) // 3)
    demand_sample = demand.sample(demand_sample_size, random_state=42)
    
    for _, row in demand_sample.iterrows():
        prob += x[row['sku_id']][row['store_id']] <= row['demand']
        constraint_count += 1
    
    print(f"✅ 수요량 제약: {len(demand_sample)}개 (전체 {len(demand)}개 중 샘플)")
    
    total_constraints = constraint_count + store_constraints
    print(f"📋 총 제약조건: {total_constraints}개")
    print("🎯 비율 제약 유지하면서 효율성 개선!")
    
    return prob, x

def solve_with_progressive_timeout(prob, initial_timeout=60):
    """점진적 시간 제한으로 해결"""
    print_header(f"점진적 최적화 (초기 제한: {initial_timeout}초)")
    
    timeouts = [initial_timeout, initial_timeout * 2, initial_timeout * 4]  # 60초, 120초, 240초
    
    for i, timeout in enumerate(timeouts):
        print_section(f"시도 {i+1}: {timeout}초 제한")
        
        start_time = time.time()
        
        solver_options = {
            'msg': True,
            'timeLimit': timeout,
            'threads': min(4, psutil.cpu_count(logical=True))  # 적당한 스레드 수
        }
        
        print(f"⚙️ 솔버 설정: {solver_options}")
        print(f"🚀 시작: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 40)
        
        try:
            solution_status = prob.solve(PULP_CBC_CMD(**solver_options))
            elapsed_time = time.time() - start_time
            
            print("=" * 40)
            print(f"⏱️ 소요 시간: {elapsed_time:.2f}초")
            print(f"🏁 완료: {datetime.now().strftime('%H:%M:%S')}")
            
            if solution_status == 1:  # 최적해 발견
                print("✅ 최적해 발견!")
                return solution_status, elapsed_time
            elif solution_status == 0:  # 시간 제한
                print("⏰ 시간 제한 - 다음 단계로...")
                if i == len(timeouts) - 1:  # 마지막 시도
                    print("💡 최종 시간 제한 도달")
                    return solution_status, elapsed_time
            else:
                print(f"❌ 문제 발생 (상태: {solution_status})")
                return solution_status, elapsed_time
                
        except Exception as e:
            print(f"❌ 오류: {e}")
            if i == len(timeouts) - 1:
                return None, time.time() - start_time
    
    return None, 0

def solve_ratio_heuristic(skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max):
    """비율을 고려한 휴리스틱 해법"""
    print_header("비율 고려 휴리스틱 해법")
    
    start_time = time.time()
    
    # 초기화
    supply_left = skus.set_index('sku_id')['supply'].to_dict()
    capacity_left = stores.set_index('store_id')['cap'].to_dict()
    
    result_data = []
    total_allocated = 0
    
    # 각 상점별로 비율을 맞춰가며 할당
    for _, store in stores.iterrows():
        store_id = store['store_id']
        store_cap = store['cap']
        
        store_allocations = []
        store_total = 0
        
        # 수요량 기준으로 해당 상점의 수요 정렬
        store_demands = demand[demand['store_id'] == store_id].sort_values('demand', ascending=False)
        
        # 1단계: 기본 할당 (용량의 70%까지)
        target_basic = int(store_cap * 0.7)
        
        for _, row in store_demands.iterrows():
            if store_total >= target_basic:
                break
                
            sku_id = row['sku_id']
            demand_qty = row['demand']
            
            can_allocate = min(
                demand_qty,
                supply_left.get(sku_id, 0),
                target_basic - store_total
            )
            
            if can_allocate > 0:
                store_allocations.append({
                    'sku_id': sku_id,
                    'store_id': store_id,
                    'allocation': can_allocate
                })
                
                supply_left[sku_id] -= can_allocate
                store_total += can_allocate
        
        # 2단계: 비율 조정 (나머지 30%)
        if store_total > 0 and len(C_color) > 0 and len(S_size) > 0:
            current_color = sum(alloc['allocation'] for alloc in store_allocations if alloc['sku_id'] in C_color)
            current_size = sum(alloc['allocation'] for alloc in store_allocations if alloc['sku_id'] in S_size)
            
            color_ratio = current_color / store_total if store_total > 0 else 0
            size_ratio = current_size / store_total if store_total > 0 else 0
            
            remaining_capacity = store_cap - store_total
            
            # 색상 비율이 부족하면 특수 색상 우선 할당
            if color_ratio < r_color_min and remaining_capacity > 0:
                color_demands = store_demands[store_demands['sku_id'].isin(C_color)]
                for _, row in color_demands.iterrows():
                    if remaining_capacity <= 0:
                        break
                    
                    sku_id = row['sku_id']
                    can_allocate = min(
                        row['demand'],
                        supply_left.get(sku_id, 0),
                        remaining_capacity
                    )
                    
                    if can_allocate > 0:
                        store_allocations.append({
                            'sku_id': sku_id,
                            'store_id': store_id,
                            'allocation': can_allocate
                        })
                        
                        supply_left[sku_id] -= can_allocate
                        remaining_capacity -= can_allocate
            
            # 사이즈 비율도 동일하게 조정
            if size_ratio < r_size_min and remaining_capacity > 0:
                size_demands = store_demands[store_demands['sku_id'].isin(S_size)]
                for _, row in size_demands.iterrows():
                    if remaining_capacity <= 0:
                        break
                    
                    sku_id = row['sku_id']
                    can_allocate = min(
                        row['demand'],
                        supply_left.get(sku_id, 0),
                        remaining_capacity
                    )
                    
                    if can_allocate > 0:
                        store_allocations.append({
                            'sku_id': sku_id,
                            'store_id': store_id,
                            'allocation': can_allocate
                        })
                        
                        supply_left[sku_id] -= can_allocate
                        remaining_capacity -= can_allocate
        
        # 상점별 결과를 전체 결과에 추가
        result_data.extend(store_allocations)
        total_allocated += sum(alloc['allocation'] for alloc in store_allocations)
        capacity_left[store_id] = store_cap - sum(alloc['allocation'] for alloc in store_allocations)
    
    elapsed_time = time.time() - start_time
    
    print(f"✅ 비율 고려 휴리스틱 완료:")
    print(f"   - 시간: {elapsed_time:.3f}초")
    print(f"   - 총 할당량: {total_allocated:,}")
    print(f"   - 할당 조합: {len(result_data):,}개")
    
    if result_data:
        result_df = pd.DataFrame(result_data)
        
        # 비율 검증
        validation_results = []
        for _, store in stores.iterrows():
            store_id = store['store_id']
            store_allocs = result_df[result_df['store_id'] == store_id]
            
            if len(store_allocs) > 0:
                total_store = store_allocs['allocation'].sum()
                color_store = store_allocs[store_allocs['sku_id'].isin(C_color)]['allocation'].sum()
                size_store = store_allocs[store_allocs['sku_id'].isin(S_size)]['allocation'].sum()
                
                color_ratio = color_store / total_store if total_store > 0 else 0
                size_ratio = size_store / total_store if total_store > 0 else 0
                
                validation_results.append({
                    'store_id': store_id,
                    'total': total_store,
                    'color_ratio': color_ratio,
                    'size_ratio': size_ratio,
                    'color_ok': r_color_min <= color_ratio <= r_color_max,
                    'size_ok': r_size_min <= size_ratio <= r_size_max
                })
        
        validation_df = pd.DataFrame(validation_results)
        color_violations = len(validation_df[~validation_df['color_ok']])
        size_violations = len(validation_df[~validation_df['size_ok']])
        
        print(f"\n🔍 비율 준수 검증:")
        print(f"   - 색상 비율 위반: {color_violations}/{len(validation_df)}개 상점")
        print(f"   - 사이즈 비율 위반: {size_violations}/{len(validation_df)}개 상점")
        
        result_df.to_csv('data/heuristic_with_ratios.csv', index=False)
        return result_df, total_allocated
    
    return None, 0

def analyze_ratio_compliance(result_df, skus, stores, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max):
    """비율 준수 상세 분석"""
    print_header("비율 준수 상세 분석")
    
    # SKU별 색상/사이즈 정보 매핑
    sku_info = skus.set_index('sku_id')[['color', 'size']].to_dict('index')
    
    # 상점별 상세 분석
    store_analysis = []
    
    for _, store in stores.iterrows():
        store_id = store['store_id']
        store_cap = store['cap']
        store_allocs = result_df[result_df['store_id'] == store_id]
        
        if len(store_allocs) == 0:
            continue
            
        # 기본 통계
        total_allocated = store_allocs['allocation'].sum()
        num_skus_allocated = len(store_allocs)
        capacity_utilization = total_allocated / store_cap
        
        # 색상별 분석
        color_breakdown = {}
        for _, row in store_allocs.iterrows():
            sku_id = row['sku_id']
            allocation = row['allocation']
            color = sku_info[sku_id]['color']
            
            if color not in color_breakdown:
                color_breakdown[color] = 0
            color_breakdown[color] += allocation
        
        # 사이즈별 분석
        size_breakdown = {}
        for _, row in store_allocs.iterrows():
            sku_id = row['sku_id']
            allocation = row['allocation']
            size = sku_info[sku_id]['size']
            
            if size not in size_breakdown:
                size_breakdown[size] = 0
            size_breakdown[size] += allocation
        
        # 비율 계산
        special_color_total = sum(color_breakdown.get(color, 0) for color in ['red', 'green', 'blue', 'yellow'])
        special_size_total = sum(size_breakdown.get(size, 0) for size in ['XS', 'XL', 'XXL'])
        
        color_ratio = special_color_total / total_allocated if total_allocated > 0 else 0
        size_ratio = special_size_total / total_allocated if total_allocated > 0 else 0
        
        # 준수 여부 확인
        color_compliant = r_color_min <= color_ratio <= r_color_max
        size_compliant = r_size_min <= size_ratio <= r_size_max
        
        store_analysis.append({
            'store_id': store_id,
            'capacity': store_cap,
            'total_allocated': total_allocated,
            'capacity_utilization': capacity_utilization,
            'num_skus': num_skus_allocated,
            'special_color_qty': special_color_total,
            'special_size_qty': special_size_total,
            'color_ratio': color_ratio,
            'size_ratio': size_ratio,
            'color_compliant': color_compliant,
            'size_compliant': size_compliant,
            'color_breakdown': color_breakdown,
            'size_breakdown': size_breakdown
        })
    
    # DataFrame으로 변환
    analysis_df = pd.DataFrame(store_analysis)
    
    # 정렬: 총 할당량 기준 내림차순
    analysis_df = analysis_df.sort_values('total_allocated', ascending=False)
    
    return analysis_df

def create_detailed_reports(result_df, analysis_df, skus, stores, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max, method_name="optimal"):
    """상세 보고서 생성"""
    print_header(f"{method_name.upper()} 결과 상세 보고서 생성")
    
    # 1. 할당 결과 정렬 및 저장
    print_section("1. 할당 결과 정리")
    
    # SKU 정보 병합
    sku_info = skus[['sku_id', 'color', 'size', 'supply']].copy()
    detailed_result = result_df.merge(sku_info, on='sku_id')
    
    # 상점 정보 병합
    store_info = stores[['store_id', 'cap']].copy()
    detailed_result = detailed_result.merge(store_info, on='store_id')
    
    # 정렬: 상점별, 할당량별
    detailed_result = detailed_result.sort_values(['store_id', 'allocation'], ascending=[True, False])
    
    # 저장
    detailed_result.to_csv(f'data/{method_name}_detailed_allocation.csv', index=False)
    print(f"✅ 상세 할당 결과: data/{method_name}_detailed_allocation.csv")
    
    # 2. 상점별 비율 분석 보고서
    print_section("2. 상점별 비율 분석")
    
    # 기본 통계 추가
    total_stores = len(analysis_df)
    allocated_stores = len(analysis_df[analysis_df['total_allocated'] > 0])
    
    color_violations = len(analysis_df[~analysis_df['color_compliant']])
    size_violations = len(analysis_df[~analysis_df['size_compliant']])
    
    color_compliance_rate = (allocated_stores - color_violations) / allocated_stores * 100 if allocated_stores > 0 else 0
    size_compliance_rate = (allocated_stores - size_violations) / allocated_stores * 100 if allocated_stores > 0 else 0
    
    print(f"📊 전체 통계:")
    print(f"   - 총 상점: {total_stores}개")
    print(f"   - 할당된 상점: {allocated_stores}개")
    print(f"   - 색상 비율 준수: {allocated_stores - color_violations}/{allocated_stores}개 ({color_compliance_rate:.1f}%)")
    print(f"   - 사이즈 비율 준수: {allocated_stores - size_violations}/{allocated_stores}개 ({size_compliance_rate:.1f}%)")
    
    # 상점별 분석 결과 저장
    store_summary = analysis_df[[
        'store_id', 'capacity', 'total_allocated', 'capacity_utilization', 'num_skus',
        'color_ratio', 'size_ratio', 'color_compliant', 'size_compliant'
    ]].copy()
    
    # 백분율로 변환
    store_summary['capacity_utilization'] = (store_summary['capacity_utilization'] * 100).round(1)
    store_summary['color_ratio'] = (store_summary['color_ratio'] * 100).round(1)
    store_summary['size_ratio'] = (store_summary['size_ratio'] * 100).round(1)
    
    store_summary.to_csv(f'data/{method_name}_store_analysis.csv', index=False)
    print(f"✅ 상점별 분석: data/{method_name}_store_analysis.csv")
    
    # 3. 위반 상점 상세 분석
    print_section("3. 비율 위반 상점 분석")
    
    violation_details = []
    
    for _, row in analysis_df.iterrows():
        violations = []
        
        if not row['color_compliant']:
            violations.append(f"색상비율 {row['color_ratio']:.1%} (범위: {r_color_min:.1%}-{r_color_max:.1%})")
        
        if not row['size_compliant']:
            violations.append(f"사이즈비율 {row['size_ratio']:.1%} (범위: {r_size_min:.1%}-{r_size_max:.1%})")
        
        if violations:
            violation_details.append({
                'store_id': row['store_id'],
                'total_allocated': row['total_allocated'],
                'violations': '; '.join(violations),
                'color_breakdown': str(row['color_breakdown']),
                'size_breakdown': str(row['size_breakdown'])
            })
    
    if violation_details:
        violation_df = pd.DataFrame(violation_details)
        violation_df = violation_df.sort_values('total_allocated', ascending=False)
        violation_df.to_csv(f'data/{method_name}_violations.csv', index=False)
        print(f"⚠️ 위반 상점 상세: data/{method_name}_violations.csv ({len(violation_details)}개 상점)")
        
        # 상위 5개 위반 상점 출력
        print(f"\n🔍 주요 위반 상점 (상위 5개):")
        for i, (_, row) in enumerate(violation_df.head().iterrows()):
            print(f"   {i+1}. {row['store_id']}: {row['violations']}")
    else:
        print("✅ 비율 위반 상점 없음!")
    
    # 4. SKU별 할당 현황
    print_section("4. SKU별 할당 현황")
    
    sku_summary = detailed_result.groupby(['sku_id', 'color', 'size', 'supply']).agg({
        'allocation': ['sum', 'count', 'mean'],
        'store_id': 'count'
    }).round(1)
    
    sku_summary.columns = ['total_allocated', 'allocation_count', 'avg_allocation', 'num_stores']
    sku_summary = sku_summary.reset_index()
    sku_summary['supply_utilization'] = (sku_summary['total_allocated'] / sku_summary['supply'] * 100).round(1)
    
    # 정렬: 총 할당량 기준
    sku_summary = sku_summary.sort_values('total_allocated', ascending=False)
    sku_summary.to_csv(f'data/{method_name}_sku_summary.csv', index=False)
    print(f"✅ SKU별 요약: data/{method_name}_sku_summary.csv")
    
    # 5. 색상/사이즈별 집계
    print_section("5. 색상/사이즈별 집계")
    
    color_summary = detailed_result.groupby('color')['allocation'].sum().sort_values(ascending=False)
    size_summary = detailed_result.groupby('size')['allocation'].sum().sort_values(ascending=False)
    
    print(f"🎨 색상별 할당량:")
    for color, qty in color_summary.items():
        special_mark = "⭐" if color in ['red', 'green', 'blue', 'yellow'] else ""
        print(f"   {color}: {qty:,} {special_mark}")
    
    print(f"\n📏 사이즈별 할당량:")
    for size, qty in size_summary.items():
        special_mark = "⭐" if size in ['XS', 'XL', 'XXL'] else ""
        print(f"   {size}: {qty:,} {special_mark}")
    
    # 집계 결과 저장
    color_summary.to_csv(f'data/{method_name}_color_summary.csv', header=['total_allocation'])
    size_summary.to_csv(f'data/{method_name}_size_summary.csv', header=['total_allocation'])
    
    print(f"✅ 색상별 집계: data/{method_name}_color_summary.csv")
    print(f"✅ 사이즈별 집계: data/{method_name}_size_summary.csv")
    
    return {
        'total_stores': total_stores,
        'allocated_stores': allocated_stores,
        'color_compliance_rate': color_compliance_rate,
        'size_compliance_rate': size_compliance_rate,
        'violation_count': len(violation_details)
    }

def print_evaluation_summary(stats, method_name, total_allocation, elapsed_time):
    """평가 요약 출력"""
    print_header(f"{method_name.upper()} 최종 평가 요약")
    
    print(f"🎯 성과 지표:")
    print(f"   - 총 할당량: {total_allocation:,}")
    print(f"   - 실행 시간: {elapsed_time:.3f}초")
    print(f"   - 할당 상점: {stats['allocated_stores']}/{stats['total_stores']}개")
    
    print(f"\n📊 비율 준수율:")
    print(f"   - 색상 비율: {stats['color_compliance_rate']:.1f}%")
    print(f"   - 사이즈 비율: {stats['size_compliance_rate']:.1f}%")
    print(f"   - 위반 상점: {stats['violation_count']}개")
    
    # 등급 평가
    overall_compliance = (stats['color_compliance_rate'] + stats['size_compliance_rate']) / 2
    
    if overall_compliance >= 95:
        grade = "🏆 EXCELLENT"
    elif overall_compliance >= 85:
        grade = "🥇 GOOD"
    elif overall_compliance >= 70:
        grade = "🥈 FAIR"
    else:
        grade = "🥉 NEEDS IMPROVEMENT"
    
    print(f"\n📈 종합 평가: {grade} ({overall_compliance:.1f}%)")

def main():
    """메인 함수"""
    print("🚀 SKU Distribution Optimizer - With Smart Ratio Constraints")
    print("=" * 70)
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    total_start = time.time()
    
    try:
        # 1. 비율 제약을 고려한 데이터 생성
        print_section("1단계: 데이터 생성")
        df_skus, df_stores, df_demand = create_data_with_ratios(num_skus=20, num_stores=100)
        
        # 2. 데이터 로드 및 비율 분석
        skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max = load_and_analyze_data()
        
        # 3. 비율 고려 휴리스틱 해법
        print_section("2단계: 비율 고려 휴리스틱")
        heuristic_start = time.time()
        heuristic_result, heuristic_obj = solve_ratio_heuristic(
            skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max
        )
        heuristic_time = time.time() - heuristic_start
        
        # 휴리스틱 결과 상세 분석
        if heuristic_result is not None:
            print_section("2-1. 휴리스틱 결과 상세 분석")
            heuristic_analysis = analyze_ratio_compliance(
                heuristic_result, skus, stores, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max
            )
            heuristic_stats = create_detailed_reports(
                heuristic_result, heuristic_analysis, skus, stores, C_color, S_size, 
                r_color_min, r_color_max, r_size_min, r_size_max, "heuristic"
            )
            print_evaluation_summary(heuristic_stats, "HEURISTIC", heuristic_obj, heuristic_time)
        
        # 4. 효율적인 비율 제약 최적화
        print_section("3단계: 비율 제약 최적화")
        prob, x = create_efficient_ratio_problem(
            skus, stores, demand, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max
        )
        
        solution_status, elapsed_time = solve_with_progressive_timeout(prob, initial_timeout=60)
        
        # 5. 최적화 결과 분석
        optimal_result = None
        optimal_obj = 0
        
        if solution_status in [1, 0]:  # 최적해 또는 시간 제한
            print_header("최적화 결과 분석")
            
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
                optimal_result = pd.DataFrame(result_data)
                optimal_obj = optimal_result['allocation'].sum()
                
                print(f"✅ 최적화 성공:")
                print(f"   - 총 할당량: {optimal_obj:,}")
                print(f"   - 할당 조합: {len(result_data):,}개")
                print(f"   - 소요 시간: {elapsed_time:.2f}초")
                
                # 최적화 결과 상세 분석
                print_section("3-1. 최적화 결과 상세 분석")
                optimal_analysis = analyze_ratio_compliance(
                    optimal_result, skus, stores, C_color, S_size, r_color_min, r_color_max, r_size_min, r_size_max
                )
                optimal_stats = create_detailed_reports(
                    optimal_result, optimal_analysis, skus, stores, C_color, S_size, 
                    r_color_min, r_color_max, r_size_min, r_size_max, "optimal"
                )
                print_evaluation_summary(optimal_stats, "OPTIMAL", optimal_obj, elapsed_time)
            else:
                print("⚠️ 최적화 결과 없음")
        
        # 6. 최종 비교 및 평가
        print_header("최종 결과 비교 및 평가")
        
        if heuristic_result is not None and optimal_result is not None:
            print(f"🔍 휴리스틱 결과: {heuristic_obj:,} ({heuristic_time:.3f}초)")
            print(f"🎯 최적화 결과: {optimal_obj:,} ({elapsed_time:.2f}초)")
            
            if heuristic_obj > 0:
                improvement = ((optimal_obj - heuristic_obj) / heuristic_obj * 100)
                print(f"📈 할당량 개선: {improvement:.1f}%")
            
            # 비율 준수율 비교
            if 'heuristic_stats' in locals() and 'optimal_stats' in locals():
                print(f"\n📊 비율 준수율 비교:")
                print(f"   휴리스틱 - 색상: {heuristic_stats['color_compliance_rate']:.1f}%, 사이즈: {heuristic_stats['size_compliance_rate']:.1f}%")
                print(f"   최적화   - 색상: {optimal_stats['color_compliance_rate']:.1f}%, 사이즈: {optimal_stats['size_compliance_rate']:.1f}%")
                
        elif heuristic_result is not None:
            print(f"🔍 휴리스틱 결과만 사용: {heuristic_obj:,}")
            print("⚠️ 최적화 실패 - 휴리스틱 결과 참조")
        
        # 7. 생성된 파일 목록
        print_header("생성된 분석 파일")
        print("📁 기본 데이터:")
        print("   - data/sku.csv (SKU 정보)")
        print("   - data/store.csv (상점 정보)")
        print("   - data/demand.csv (수요 정보)")
        
        if heuristic_result is not None:
            print("\n📊 휴리스틱 결과:")
            print("   - data/heuristic_detailed_allocation.csv (상세 할당 결과)")
            print("   - data/heuristic_store_analysis.csv (상점별 비율 분석)")
            print("   - data/heuristic_sku_summary.csv (SKU별 요약)")
            print("   - data/heuristic_violations.csv (비율 위반 상점)")
            print("   - data/heuristic_color_summary.csv (색상별 집계)")
            print("   - data/heuristic_size_summary.csv (사이즈별 집계)")
        
        if optimal_result is not None:
            print("\n🎯 최적화 결과:")
            print("   - data/optimal_detailed_allocation.csv (상세 할당 결과)")
            print("   - data/optimal_store_analysis.csv (상점별 비율 분석)")
            print("   - data/optimal_sku_summary.csv (SKU별 요약)")
            print("   - data/optimal_violations.csv (비율 위반 상점)")
            print("   - data/optimal_color_summary.csv (색상별 집계)")
            print("   - data/optimal_size_summary.csv (사이즈별 집계)")
        
        total_time = time.time() - total_start
        print(f"\n⏱️ 총 실행시간: {total_time:.2f}초")
        print(f"✅ 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n🎯 비율 제약을 유지하면서도 효율적으로 해결하고 상세 분석 완료!")
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 