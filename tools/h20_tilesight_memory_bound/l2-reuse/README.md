# Memory-bound GEMM L2 reuse explorer

This explorer uses the page's saved M=16, N=79,872, K=8,192 FP16 plan, with a 16 × 128 × 64 tile, 60 MiB L2, 78 SMs and four resident CTAs per SM. The full trace walks all 160,368 declared A/B/C accesses in two modeled waves. It does not run a GPU kernel or sample a subset of accesses.

Reproduce using the TileSight checkout recorded in `docs/h20-tilesight-memory-bound/data/l2-reuse-model.json`:

```sh
PYTHONPATH=/path/to/TileSight CUDA_VISIBLE_DEVICES='' \
  python3 tools/h20_tilesight_memory_bound/l2-reuse/generate_data.py \
  --plan docs/h20-tilesight-memory-bound/data/plan.json \
  --output-dir /path/to/trace-output
python3 tools/h20_tilesight_memory_bound/l2-reuse/build_fragment.py \
  --data-dir /path/to/trace-output
python3 /path/to/visualize/scripts/render.py \
  tools/h20_tilesight_memory_bound/l2-reuse/fragment.html \
  docs/h20-tilesight-memory-bound/assets/l2-reuse.html --force
cp /path/to/trace-output/metadata.json \
  docs/h20-tilesight-memory-bound/data/l2-reuse-model.json
python3 tools/h20_tilesight_memory_bound/build.py
```

The generator observes TileSight's weighted LRU stack accesses and applies the same SDCM probability function as the model. It verifies every operand identity, the total event count, and the aggregate probabilities against `build_cache_view`. Probabilities are stored as little-endian float32, indexed by `(k * 624 + n) * 2 + operand`, with A=0 and B=1.

All K slices have the same predicted reuse pattern. In each slice, A misses at output columns 0 and 312 and hits in the other 622. B is a first access everywhere. The 24-column display wraps one logical row; it does not change the task grid. Hit probabilities are model outputs, not measured counters or guarantees about physical CTA execution order.

The existing timing calculation remains based on its archived sampled cache result. This addition exposes the full cache trace separately rather than rewriting the original timing evidence.
