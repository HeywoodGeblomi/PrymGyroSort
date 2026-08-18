# Path A — Isolated Visualization Profile

**Status:** implemented as read-only sidecar  
**Core impact:** none — never touches C++ build, Dockerfile builder stage, or ranking kernel

## Goal

Render clean ASCII and web-based Pareto frontiers from ranking outputs under
`work/` without polluting the core compilation runtime.

## Inputs (produced by the ranking pipeline)

| File | Role |
|------|------|
| `matrix.bin` | N×2 float64 objectives (obj0, obj1) |
| `ranks.bin` | N int32 weak-dominance ranks |
| `is_good.npy` | optional boolean anchors |

## Outputs

| File | Description |
|------|-------------|
| `pareto_ascii.txt` | Monospace scatter (top-left = best) |
| `pareto.html` | Self-contained HTML + inline SVG (zero external JS/CSS) |

## Usage

### Local (no Docker)

```bash
# after ranking has written work/
python3 python/viz_pareto.py --dir work --format both
# open work/pareto.html in a browser
```

### Docker Compose profile (core image untouched)

```bash
# 1. run the ranking service as usual (writes ./work)
docker compose run --rm prym-gyro-rank

# 2. render Pareto without rebuilding anything
docker compose --profile viz run --rm viz
```

The `viz` service uses a stock `python:3.11-slim` image, mounts `./work` and
`./python` read-only, installs numpy only inside that ephemeral container, and
exits. The multi-stage ranking Dockerfile is never invoked.

## Design rules

1. **Read-only** on ranking artifacts.
2. **No new dependencies** on the core image / builder stage.
3. **No matplotlib / plotly / bokeh** — ASCII + inline SVG only.
4. Honesty note embedded in HTML footer: path-local ranks only.

## Non-claims

Visualization of path-local geometric ranks. Does not claim global Lyapunov
exponents or ownership of 8/5. See root `NON_CLAIMS.md`.
