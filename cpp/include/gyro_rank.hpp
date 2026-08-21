/**
 * @file gyro_rank.hpp
 * @brief GyroRank — Elite Gyroscopic Ranking Optimizer (v0.2)
 * Vendored into PrymGyroSort from https://github.com/HeywoodGeblomi/GyroRank @ 18b89bd
 *
 * Phase 1: rank identity (silent 1-D escape deleted, Rank1D ≤ M=1, Approx1D opt-in).
 * Phase 2: LowAux2D stub deleted.
 * Phase 3: cheap observe (sample S≤1024) + striate writing dumpable U[k].
 *
 * Exact M=2 path is FenwickMax only. memory_pressure is currently a no-op for algorithm selection.
 * GYR-FIX-001 F4: U_ initializer length matches Strategy::COUNT.
 */

#pragma once

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <limits>
#include <vector>
#include <utility>
#include <cmath>
#include <cassert>
#include <type_traits>
#include <cstdio>

#if defined(_OPENMP)
#include <omp.h>
#endif

#if __has_include("pdqsort.h")
  #include "pdqsort.h"
  #define GYRO_SORT(...) ::pdqsort(__VA_ARGS__)
#elif __has_include(<pdqsort.h>)
  #include <pdqsort.h>
  #define GYRO_SORT(...) ::pdqsort(__VA_ARGS__)
#else
  #define GYRO_SORT(...) ::std::sort(__VA_ARGS__)
#endif

