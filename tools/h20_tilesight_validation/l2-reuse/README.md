# L2 reuse explorer source

`fragment.html` is the original interactive 32 × 32 × 64 visualization. It embeds
all 131,072 A/B probability values, obtained by fully expanding the modeled
GEMM access sequence. It does not sample accesses or read hardware counters.

`generate_data.py` captures the probabilities from TileSight's full trace. Run
it with the TileSight checkout at commit
`6673bc3941d23572caad5d25473c9f129c3f000a` on `PYTHONPATH` to produce the data
and provenance. It performs CPU-only modeling.

The deployed `docs/h20-tilesight-gemm-validation/assets/l2-reuse.html` is an
export of the fragment using the visualize skill's `scripts/render.py`. It
retains the sandboxed iframe, Content Security Policy, and browser-local state
storage supplied by the export wrapper. The wrapper is an embedded asset;
annotations belong to the enclosing documentation page.

To re-export after a fragment change, run the installed visualize skill's
renderer with the fragment as the source and the deployed asset as the
destination, with `--force`. Then run `tools/h20_tilesight_validation/build.py`.
The page generator inserts the asset's content hash into its URL and updates
the page checksum manifest.
