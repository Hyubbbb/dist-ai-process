# 커버리지 중심 최적화
python main.py --sku_file "../data_real/발주수량.csv" --store_file "../data_real/매장데이터.csv" --scenario coverage_focused --config "config.yaml" --output_dir "../output"

# 균형 중심 최적화  
python main.py --sku_file "../data_real/발주수량.csv" --store_file "../data_real/매장데이터.csv" --scenario balance_focused --config "config.yaml" --output_dir "../output"

# 하이브리드 접근
python main.py --sku_file "../data_real/발주수량.csv" --store_file "../data_real/매장데이터.csv" --scenario hybrid --config "config.yaml" --output_dir "../output"

# 극단적 커버리지
python main.py --sku_file "../data_real/발주수량.csv" --store_file "../data_real/매장데이터.csv" --scenario extreme_coverage --config "config.yaml" --output_dir "../output"

# 실용적 시나리오
python main.py --sku_file "../data_real/발주수량.csv" --store_file "../data_real/매장데이터.csv" --scenario practical --config "config.yaml" --output_dir "../output"

# QTY_SUM 비례 배분 중심
python main.py --sku_file "../data_real/발주수량.csv" --store_file "../data_real/매장데이터.csv" --scenario proportional_focused --config "config.yaml" --output_dir "../output"

# 최대 분산 추구
python main.py --sku_file "../data_real/발주수량.csv" --store_file "../data_real/매장데이터.csv" --scenario max_dispersion --config "config.yaml" --output_dir "../output"