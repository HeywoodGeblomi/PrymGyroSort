/**
 * PrymGyroSort zero-copy binding — GyroRank v0.2
 * Requires C-contiguous float64 matrix with shape (N, 2). No silent copy.
 * GYR-FIX-001 F3: rank_fenwick_ref exports exact_rank_2d_fenwick for identity oracle.
 */
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include "gyro_rank.hpp"
#include <cstdint>
#include <stdexcept>

namespace py = pybind11;

namespace {

void require_c_contiguous_matrix(const py::buffer_info& mbuf) {
    if (mbuf.ndim != 2)
        throw std::invalid_argument("matrix must be 2-D (N, M)");
    if (mbuf.shape[1] != 2)
        throw std::invalid_argument(
            "matrix must have shape (N, 2); M!=2 is not supported on the fast path");
    const ssize_t item = static_cast<ssize_t>(mbuf.itemsize);
    if (item != static_cast<ssize_t>(sizeof(double)))
        throw std::invalid_argument("matrix must be float64");
    if (mbuf.strides[1] != item)
        throw std::invalid_argument(
            "matrix must be C-contiguous float64 (use np.ascontiguousarray); refusing silent copy");
    if (mbuf.shape[0] > 1 && mbuf.strides[0] != item * mbuf.shape[1])
        throw std::invalid_argument(
            "matrix must be C-contiguous float64 (row-major); refusing silent copy");
}

void rank_numpy(py::array matrix, py::array ranks, bool memory_pressure) {
    if (!py::isinstance<py::array_t<double>>(matrix))
        throw std::invalid_argument("matrix must be dtype float64");
    if (!py::isinstance<py::array_t<int32_t>>(ranks))
        throw std::invalid_argument("ranks must be dtype int32");

    auto mbuf = matrix.request();
    auto rbuf = ranks.request();
    require_c_contiguous_matrix(mbuf);

    const auto n = static_cast<uint32_t>(mbuf.shape[0]);
    const auto m = static_cast<uint32_t>(mbuf.shape[1]);

    if (rbuf.ndim != 1 || static_cast<uint32_t>(rbuf.shape[0]) != n)
        throw std::invalid_argument("ranks must be 1-D int32 of length N");
    if (rbuf.itemsize != static_cast<ssize_t>(sizeof(int32_t)) ||
        rbuf.strides[0] != static_cast<ssize_t>(sizeof(int32_t)))
        throw std::invalid_argument("ranks must be C-contiguous int32");

    if (n == 0) return;
    if (mbuf.ptr == nullptr || rbuf.ptr == nullptr)
        throw std::invalid_argument("null buffer");

    gyro::execute_gyro_rank(static_cast<const double*>(mbuf.ptr), n, m,
                            static_cast<int32_t*>(rbuf.ptr), nullptr, memory_pressure);
}

py::dict rank_numpy_report(py::array matrix, py::array ranks, bool memory_pressure) {
    auto mbuf = matrix.request();
    require_c_contiguous_matrix(mbuf);
    const auto n = static_cast<uint32_t>(mbuf.shape[0]);
    const auto m = static_cast<uint32_t>(mbuf.shape[1]);
    rank_numpy(matrix, ranks, memory_pressure);

    gyro::GyroOptions opt;
    opt.exact = true;
    opt.memory_pressure = memory_pressure;
    opt.allow_approx_1d = false;

    gyro::GyroController ctrl;
    ctrl.observe(static_cast<const double*>(mbuf.ptr), n, m, memory_pressure, 0);
    ctrl.striate(opt);
    const auto strat = ctrl.gate(opt);

    const char* strat_name = "Fenwick2D";
    switch (strat) {
    case gyro::Strategy::Rank1D: strat_name = "Rank1D"; break;
    case gyro::Strategy::Fenwick2D: strat_name = "Fenwick2D"; break;
    case gyro::Strategy::NestedOrProjection: strat_name = "NestedOrProjection"; break;
    case gyro::Strategy::Approx1D: strat_name = "Approx1D"; break;
    default: break;
    }

    py::dict out;
    out["n"] = n;
    out["m"] = m;
    out["memory_pressure"] = memory_pressure;
    out["strategy"] = strat_name;
    out["zerocopy"] = true;
    out["c_contiguous_required"] = true;
    out["shape_required"] = "(N, 2)";
    out["scope"] = "path-local / execution-sieve only; promote_ready=false";
    return out;
}

void rank_fenwick_ref(py::array matrix, py::array ranks) {
    if (!py::isinstance<py::array_t<double>>(matrix))
        throw std::invalid_argument("matrix must be dtype float64");
    if (!py::isinstance<py::array_t<int32_t>>(ranks))
        throw std::invalid_argument("ranks must be dtype int32");
    auto mbuf = matrix.request();
    auto rbuf = ranks.request();
    require_c_contiguous_matrix(mbuf);
    const auto n = static_cast<uint32_t>(mbuf.shape[0]);
    const auto m = static_cast<uint32_t>(mbuf.shape[1]);
    if (rbuf.ndim != 1 || static_cast<uint32_t>(rbuf.shape[0]) != n)
        throw std::invalid_argument("ranks must be 1-D int32 of length N");
    if (n == 0) return;
    gyro::exact_rank_2d_fenwick(static_cast<const double*>(mbuf.ptr), n, m,
                                static_cast<int32_t*>(rbuf.ptr), nullptr);
}

}  // namespace

PYBIND11_MODULE(prym_gyro_native, m) {
    m.doc() = "PrymGyroSort zero-copy binding (GyroRank v0.2). Requires C-contiguous (N,2) float64.";
    m.def("rank", &rank_numpy, py::arg("matrix"), py::arg("ranks"),
          py::arg("memory_pressure") = false);
    m.def("rank_report", &rank_numpy_report, py::arg("matrix"), py::arg("ranks"),
          py::arg("memory_pressure") = false);
    m.def("rank_fenwick_ref", &rank_fenwick_ref, py::arg("matrix"), py::arg("ranks"),
          "F3: exact_rank_2d_fenwick only — identity oracle");
}
