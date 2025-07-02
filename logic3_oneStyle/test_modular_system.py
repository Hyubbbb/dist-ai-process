"""
모듈화된 SKU 분배 최적화 시스템 테스트
"""

import sys
import os

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_data_loading():
    """데이터 로딩 테스트"""
    print("🧪 데이터 로딩 테스트...")
    
    try:
        from modules import DataLoader
        
        data_loader = DataLoader()
        data_loader.load_data()
        print(f"   ✅ 기본 데이터 로드 성공: SKU {len(data_loader.df_sku)}개, 매장 {len(data_loader.df_store)}개")
        
        data_loader.filter_by_style('DWLG42044')
        print(f"   ✅ 스타일 필터링 성공: {len(data_loader.df_sku_filtered)}개 SKU")
        
        data = data_loader.get_basic_data_structures()
        print(f"   ✅ 데이터 구조 생성 성공: {len(data['SKUs'])}개 SKU, {len(data['stores'])}개 매장")
        
        return True, data_loader
        
    except Exception as e:
        print(f"   ❌ 데이터 로딩 실패: {str(e)}")
        return False, None

def test_tier_system():
    """Tier 시스템 테스트"""
    print("\n🧪 Tier 시스템 테스트...")
    
    try:
        from modules import StoreTierSystem
        
        tier_system = StoreTierSystem()
        
        # 가상의 매장 리스트로 테스트
        test_stores = list(range(100))  # 100개 가상 매장
        limits = tier_system.create_store_allocation_limits(test_stores)
        
        print(f"   ✅ Tier 시스템 초기화 성공: {len(limits)}개 매장에 제한 설정")
        
        # Tier별 분포 확인
        tier_counts = tier_system.print_tier_summary(test_stores)
        
        return True, tier_system
        
    except Exception as e:
        print(f"   ❌ Tier 시스템 실패: {str(e)}")
        return False, None

def test_sku_classification():
    """SKU 분류 테스트"""
    print("\n🧪 SKU 분류 테스트...")
    
    try:
        # 먼저 데이터 로더 필요
        success, data_loader = test_data_loading()
        if not success:
            return False
        
        from modules import SKUClassifier
        
        classifier = SKUClassifier(data_loader.df_sku_filtered)
        data = data_loader.get_basic_data_structures()
        
        # 가상의 target_stores (처음 50개 매장)
        target_stores = data['stores'][:50]
        
        scarce, abundant = classifier.classify_skus(data['A'], target_stores)
        
        print(f"   ✅ SKU 분류 성공: 희소 {len(scarce)}개, 충분 {len(abundant)}개")
        
        stats = classifier.get_classification_stats()
        print(f"   📊 분류 비율: 희소 {stats['scarce_ratio']:.2f}, 충분 {stats['abundant_ratio']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ SKU 분류 실패: {str(e)}")
        return False

def test_modules_import():
    """모든 모듈 import 테스트"""
    print("🧪 모듈 import 테스트...")
    
    try:
        from modules import (
            DataLoader, StoreTierSystem, SKUClassifier,
            CoverageOptimizer, GreedyAllocator, ResultAnalyzer,
            ResultVisualizer, ExperimentManager
        )
        print("   ✅ 모든 모듈 import 성공")
        return True
        
    except Exception as e:
        print(f"   ❌ 모듈 import 실패: {str(e)}")
        return False

def test_config():
    """설정 파일 테스트"""
    print("\n🧪 설정 파일 테스트...")
    
    try:
        from config import (
            TIER_CONFIG, EXPERIMENT_SCENARIOS, 
            DEFAULT_TARGET_STYLE, DEFAULT_SCENARIO
        )
        
        print(f"   ✅ 설정 로드 성공:")
        print(f"      기본 스타일: {DEFAULT_TARGET_STYLE}")
        print(f"      기본 시나리오: {DEFAULT_SCENARIO}")
        print(f"      Tier 개수: {len(TIER_CONFIG)}개")
        print(f"      시나리오 개수: {len(EXPERIMENT_SCENARIOS)}개")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 설정 파일 실패: {str(e)}")
        return False

def run_all_tests():
    """모든 테스트 실행"""
    print("🚀 모듈화된 시스템 테스트 시작")
    print("="*50)
    
    tests = [
        ("모듈 import", test_modules_import),
        ("설정 파일", test_config),
        ("데이터 로딩", lambda: test_data_loading()[0]),
        ("Tier 시스템", lambda: test_tier_system()[0]),
        ("SKU 분류", test_sku_classification)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ {test_name} 테스트 중 예외 발생: {str(e)}")
            results.append((test_name, False))
    
    # 결과 요약
    print("\n" + "="*50)
    print("🏁 테스트 결과 요약")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 총 {passed}/{total} 테스트 통과 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 모든 테스트 통과! 시스템이 정상적으로 모듈화되었습니다.")
        print("\n💡 다음 단계:")
        print("   python main.py  # 전체 시스템 실행")
        print("   또는")
        print("   from main import run_optimization")
        print("   run_optimization()  # Python에서 직접 실행")
    else:
        print("⚠️ 일부 테스트가 실패했습니다. 문제를 해결한 후 다시 시도하세요.")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests() 