# PrymGyroSort build profiles
#   make native       → -march=native (rank path still sequential)
#   make native-omp   → optional -fopenmp link; NO omp pragmas in rank path yet

CXX ?= g++
CXXFLAGS_PORTABLE = -O3 -std=c++17 -Icpp/include
CXXFLAGS_NATIVE = -O3 -std=c++17 -march=native -Icpp/include
CXXFLAGS_NATIVE_OMP = -O3 -std=c++17 -march=native -fopenmp -Icpp/include

.PHONY: all native native-omp rank_driver rank_driver_native rank_driver_native_omp binding binding-native clean

all: rank_driver

rank_driver: cpp/rank_driver.cpp cpp/include/gyro_rank.hpp
	@mkdir -p work
	$(CXX) $(CXXFLAGS_PORTABLE) cpp/rank_driver.cpp -o work/rank_driver
	@echo "[build] portable rank_driver"

native: rank_driver_native
rank_driver_native: cpp/rank_driver.cpp cpp/include/gyro_rank.hpp
	@mkdir -p work
	$(CXX) $(CXXFLAGS_NATIVE) cpp/rank_driver.cpp -o work/rank_driver_native
	@echo "[build] native rank_driver (-march=native; sequential rank path)"

native-omp: rank_driver_native_omp
rank_driver_native_omp: cpp/rank_driver.cpp cpp/include/gyro_rank.hpp
	@mkdir -p work
	$(CXX) $(CXXFLAGS_NATIVE_OMP) cpp/rank_driver.cpp -o work/rank_driver_native_omp -fopenmp
	@echo "[build] native-omp (link-safe only; no rank-path pragmas)"

binding:
	cd python/bindings && python3 setup.py build_ext --inplace
binding-native:
	cd python/bindings && PRYM_NATIVE=1 python3 setup.py build_ext --inplace

clean:
	rm -f work/rank_driver work/rank_driver_native work/rank_driver_native_omp
	rm -f python/bindings/prym_gyro_native*.so
	rm -rf python/bindings/build
