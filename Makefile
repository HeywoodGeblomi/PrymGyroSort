# PrymGyroSort build profiles
#   make              → portable -O3
#   make native       → -march=native -fopenmp
#   make binding / binding-native

CXX      ?= g++
CXXFLAGS_PORTABLE = -O3 -std=c++17 -Icpp/include
CXXFLAGS_NATIVE   = -O3 -std=c++17 -march=native -fopenmp -Icpp/include
LDFLAGS_NATIVE    = -fopenmp

.PHONY: all native rank_driver rank_driver_native binding binding-native clean

all: rank_driver

rank_driver: cpp/rank_driver.cpp cpp/include/gyro_rank.hpp
	@mkdir -p work
	$(CXX) $(CXXFLAGS_PORTABLE) cpp/rank_driver.cpp -o work/rank_driver
	@echo "[build] portable rank_driver → work/rank_driver"

native: rank_driver_native

rank_driver_native: cpp/rank_driver.cpp cpp/include/gyro_rank.hpp
	@mkdir -p work
	$(CXX) $(CXXFLAGS_NATIVE) cpp/rank_driver.cpp -o work/rank_driver_native $(LDFLAGS_NATIVE)
	@echo "[build] native+OpenMP rank_driver → work/rank_driver_native"

binding:
	cd python/bindings && python3 setup.py build_ext --inplace
	@echo "[build] portable prym_gyro_native.so"

binding-native:
	cd python/bindings && PRYM_NATIVE=1 python3 setup.py build_ext --inplace
	@echo "[build] native+OpenMP prym_gyro_native.so"

clean:
	rm -f work/rank_driver work/rank_driver_native
	rm -f python/bindings/prym_gyro_native*.so
	rm -rf python/bindings/build
