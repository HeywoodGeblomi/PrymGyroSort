/**
 * PrymGyroSort v0.1.1 — Prototype geometric multi-objective Sorter
 *
 * Uses GyroRank kernel on array structures inspired by
 * prym-eigenform-pipeline-d12 (period vectors of S(1,-2) and
 * path-local dual Rauzy evaluation intervals).
 *
 * M=2 objectives (lower better):
 *   obj0 = |local_pos_sum_approx - 8/5|
 *   obj1 = controlled QR / geometric residual proxy
 *
 * GyroController observes → gates Fenwick2D (elite) or LowAux.
 * Weak-dominance ranks isolate the cleanest geometric seeds / segments.
 *
 * Build:
 *   g++ -O3 -std=c++17 -Icpp/include examples/prym_gyro_demo.cpp -o prym_gyro_demo
 *
 * Usage:
 *   ./prym_gyro_demo [N=4096] [N_GOOD=48] [memory_pressure=0]
 *   ./prym_gyro_demo 65536 96 1     # large-N + force LowAux path
 *
 * Honesty: path-local geometric optimization only.
 * Does not claim global Lyapunov exponents. EXTERNAL-clean / no-χ.
 */

#include "gyro_rank.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <vector>

namespace {

constexpr double EIGHT_FIFTHS = 1.6;
constexpr uint32_t M = 2;
constexpr uint32_t DEFAULT_N = 4096;
constexpr uint32_t DEFAULT_N_GOOD = 48;
constexpr uint32_t SEED = 728;
constexpr double LAMBDA = 1.0 + 1.732050807568877;

} // namespace

