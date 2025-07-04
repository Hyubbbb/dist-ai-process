"""
3-Step 배분 불균형 분석 스크립트
(Step1: 커버리지 + Step2: 1개씩 배분 + Step3: 잔여 배분)
"""

import pandas as pd
import numpy as np
import os

def analyze_allocation_imbalance(experiment_folder=None):
    """배분 불균형 분석"""
    
    if experiment_folder is None:
        # extreme_coverage 시나리오 찾기
        output_dir = './output'
        extreme_folders = [f for f in os.listdir(output_dir) if 'extreme_coverage' in f and 'DWLG42044' in f]
        if extreme_folders:
            experiment_folder = extreme_folders[-1]  # 가장 최근 것
        else:
            # hybrid 폴더 찾기
            hybrid_folders = [f for f in os.listdir(output_dir) if 'hybrid' in f and 'DWLG42044' in f]
            if hybrid_folders:
                experiment_folder = hybrid_folders[-1]
    
    print(f'📁 분석 대상: {experiment_folder}')
    
    # 결과 파일 로드
    csv_file = None
    for file in os.listdir(f'./output/{experiment_folder}'):
        if file.endswith('_allocation_results.csv'):
            csv_file = f'./output/{experiment_folder}/{file}'
            break
    
    if csv_file is None:
        print('❌ 배분 결과 파일을 찾을 수 없습니다.')
        return []
    
    df = pd.read_csv(csv_file)
    
    print('🔍 현재 배분 현황 분석:')
    print('='*50)
    
    # SKU별 배분 현황 분석
    sku_analysis = df.groupby('SKU').agg({
        'SHOP_ID': 'count',
        'ALLOCATED_QTY': ['sum', 'mean', 'min', 'max'],
        'STORE_TIER': lambda x: list(x.unique())
    }).round(2)
    
    print('📊 SKU별 배분 요약:')
    for i, (sku, row) in enumerate(sku_analysis.head(8).iterrows()):
        shop_count = row[('SHOP_ID', 'count')]
        total_qty = row[('ALLOCATED_QTY', 'sum')]
        avg_qty = row[('ALLOCATED_QTY', 'mean')]
        min_qty = row[('ALLOCATED_QTY', 'min')]
        max_qty = row[('ALLOCATED_QTY', 'max')]
        tiers = row[('STORE_TIER', '<lambda>')]
        
        print(f'{i+1:2d}. {sku}')
        print(f'    매장수: {shop_count}개, 총량: {total_qty}개, 평균: {avg_qty:.1f}개')
        print(f'    최소: {min_qty}개, 최대: {max_qty}개')
        print(f'    배분받은 Tier: {tiers}')
        print()
    
    print('🎯 불균형 사례 찾기:')
    print('(상위 티어에만 배분되고 하위 티어에 배분되지 않은 SKU)')
    print('-'*50)
    
    imbalance_cases = []
    
    for sku in df['SKU'].unique():
        sku_data = df[df['SKU'] == sku]
        tier_distribution = sku_data.groupby('STORE_TIER')['ALLOCATED_QTY'].agg(['count', 'sum', 'mean']).round(1)
        
        # 각 Tier 존재 여부 확인
        tier1_exists = 'TIER_1_HIGH' in tier_distribution.index
        tier2_exists = 'TIER_2_MEDIUM' in tier_distribution.index  
        tier3_exists = 'TIER_3_LOW' in tier_distribution.index
        
        # 불균형 케이스: 상위 Tier에만 배분되고 하위 Tier에 배분되지 않은 경우
        if tier1_exists and not tier3_exists:
            tier1_avg = tier_distribution.loc['TIER_1_HIGH', 'mean']
            tier1_count = tier_distribution.loc['TIER_1_HIGH', 'count']
            
            imbalance_cases.append({
                'sku': sku,
                'tier1_avg': tier1_avg,
                'tier1_count': tier1_count,
                'tier2_exists': tier2_exists,
                'tier3_exists': tier3_exists
            })
            
            print(f'⚠️ {sku}: TIER_1에만 {tier1_count}매장 (평균 {tier1_avg:.1f}개)')
            if tier2_exists:
                tier2_avg = tier_distribution.loc['TIER_2_MEDIUM', 'mean']
                tier2_count = tier_distribution.loc['TIER_2_MEDIUM', 'count']
                print(f'   TIER_2에도 {tier2_count}매장 (평균 {tier2_avg:.1f}개)')
            print(f'   TIER_3에는 배분 없음 ❌')
            print()
    
    print(f'\n📊 불균형 분석 결과:')
    print(f'   총 SKU: {len(df["SKU"].unique())}개')
    print(f'   불균형 SKU: {len(imbalance_cases)}개')
    print(f'   불균형 비율: {len(imbalance_cases)/len(df["SKU"].unique())*100:.1f}%')
    
    # Tier별 전체 현황
    print(f'\n🏆 Tier별 전체 배분 현황:')
    tier_summary = df.groupby('STORE_TIER').agg({
        'SHOP_ID': 'nunique',
        'ALLOCATED_QTY': ['sum', 'mean']
    }).round(2)
    
    for tier in tier_summary.index:
        store_count = tier_summary.loc[tier, ('SHOP_ID', 'nunique')]
        total_qty = tier_summary.loc[tier, ('ALLOCATED_QTY', 'sum')]  
        avg_qty = tier_summary.loc[tier, ('ALLOCATED_QTY', 'mean')]
        print(f'   {tier}: {store_count}매장, 총 {total_qty}개 (매장당 평균 {avg_qty:.1f}개)')
    
    # 재분배 가능성 분석
    print(f'\n🔄 재분배 최적화 가능성:')
    print('-'*30)
    
    for sku in df['SKU'].unique():
        sku_data = df[df['SKU'] == sku]
        
        # Tier별 배분 현황
        tier1_data = sku_data[sku_data['STORE_TIER'] == 'TIER_1_HIGH']
        tier3_data = sku_data[sku_data['STORE_TIER'] == 'TIER_3_LOW']
        
        # TIER_1에서 3개 받은 매장이 있고, TIER_3에 0개인 매장이 있는 경우
        tier1_with_3 = len(tier1_data[tier1_data['ALLOCATED_QTY'] == 3])
        tier3_count = len(tier3_data)
        tier3_missing = 50 - tier3_count  # 전체 TIER_3 매장(50개) - 배분받은 매장
        
        if tier1_with_3 > 0 and tier3_missing > 0:
            possible_redistribution = min(tier1_with_3, tier3_missing)
            print(f'📦 {sku}:')
            print(f'   TIER_1에서 3개 받은 매장: {tier1_with_3}개')
            print(f'   TIER_3에서 미배분 매장: {tier3_missing}개')
            print(f'   재분배 가능: {possible_redistribution}개 (T1 3→2, T3 0→1)')
            print()
    
    return imbalance_cases

if __name__ == "__main__":
    analyze_allocation_imbalance() 