namespace gyro {

constexpr uint32_t LCG_A   = 1664525u;
constexpr uint32_t LCG_C   = 1013904223u;
constexpr uint64_t LCG_DIV = 0x100000000ull;

inline uint32_t lcg_next(uint32_t& s) {
    s = LCG_A * s + LCG_C;
    return s;
}

inline double lcg_uniform(uint32_t& s) {
    return static_cast<double>(lcg_next(s)) / static_cast<double>(LCG_DIV);
}

class FenwickMax {
public:
    explicit FenwickMax(uint32_t n) : n_(std::max(n, 1u)), bit_(n_ + 4, 0) {}
    void clear() { std::fill(bit_.begin(), bit_.end(), 0); }
    void update(uint32_t idx, int32_t val) {
        for (uint32_t x = idx + 1; x <= n_ + 1 && x < bit_.size(); x += x & -x)
            if (val > bit_[x]) bit_[x] = val;
    }
    int32_t prefix_max(int32_t idx) const {
        if (idx < 0) return 0;
        int32_t m = 0;
        for (int32_t x = idx + 1; x > 0; x -= x & -x) {
            uint32_t ux = static_cast<uint32_t>(x);
            if (ux < bit_.size() && bit_[ux] > m) m = bit_[ux];
        }
        return m;
    }
private:
    uint32_t n_;
    std::vector<int32_t> bit_;
};

class FenwickSum {
public:
    explicit FenwickSum(uint32_t n) : n_(std::max(n, 1u)), bit_(n_ + 4, 0) {}
    void add(uint32_t idx, int32_t delta) {
        for (uint32_t x = idx + 1; x <= n_ + 1 && x < bit_.size(); x += x & -x)
            bit_[x] += delta;
    }
    int32_t prefix_sum(int32_t idx) const {
        if (idx < 0) return 0;
        int32_t s = 0;
        for (int32_t x = idx + 1; x > 0; x -= x & -x) {
            uint32_t ux = static_cast<uint32_t>(x);
            if (ux < bit_.size()) s += bit_[ux];
        }
        return s;
    }
private:
    uint32_t n_;
    std::vector<int32_t> bit_;
};

inline void compress_column(const double* matrix, uint32_t n, uint32_t m,
                            uint32_t col, std::vector<uint32_t>& out_rank,
                            uint32_t& max_rank) {
    if (n == 0) { out_rank.clear(); max_rank = 0; return; }
    std::vector<std::pair<double, uint32_t>> vals(n);
    for (uint32_t i = 0; i < n; ++i)
        vals[i] = {matrix[i * m + col], i};

    GYRO_SORT(vals.begin(), vals.end(),
              [](const auto& a, const auto& b) {
                  if (a.first != b.first) return a.first < b.first;
                  return a.second < b.second;
              });

    out_rank.assign(n, 0);
    uint32_t r = 0;
    for (uint32_t k = 0; k < n; ++k) {
        if (k && vals[k].first != vals[k - 1].first) ++r;
        out_rank[vals[k].second] = r;
    }
    max_rank = r;
}

inline double sortedness_1d(const double* col, uint32_t n, uint32_t stride = 1) {
    if (n <= 1) return 1.0;
    uint32_t ordered = 0;
    for (uint32_t i = 0; i + 1 < n; ++i)
        if (col[i * stride] <= col[(i + 1) * stride]) ++ordered;
    return static_cast<double>(ordered) / (n - 1);
}

inline void exact_rank_2d_fenwick(const double* matrix, uint32_t n, uint32_t m,
                                  int32_t* ranks_out, int32_t* dom_out = nullptr) {
    if (n == 0) return;
    std::fill(ranks_out, ranks_out + n, 1);
    if (dom_out) std::fill(dom_out, dom_out + n, 0);
    if (m < 2) return;

    std::vector<uint32_t> y_rank;
    uint32_t max_y = 0;
    compress_column(matrix, n, m, 1, y_rank, max_y);

    std::vector<uint32_t> order(n);
    for (uint32_t i = 0; i < n; ++i) order[i] = i;

    GYRO_SORT(order.begin(), order.end(),
              [&](uint32_t a, uint32_t b) {
                  double ax = matrix[a * m + 0], bx = matrix[b * m + 0];
                  if (ax != bx) return ax < bx;
                  double ay = matrix[a * m + 1], by = matrix[b * m + 1];
                  if (ay != by) return ay < by;
                  return a < b;
              });

    FenwickMax fenwick(max_y + 2);
    FenwickSum fenwick_cnt(max_y + 2);

    uint32_t i = 0;
    while (i < n) {
        uint32_t j = i;
        double x0 = matrix[order[i] * m + 0];
        while (j < n && matrix[order[j] * m + 0] == x0) ++j;

        for (uint32_t k = i; k < j; ++k) {
            uint32_t idx = order[k];
            uint32_t yr  = y_rank[idx];
            int32_t better = fenwick.prefix_max(static_cast<int32_t>(yr));
            int32_t cnt    = fenwick_cnt.prefix_sum(static_cast<int32_t>(yr));
            if (better > 0) ranks_out[idx] = better + 1;
            if (dom_out)    dom_out[idx]   = cnt;
        }
        for (uint32_t k = i; k < j; ++k) {
            uint32_t idx = order[k];
            fenwick.update(y_rank[idx], ranks_out[idx]);
            fenwick_cnt.add(y_rank[idx], 1);
        }
        i = j;
    }
}

inline void rank_1d(const double* matrix, uint32_t n, uint32_t m,
                    int32_t* ranks_out) {
    if (n == 0) return;
    std::vector<uint32_t> order(n);
    for (uint32_t i = 0; i < n; ++i) order[i] = i;

    GYRO_SORT(order.begin(), order.end(),
              [&](uint32_t a, uint32_t b) {
                  if (matrix[a * m] != matrix[b * m])
                      return matrix[a * m] < matrix[b * m];
                  return a < b;
              });

    int32_t layer = 1;
    uint32_t i = 0;
    while (i < n) {
        uint32_t j = i;
        double v = matrix[order[i] * m];
        while (j < n && matrix[order[j] * m] == v) ++j;
        for (uint32_t k = i; k < j; ++k)
            ranks_out[order[k]] = layer;
        ++layer;
        i = j;
    }
}

struct GyroOptions {
    bool exact = true;
    bool memory_pressure = false;
    uint64_t memory_budget_bytes = 0;
    bool allow_approx_1d = false;
};

struct GyroFeatures {
    uint32_t n = 0;
    uint32_t m = 0;
    double   sortedness_0 = 1.0;
    double   sortedness_1 = 1.0;
    uint32_t uniq_x_hat = 0;
    uint32_t uniq_y_hat = 0;
    double   density_product = 0.0;
    bool     memory_pressure = false;
    uint64_t memory_budget_bytes = 0;
};

enum class Strategy : uint8_t {
    Rank1D,
    Fenwick2D,
    NestedOrProjection,
    Approx1D,
    COUNT
};

constexpr double GYRO_C1 = 1.0;
constexpr double GYRO_C2 = 0.5;
constexpr double GYRO_LAMBDA_MEM = 1e12;
constexpr double GYRO_INF = 1e300;

class GyroController {
public:
    GyroFeatures observe(const double* matrix, uint32_t n, uint32_t m,
                         bool memory_pressure = false,
                         uint64_t memory_budget_bytes = 0) {
        feats_.n = n;
        feats_.m = m;
        feats_.memory_pressure = memory_pressure;
        feats_.memory_budget_bytes = memory_budget_bytes;
        feats_.sortedness_0 = 1.0;
        feats_.sortedness_1 = 1.0;
        feats_.uniq_x_hat = 0;
        feats_.uniq_y_hat = 0;
        feats_.density_product = 0.0;
        if (n == 0 || m == 0) return feats_;

        const uint32_t S = std::min(n, 1024u);
        const uint32_t step = (n + S - 1) / S;

        {
            std::vector<double> sample;
            sample.reserve(S);
            for (uint32_t i = 0; i < n && sample.size() < S; i += step)
                sample.push_back(matrix[i * m + 0]);
            uint32_t ordered = 0;
            for (size_t i = 0; i + 1 < sample.size(); ++i)
                if (sample[i] <= sample[i + 1]) ++ordered;
            feats_.sortedness_0 = sample.size() <= 1 ? 1.0 : static_cast<double>(ordered) / (sample.size() - 1);
            std::vector<double> sorted_s = sample;
            std::sort(sorted_s.begin(), sorted_s.end());
            feats_.uniq_x_hat = static_cast<uint32_t>(std::unique(sorted_s.begin(), sorted_s.end()) - sorted_s.begin());
        }

        if (m >= 2) {
            std::vector<double> sample;
            sample.reserve(S);
            for (uint32_t i = 0; i < n && sample.size() < S; i += step)
                sample.push_back(matrix[i * m + 1]);
            uint32_t ordered = 0;
            for (size_t i = 0; i + 1 < sample.size(); ++i)
                if (sample[i] <= sample[i + 1]) ++ordered;
            feats_.sortedness_1 = sample.size() <= 1 ? 1.0 : static_cast<double>(ordered) / (sample.size() - 1);
            std::vector<double> sorted_s = sample;
            std::sort(sorted_s.begin(), sorted_s.end());
            feats_.uniq_y_hat = static_cast<uint32_t>(std::unique(sorted_s.begin(), sorted_s.end()) - sorted_s.begin());
        }

        feats_.density_product = static_cast<double>(feats_.uniq_x_hat) * static_cast<double>(std::max(feats_.uniq_y_hat, 1u));
        return feats_;
    }

