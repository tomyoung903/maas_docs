# MaaS Docs

Static documentation for MaaS serving/math notes.

## GitHub Pages Layout

This repo is intended to publish through GitHub Pages with:

- Source: `main`
- Folder: `/docs`

After Pages is enabled, the expected URLs are:

- `https://<owner>.github.io/maas_docs/`
- `https://<owner>.github.io/maas_docs/kimi25-flops/`

## Current Pack

- `docs/kimi25-flops/index.html`
- `docs/kimi25-flops/kimi25_full_model_architecture.html`
- `docs/kimi25-flops/kimi25_mla_attention_tutorial.html`
- `docs/kimi25-flops/kimi25_linear_flops_constant.html`
- `docs/kimi25-flops/kimi25_linear_flops_constant.notebook.html`
- `docs/kimi25-flops/kimi25_attention_scan_flops_constant.html`
- `docs/kimi25-flops/kimi25_attention_scan_flops_constant.notebook.html`

## Refresh From Source

From `/home/tom/sglang2`:

```bash
python3 z_local/benchserving/mfu_metrics/build_kimi25_flops_static_docs.py
rsync -a --delete z_local/benchserving/mfu_metrics/publish/kimi25-flops/ ~/maas_docs/docs/kimi25-flops/
touch ~/maas_docs/docs/.nojekyll
```

Then review, commit, and push.
