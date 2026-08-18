# PrymGyroSort — multi-stage production image
# Portable ISA default (no -march=native). Optional MARCH=x86-64-v3.
# No false OpenMP. Non-root quantoperator. promote_ready=false.

FROM python:3.11-slim-bookworm AS builder
ARG MARCH=
RUN apt-get update && apt-get install -y --no-install-recommends \
        g++ make python3-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY cpp/include/ /build/cpp/include/
COPY python/bindings/ /build/python/bindings/
RUN pip install --no-cache-dir pybind11 numpy setuptools wheel
WORKDIR /build/python/bindings
RUN if [ -n "$MARCH" ]; then \
      g++ -O3 -shared -std=c++17 -fPIC -fvisibility=hidden -march=${MARCH} \
        $(python3 -m pybind11 --includes) -I/build/cpp/include \
        $(python3 -c "import numpy; print('-I'+numpy.get_include())") \
        prym_gyro_bind.cpp -o prym_gyro_native.so ; \
    else \
      g++ -O3 -shared -std=c++17 -fPIC -fvisibility=hidden \
        $(python3 -m pybind11 --includes) -I/build/cpp/include \
        $(python3 -c "import numpy; print('-I'+numpy.get_include())") \
        prym_gyro_bind.cpp -o prym_gyro_native.so ; \
    fi
WORKDIR /build
COPY cpp/ /build/cpp/
RUN g++ -O3 -std=c++17 -Icpp/include cpp/rank_driver.cpp -o /build/rank_driver

FROM python:3.11-slim-bookworm AS runner
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 10001 quantgroup \
    && useradd -u 10001 -g quantgroup -m -s /usr/sbin/nologin quantoperator
WORKDIR /app
RUN pip install --no-cache-dir numpy
COPY --from=builder /build/python/bindings/prym_gyro_native.so /app/python/bindings/
COPY --from=builder /build/rank_driver /usr/local/bin/rank_driver
COPY python/ /app/python/
COPY NON_CLAIMS.md README.md LICENSE /app/
RUN mkdir -p /app/work /app/docs /app/python/bindings \
    && chown -R quantoperator:quantgroup /app \
    && chmod +x /usr/local/bin/rank_driver
ENV PYTHONPATH=/app/python:/app/python/bindings
USER quantoperator
WORKDIR /app/work
ENTRYPOINT ["python3", "/app/python/prym_sieve_cli.py"]
CMD ["--n", "4096", "--seed", "42"]
