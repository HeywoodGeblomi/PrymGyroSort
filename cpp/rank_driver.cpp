/**
 * PrymGyroSort rank driver — thin bridge over GyroRank
 *
 * Reads matrix.bin (N*M little-endian float64 row-major)
 * Calls gyro::execute_gyro_rank
 * Writes ranks.bin (N int32) + rank_report.json
 *
 * Large-N: N >= 65536 auto-enables memory_pressure -> LowAux2D
 *
 * Build:
 *   # fetch header if needed
 *   curl -fsSL https://raw.githubusercontent.com/HeywoodGeblomi/GyroRank/main/include/gyro_rank.hpp -o cpp/include/gyro_rank.hpp
 *   g++ -O3 -std=c++17 -Icpp/include cpp/rank_driver.cpp -o rank_driver
 *
 * Usage:
 *   rank_driver <matrix.bin> <N> <M> <out_dir> [memory_pressure=0|1]
 */

#include "gyro_rank.hpp"

#include <cstdint>
#include <vector>
#include <fstream>
#include <iostream>
#include <string>
#include <chrono>

static bool read_matrix(const std::string& path, uint32_t n, uint32_t m,
                        std::vector<double>& out) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return false;
    out.resize(static_cast<size_t>(n) * m);
    in.read(reinterpret_cast<char*>(out.data()),
            static_cast<std::streamsize>(out.size() * sizeof(double)));
    return static_cast<bool>(in);
}

int main(int argc, char** argv) {
    if (argc < 5) {
        std::cerr << "Usage: rank_driver <matrix.bin> <N> <M> <out_dir> [memory_pressure]\n";
        return 1;
    }
    const std::string matrix_path = argv[1];
    const uint32_t N = static_cast<uint32_t>(std::stoul(argv[2]));
    const uint32_t M = static_cast<uint32_t>(std::stoul(argv[3]));
    const std::string out_dir = argv[4];
    bool memory_pressure = (argc > 5) && (std::string(argv[5]) == "1");
    if (N >= 65536u) memory_pressure = true;

    std::vector<double> matrix;
    if (!read_matrix(matrix_path, N, M, matrix)) {
        std::cerr << "[PrymGyro] failed to read matrix\n";
        return 1;
    }

    std::vector<int32_t> ranks(N), dom(N);
    auto t0 = std::chrono::high_resolution_clock::now();
    gyro::execute_gyro_rank(matrix.data(), N, M, ranks.data(), dom.data(), memory_pressure);
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    {
        std::ofstream out(out_dir + "/ranks.bin", std::ios::binary);
        out.write(reinterpret_cast<const char*>(ranks.data()),
                  static_cast<std::streamsize>(ranks.size() * sizeof(int32_t)));
    }

    int32_t max_rank = 0;
    for (int32_t r : ranks) if (r > max_rank) max_rank = r;

    std::ofstream rep(out_dir + "/rank_report.json");
    rep << "{\n  \"n\": " << N << ",\n  \"m\": " << M
        << ",\n  \"time_ms\": " << ms
        << ",\n  \"max_rank\": " << max_rank
        << ",\n  \"memory_pressure\": " << (memory_pressure ? "true" : "false")
        << "\n}\n";

    std::cout << "[PrymGyroSort] ranked N=" << N << " M=" << M
              << " time_ms=" << ms << " max_rank=" << max_rank
              << " memory_pressure=" << memory_pressure << "\n";
    return 0;
}