    void striate(const GyroOptions& opt) {
        const auto& f = feats_;
        const double logN = std::log2(static_cast<double>(f.n) + 1.0);
        const double NlogN = static_cast<double>(f.n) * logN;

        for (int i = 0; i < static_cast<int>(Strategy::COUNT); ++i)
            U_[i] = GYRO_INF;

        if (f.m <= 1)
            U_[static_cast<int>(Strategy::Rank1D)] = GYRO_C1 * NlogN;

        if (f.m >= 2)
            U_[static_cast<int>(Strategy::Fenwick2D)] =
                GYRO_C1 * NlogN + GYRO_C2 * static_cast<double>(f.uniq_y_hat);

        if (f.m >= 3)
            U_[static_cast<int>(Strategy::NestedOrProjection)] =
                GYRO_C1 * NlogN + GYRO_C2 * static_cast<double>(f.uniq_y_hat);

        if (opt.allow_approx_1d && !opt.exact)
            U_[static_cast<int>(Strategy::Approx1D)] = GYRO_C1 * NlogN;

        if (opt.memory_pressure || (opt.memory_budget_bytes > 0 && f.density_product > 1e9)) {
            if (U_[static_cast<int>(Strategy::Fenwick2D)] < GYRO_INF)
                U_[static_cast<int>(Strategy::Fenwick2D)] += GYRO_LAMBDA_MEM * 0.01;
        }

#ifdef GYRO_DEBUG
        std::fprintf(stderr, "[gyro] n=%u m=%u sortedness_0=%.4f sortedness_1=%.4f "
                             "uniq_x_hat=%u uniq_y_hat=%u density=%.0f mem_pressure=%d\n",
                     f.n, f.m, f.sortedness_0, f.sortedness_1,
                     f.uniq_x_hat, f.uniq_y_hat, f.density_product,
                     f.memory_pressure ? 1 : 0);
        std::fprintf(stderr, "[gyro] U[Rank1D]=%.3g U[Fenwick2D]=%.3g U[NestedOrProjection]=%.3g U[Approx1D]=%.3g\n",
                     U_[static_cast<int>(Strategy::Rank1D)],
                     U_[static_cast<int>(Strategy::Fenwick2D)],
                     U_[static_cast<int>(Strategy::NestedOrProjection)],
                     U_[static_cast<int>(Strategy::Approx1D)]);
#endif
    }

