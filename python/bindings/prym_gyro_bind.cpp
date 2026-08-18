/**
 * PrymGyroSort — Phase 1 zero-copy pybind11 sidecar
 * Core gyro_rank.hpp is the source of truth (read-only include).
 * Honesty: ranking kernel only. No alpha / spectral claims.
 */
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

#include "gyro_rank.hpp"

#include <cstdint>
#include <stdexcept>

namespace py = pybind11;

namespace {

void rank_numpy(py::array_t<double, py::array::c_style | py::array::forcecast> matrix,
                py::array_t<int32_t, py::array::c_style | py::array::forcecast> ranks,
                bool memory_pressure) {
    auto mbuf = matrix.request();
    auto rbuf = ranks.request();

    if (mbuf.ndim != 2) {
        throw std::invalid_argument("matrix must be 2-D (N, M)");
    }
    if (mbuf.shape[1] < 1) {
        throw std::invalid_argument("matrix M must be >= 1");
    }
    const auto n = static_cast<uint32_t>(mbuf.shape[0]);
    const auto m = static_cast<uint32_t>(mbuf.shape[1]);

    if (rbuf.ndim != 1 || static_cast<uint32_t>(rbuf.shape[0]) != n) {
        throw std::invalid_argument("ranks must be 1-D int32 of length N");
    }
    if (n == 0) return;

    const double* mat = static_cast<const double*>(mbuf.ptr);
    int32_t* rk = static_cast<int32_t*>(rbuf.ptr);
    gyro::execute_gyro_rank(mat, n, m, rk, /*dom_out=*/nullptr, memory_pressure);
}

py::dict rank_numpy_report(
    py::array_t<double, py::array::c_style | py::array::forcecast> matrix,
    py::array_t<int32_t, py::array::c_style | py::array::forcecast> ranks,
    bool memory_pressure) {
    auto mbuf = matrix.request();
    if (mbuf.ndim != 2) {
        throw std::invalid_argument("matrix must be 2-D (N, M)");
    }
    const auto n = static_cast<uint32_t>(mbuf.shape[0]);
    const auto m = static_cast<uint32_t>(mbuf.shape[1]);

    rank_numpy(matrix, ranks, memory_pressure);

    gyro::GyroController ctrl;
    ctrl.observe(static_cast<const double*>(mbuf.ptr), n, m, memory_pressure);
    const auto strat = ctrl.gate();
    const auto& f = ctrl.features();

    const char* strat_name = "Unknown";
    switch (strat) {
    case gyro::Strategy::Insertion1D: strat_name = "Insertion1D"; break;
    case gyro::Strategy::Fenwick2D:   strat_name = "Fenwick2D"; break;
    case gyro::Strategy::LowAux2D:    strat_name = "LowAux2D"; break;
    case gyro::Strategy::NestedOrProjection: strat_name = "NestedOrProjection"; break;
    }

    py::dict out;
    out["n"] = n;
    out["m"] = m;
    out["memory_pressure"] = memory_pressure;
    out["strategy"] = strat_name;
    out["sortedness_0"] = f.sortedness_0;
    out["sortedness_1"] = f.sortedness_1;
    out["density_product"] = f.density_product;
    out["zerocopy"] = true;
    out["scope"] = "path-local / execution-sieve only; promote_ready=false";
    return out;
}

}  // namespace

PYBIND11_MODULE(prym_gyro_native, m) {
    m.doc() = "PrymGyroSort Phase-1 zero-copy binding (GyroRank kernel)";

    m.def("rank", &rank_numpy,
          py::arg("matrix"),
          py::arg("ranks"),
          py::arg("memory_pressure") = false);

    m.def("rank_report", &rank_numpy_report,
          py::arg("matrix"),
          py::arg("ranks"),
          py::arg("memory_pressure") = false);
}
