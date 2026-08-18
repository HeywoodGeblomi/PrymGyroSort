# PrymGyroSort v0.1.1-prototype — multi-stage container
# Array structure: prym-eigenform-pipeline-d12 geometric points
# Sorter kernel: GyroRank (weak-dominance multi-obj ranking)
#
# Build: docker build -t prym-gyro-sort:0.1.1 .
# Run:   docker run --rm -e N=4096 prym-gyro-sort:0.1.1

FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        g++ make python3 python3-numpy curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY . .

RUN if [ ! -f cpp/include/gyro_rank.hpp ]; then \
      mkdir -p cpp/include && \
      curl -fsSL https://raw.githubusercontent.com/HeywoodGeblomi/GyroRank/main/include/gyro_rank.hpp \
        -o cpp/include/gyro_rank.hpp ; \
    fi

RUN curl -fsSL https://raw.githubusercontent.com/orlp/pdqsort/master/pdqsort.h \
      -o cpp/include/pdqsort.h || true

RUN g++ -O3 -std=c++17 -Icpp/include cpp/rank_driver.cpp -o /usr/local/bin/rank_driver

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-numpy libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/bin/rank_driver /usr/local/bin/rank_driver
COPY python/ /opt/prym-gyro/python/
COPY NON_CLAIMS.md README.md LICENSE /opt/prym-gyro/
COPY entrypoint.sh /opt/prym-gyro/entrypoint.sh

RUN chmod +x /opt/prym-gyro/entrypoint.sh \
 && useradd -m -u 10001 prymgyro

USER prymgyro
WORKDIR /tmp

ENV N=4096 SEED=728 N_GOOD=48

ENTRYPOINT ["/opt/prym-gyro/entrypoint.sh"]