    Strategy gate(const GyroOptions& opt) const {
        Strategy best = Strategy::Fenwick2D;
        double bestU = GYRO_INF;

        auto consider = [&](Strategy s) {
            double u = U_[static_cast<int>(s)];
            if (u < bestU) {
                bestU = u;
                best = s;
            }
        };

        if (feats_.m <= 1)
            consider(Strategy::Rank1D);
        if (feats_.m == 2)
            consider(Strategy::Fenwick2D);
        if (feats_.m >= 3)
            consider(Strategy::NestedOrProjection);
        if (opt.allow_approx_1d && !opt.exact)
            consider(Strategy::Approx1D);

        if (bestU >= GYRO_INF) {
            if (feats_.m <= 1) return Strategy::Rank1D;
            if (feats_.m >= 2) return Strategy::Fenwick2D;
            return Strategy::Rank1D;
        }

#ifdef GYRO_DEBUG
        const char* name = "?";
        switch (best) {
        case Strategy::Rank1D: name = "Rank1D"; break;
        case Strategy::Fenwick2D: name = "Fenwick2D"; break;
        case Strategy::NestedOrProjection: name = "NestedOrProjection"; break;
        case Strategy::Approx1D: name = "Approx1D"; break;
        default: break;
        }
        std::fprintf(stderr, "[gyro] chosen=%s U=%.3g\n", name, bestU);
#endif
        return best;
    }

    Strategy gate() const {
        GyroOptions opt;
        opt.exact = true;
        opt.memory_pressure = feats_.memory_pressure;
        return gate(opt);
    }

    const GyroFeatures& features() const { return feats_; }
    const double* utilities() const { return U_; }

private:
    GyroFeatures feats_;
    double U_[static_cast<int>(Strategy::COUNT)] = {GYRO_INF, GYRO_INF, GYRO_INF, GYRO_INF};
};

inline void execute_gyro_rank_ex(const double* matrix_in,
                                 uint32_t n,
                                 uint32_t m,
                                 int32_t* ranks_out,
                                 int32_t* dom_out,
                                 const GyroOptions& opt) {
    if (n == 0 || m == 0) return;

    GyroController ctrl;
    ctrl.observe(matrix_in, n, m, opt.memory_pressure, opt.memory_budget_bytes);
    ctrl.striate(opt);
    Strategy strat = ctrl.gate(opt);

    switch (strat) {
    case Strategy::Rank1D:
        rank_1d(matrix_in, n, m, ranks_out);
        if (dom_out) std::fill(dom_out, dom_out + n, 0);
        break;
    case Strategy::Approx1D:
        rank_1d(matrix_in, n, m, ranks_out);
        if (dom_out) std::fill(dom_out, dom_out + n, 0);
        break;
    case Strategy::Fenwick2D:
        exact_rank_2d_fenwick(matrix_in, n, m, ranks_out, dom_out);
        break;
    case Strategy::NestedOrProjection:
        if (m >= 2)
            exact_rank_2d_fenwick(matrix_in, n, m, ranks_out, dom_out);
        else
            rank_1d(matrix_in, n, m, ranks_out);
        break;
    default:
        exact_rank_2d_fenwick(matrix_in, n, m, ranks_out, dom_out);
        break;
    }
}

inline void execute_gyro_rank(const double* matrix_in,
                              uint32_t n,
                              uint32_t m,
                              int32_t* ranks_out,
                              int32_t* dom_out = nullptr,
                              bool memory_pressure = false) {
    GyroOptions opt;
    opt.exact = true;
    opt.memory_pressure = memory_pressure;
    opt.allow_approx_1d = false;
    execute_gyro_rank_ex(matrix_in, n, m, ranks_out, dom_out, opt);
}

} // namespace gyro
