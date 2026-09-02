# MaaS Docs

Static documentation for MaaS serving/math notes.

## Layout

This repo publishes static HTML through GitHub Pages with:

- Source: `main`
- Folder: `/docs`

Folder convention:

- `docs/index.html`: public catalog page.
- `docs/<pack-slug>/index.html`: pack overview.
- `docs/<pack-slug>/<topic>.html`: stable topic pages.
- `docs/assets/maas-annotator.js`: shared browser-local drawing layer.
- `docs/.nojekyll`: keeps GitHub Pages from filtering generated files.

Expected public URLs:

- `https://tomyoung903.github.io/maas_docs/`
- `https://tomyoung903.github.io/maas_docs/glm52-flops/`
- `https://tomyoung903.github.io/maas_docs/kimi25-flops/`

## Current Packs

### GLM-5.2 FLOPs

- `docs/glm52-flops/index.html`
- `docs/glm52-flops/glm52_architecture.html`
- `docs/glm52-flops/glm52_linear_flops_per_token.html`
- `docs/glm52-flops/glm52_attention_scan_flops_per_token.html`

### Kimi K2.5 FLOPs

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
python3 z_local/benchserving/mfu_metrics/build_glm52_flops_static_docs.py
rsync -a --delete z_local/benchserving/mfu_metrics/publish/glm52-flops/ ~/maas_docs/docs/glm52-flops/

python3 z_local/benchserving/mfu_metrics/build_kimi25_flops_static_docs.py
rsync -a --delete z_local/benchserving/mfu_metrics/publish/kimi25-flops/ ~/maas_docs/docs/kimi25-flops/

touch ~/maas_docs/docs/.nojekyll

cd ~/maas_docs
python3 tools/inject_maas_annotator.py
python3 tools/inject_maas_annotator.py --check
```

Then review, commit, and push.

## Page Annotations

Every published HTML page loads the shared annotator. The bottom-right pencil opens pen, highlighter, arrow, text, eraser, undo/redo, visibility, import/export, and clear controls. For text, select **Add text**, click the page, type, then use the button or Ctrl/Command+Enter to save.

Annotations are stored per page in the current browser profile's `localStorage`; they are not uploaded to GitHub Pages. Use JSON export/import to move or share a set of annotations. Run `tools/inject_maas_annotator.py` after adding or regenerating HTML files.
