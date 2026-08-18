# PrymGyroSort v0.1.3-finance — multi-stage container
# Multi-objective weak-dominance ranking filter (GyroRank kernel)
#
# Build:  docker build -t prym-gyro-sort:0.1.3 .
# Run:    docker run --rm -e N=4096 -e SEED=728 prym-gyro-sort:0.1.3
# Finance: docker run --rm -e MODE=finance -e N=4096 prym-gyro-sort:0.1.3

# ---- Builder ----
FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        g++ make curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY cpp/ cpp/

# Optional pdqsort (variadic GYRO_SORT handles lambdas)
RUN curl -fsSL https://raw.githubusercontent.com/orlp/pdqsort/master/pdqsort.h \
      -o cpp/include/pdqsort.h || true

RUN g++ -O3 -std=c++17 -Icpp/include cpp/rank_driver.cpp -o /usr/local/bin/rank_driver

# ---- Runtime ----
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-numpy libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/bin/rank_driver /usr/local/bin/rank_driver
COPY python/ /opt/prym-gyro/python/
COPY NON_CLAIMS.md README.md LICENSE /opt/prym-gyro/
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/rank_driver /usr/local/bin/entrypoint.sh \
 && useradd -m -u 10001 prym \
 && mkdir -p /work && chown prym:prym /work

USER prym
WORKDIR /work

ENV N=4096
ENV SEED=728
ENV MODE=synthetic
ENV MEMORY_PRESSURE=0

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