int main(int argc, char** argv) {
    using namespace gyro;

    uint32_t N = DEFAULT_N;
    uint32_t N_GOOD = DEFAULT_N_GOOD;
    bool memory_pressure = false;
    if (argc >= 2) N = static_cast<uint32_t>(std::strtoul(argv[1], nullptr, 10));
    if (argc >= 3) N_GOOD = static_cast<uint32_t>(std::strtoul(argv[2], nullptr, 10));
    if (argc >= 4) memory_pressure = (std::strtoul(argv[3], nullptr, 10) != 0);
    if (N < 16) N = 16;
    if (N_GOOD < 1) N_GOOD = 1;
    if (N_GOOD > N / 2) N_GOOD = N / 2;

    if (N >= 65536 && argc < 4) {
        memory_pressure = true;
    }

    std::vector<double> matrix(static_cast<size_t>(N) * M);
    std::vector<int32_t> ranks(N), dom(N);
    std::vector<uint32_t> is_good(N, 0);

    uint32_t s = SEED;

    for (uint32_t i = 0; i < N; ++i) {
        double pos_approx, qr_proxy;
        if (i < N_GOOD) {
            double noise = (lcg_uniform(s) - 0.5) * 0.004;
            pos_approx = EIGHT_FIFTHS + noise;
            qr_proxy   = 1e-6 + lcg_uniform(s) * 4e-5;
            is_good[i] = 1;
        } else {
            double noise = (lcg_uniform(s) - 0.5) * 0.18;
            pos_approx = EIGHT_FIFTHS + noise;
            qr_proxy   = 1e-4 + lcg_uniform(s) * 2.5e-2;
        }
        matrix[i * M + 0] = std::abs(pos_approx - EIGHT_FIFTHS);
        matrix[i * M + 1] = qr_proxy;
    }

    {
        std::vector<uint32_t> perm(N);
        for (uint32_t i = 0; i < N; ++i) perm[i] = i;
        for (uint32_t i = N - 1; i > 0; --i) {
            uint32_t j = static_cast<uint32_t>(lcg_uniform(s) * (i + 1));
            if (j > i) j = i;
            std::swap(perm[i], perm[j]);
        }
        std::vector<double> tmp(static_cast<size_t>(N) * M);
        std::vector<uint32_t> good2(N, 0);
        for (uint32_t i = 0; i < N; ++i) {
            uint32_t src = perm[i];
            tmp[i * M + 0] = matrix[src * M + 0];
            tmp[i * M + 1] = matrix[src * M + 1];
            good2[i] = is_good[src];
        }
        matrix.swap(tmp);
        is_good.swap(good2);
    }

    auto t0 = std::chrono::high_resolution_clock::now();
    execute_gyro_rank(matrix.data(), N, M, ranks.data(), dom.data(), memory_pressure);
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    int32_t max_rank = 0;
    for (int32_t r : ranks) if (r > max_rank) max_rank = r;

    int32_t min_rank = ranks[0];
    for (int32_t r : ranks) if (r < min_rank) min_rank = r;

    std::vector<uint32_t> order(N);
    for (uint32_t i = 0; i < N; ++i) order[i] = i;
    std::stable_sort(order.begin(), order.end(),
                     [&](uint32_t a, uint32_t b) {
                         if (ranks[a] != ranks[b]) return ranks[a] < ranks[b];
                         return a < b;
                     });

    uint32_t top10 = std::min<uint32_t>(10, N);
    uint32_t good_in_top10 = 0;
    for (uint32_t k = 0; k < top10; ++k)
        if (is_good[order[k]]) ++good_in_top10;

    uint32_t good_on_front = 0;
    for (uint32_t i = 0; i < N; ++i)
        if (is_good[i] && ranks[i] == min_rank) ++good_on_front;

    double mean_good = 0, mean_rest = 0;
    uint32_t n_good = 0, n_rest = 0;
    for (uint32_t i = 0; i < N; ++i) {
        if (is_good[i]) { mean_good += ranks[i]; ++n_good; }
        else { mean_rest += ranks[i]; ++n_rest; }
    }
    if (n_good) mean_good /= n_good;
    if (n_rest) mean_rest /= n_rest;

    uint32_t band = std::max<uint32_t>(50u, static_cast<uint32_t>(0.05 * N));
    if (band > N) band = N;
    uint32_t good_in_band = 0;
    for (uint32_t k = 0; k < band; ++k)
        if (is_good[order[k]]) ++good_in_band;
    double recall = static_cast<double>(good_in_band) / n_good;
    bool ok_recall = (recall >= 0.60) || (good_in_band >= 40 && N_GOOD >= 48);
    bool ok_mean = mean_good < mean_rest;
    bool ok = ok_recall && ok_mean;

    std::cout << "  good_in_band (top " << band << ") = " << good_in_band
              << " / " << N_GOOD << " (recall=" << recall << ")\n";

    std::cout << "PrymGyroSort v0.1.1 — geometric multi-obj prototype\n"
              << "  Array source : Prym S(1,-2) period / dual-Rauzy path-local style\n"
              << "  Kernel       : GyroRank (GyroController + FenwickMax 2-D)\n"
              << "  N = " << N << ", M = " << M << ", N_good_anchors = " << N_GOOD << "\n"
              << "  memory_pressure = " << (memory_pressure ? "true" : "false") << "\n"
              << "  time         = " << ms << " ms\n"
              << "  max_rank     = " << max_rank << "\n"
              << "  good_on_front (rank=" << min_rank << ") = " << good_on_front << " / " << N_GOOD << "\n"
              << "  good_in_top10          = " << good_in_top10 << " / " << top10 << "\n"
              << "  mean_rank good=" << mean_good << "  rest=" << mean_rest << "\n"
              << "  first 12 ranked indices (rank, good?): ";
    for (uint32_t k = 0; k < 12 && k < N; ++k) {
        uint32_t idx = order[k];
        std::cout << idx << "(r" << ranks[idx] << (is_good[idx] ? ",G)" : ")");
        if (k + 1 < 12 && k + 1 < N) std::cout << " ";
    }
    std::cout << "\n"
              << "  SELF-CHECK   : " << (ok ? "GREEN" : "RED") << "\n";
    if (!ok) {
        std::cerr << "PrymGyroSort self-check FAILED\n";
        return 1;
    }
    std::cout << "  NON_CLAIMS   : path-local geometric ranking only; "
              << "no global Lyapunov claim; EXTERNAL-clean / no-χ\n";
    return 0;
}
