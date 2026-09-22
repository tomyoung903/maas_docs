"""Render a verified Kimi K3 ledger using the original GLM-5.2 tree UI.

No model arithmetic belongs here. The caller owns all operation counts,
architecture statements, sources, formulas, and accounting scope.

Content fields are trusted author-controlled HTML: lead, card value, node title,
role, repeat, input, output, state, formula, note, auxiliary, source/evidence,
intro_html, section html, and footer_html. Titles, labels, links, IDs, and other
attributes are escaped where appropriate. All parents start expanded, exactly as
in the requested reference page.
"""
from __future__ import annotations

from decimal import Decimal
from html import escape
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PAGE_KEY = "/kimi-k3-flops/kimi_k3_100k_prefill_execution_tree.html"
REFERENCE_URL = (
    "https://tomyoung903.github.io/maas_docs/"
    "glm52-flops/glm52_100k_prefill_execution_tree.html"
)


def format_flops(flops: int) -> str:
    """Format raw FLOPs in the reference's units with four significant figures."""
    if isinstance(flops, bool) or not isinstance(flops, int) or flops < 0:
        raise ValueError("flops must be a non-negative exact integer")
    if flops == 0:
        return "0 FLOP"
    for threshold, scale, unit in (
        (10**13, 10**15, "PFLOP"),
        (10**12, 10**12, "TFLOP"),
        (10**9, 10**9, "GFLOP"),
        (10**6, 10**6, "MFLOP"),
        (10**3, 10**3, "KFLOP"),
        (1, 1, "FLOP"),
    ):
        if flops >= threshold:
            value = Decimal(flops) / Decimal(scale)
            places = max(0, 3 - value.adjusted())
            return f"{value:.{places}f} {unit}"
    raise AssertionError("unreachable")


def _text(value: Any) -> str:
    return escape(str(value), quote=True)


def _html(value: Any) -> str:
    return str(value) if value is not None else ""


def _render_tree(node: dict[str, Any]) -> str:
    next_group = 0

    def render(item: dict[str, Any], *, root: bool = False) -> str:
        nonlocal next_group
        children = item.get("children") or []
        step = _text(item["id"])
        kind = str(item.get("kind") or ("group" if children else "leaf"))
        # Accept both the schema's short branch names and exact CSS classes.
        kind = {"refresh": "branch-refresh", "reuse": "branch-reuse",
                "dense": "branch-dense", "moe": "branch-moe"}.get(kind, kind)
        allowed = {"group", "leaf", "branch-refresh", "branch-reuse",
                   "branch-dense", "branch-moe"}
        if kind not in allowed:
            raise ValueError(f"Unsupported flow kind: {kind!r}")
        classes = f"flow-step {kind}" + (" has-children" if children else "")
        toggle = ""
        children_id = ""
        if children:
            next_group += 1
            children_id = f"flow-children-{next_group}"
            toggle = (
                '<button type="button" class="flow-toggle" aria-expanded="true" '
                f'aria-controls="{children_id}" '
                f'aria-label="Collapse child modules under step {step}" '
                f'data-step="{step}" title="Collapse child modules">'
                '<span class="flow-toggle-icon expanded" aria-hidden="true">&#9662;</span>'
                '<span class="flow-toggle-icon collapsed" aria-hidden="true">&#9656;</span>'
                '</button>'
            )
            if root:
                toggle = ('<span class="flow-toggle-prompt">' + toggle +
                          '<span class="flow-toggle-hint">Click to expand / collapse</span></span>')
        repeat = (f'<span class="repeat-badge">{_html(item["repeat"])}</span>'
                  if item.get("repeat") else "")
        raw = item["flops"]
        formatted = format_flops(raw)
        flop_parts = [
            '<span class="flow-label">100K prefill FLOPs</span>',
            f'<span class="flop-value" title="{raw:,} FLOP exactly" data-flops="{raw}">{formatted}</span>',
        ]
        auxiliary = _html(item.get("auxiliary"))
        if auxiliary and raw == 0:
            flop_parts.append('<span class="flop-status">Non-FLOP work</span>')
        for key, cls in (("formula", "flop-formula"), ("note", "flop-note")):
            if item.get(key):
                flop_parts.append(f'<span class="{cls}">{_html(item[key])}</span>')
        if auxiliary:
            flop_parts.append(f'<span class="flop-note">{auxiliary}</span>')
        source = item.get("source") or item.get("evidence")
        if source:
            flop_parts.append(f'<span class="flop-note">{_html(source)}</span>')
        # Optional caller-owned display blocks; never infer precision or totals.
        if item.get("extra_flops_html"):
            flop_parts.append(_html(item["extra_flops_html"]))
        body = f'''<li class="{classes}">
  <div class="flow-row">
    <div class="flow-main">
      <div class="flow-heading">
        {toggle}<span class="flow-step-id">{step}</span>
        <span class="flow-title-wrap"><span class="flow-title">{_html(item["title"])}</span><span class="flow-role">{_html(item.get("role", ""))}</span>{repeat}</span>
      </div>
    </div>
    <div class="flow-io"><span class="flow-label">Tensor flow</span>{_html(item.get("input", ""))}<span class="flow-arrow" aria-hidden="true">&darr;</span>{_html(item.get("output", ""))}</div>
    <div class="flow-state"><span class="flow-label">Logical parameter state</span>{_html(item.get("state", ""))}</div>
    <div class="flow-flops">{"".join(flop_parts)}</div>
  </div>
'''
        if children:
            body += (f'<ol id="{children_id}" class="flow-children">' +
                     "".join(render(child) for child in children) + '</ol>\n')
        return body + '</li>'

    return ('<ol id="execution-flow-tree" class="flow-tree" '
            'aria-label="Logical 100K prefill execution tree with FLOP accounting">' +
            render(node, root=True) + '</ol>')


def render_report(report: dict[str, Any]) -> str:
    """Return one self-contained static HTML page in the original reference UI."""
    style = (HERE / "reference-style.css").read_text(encoding="utf-8")
    script = (HERE / "reference-interactions.js").read_text(encoding="utf-8")
    title = _text(report["title"])
    canonical = _text(report["canonical"])
    nav = "".join(f'<a href="{_text(link["href"])}">{_text(link["label"])}</a>'
                  for link in report.get("nav", []))
    overview = "\n".join(
        f'<a class="depth-{int(link.get("depth", 1))}" href="{_text(link["href"])}">{_text(link["label"])}</a>'
        for link in report.get("overview", [])
    )
    cards = "".join(
        f'<section class="card"><div class="label">{_text(card["label"])}</div><div class="value">{_html(card["value"])}</div></section>'
        for card in report.get("cards", [])
    )
    legend = "".join(
        f'<span class="logic-badge {_text(item["kind"])}">{_text(item["label"])}</span>'
        for item in report.get("legend", [])
    )
    branch_legend = (
        '<div class="legend-group" aria-label="Layer-dependent branch colors">'
        '<span class="legend-group-label">Layer-dependent branches</span>' +
        legend + '</div>'
    ) if legend else ""
    sections = "\n".join(
        f'<h2 id="{_text(section["id"])}">{_text(section["title"])}</h2>\n{_html(section["html"])}'
        for section in report.get("sections", [])
    )
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Static technical documentation for {title}.">
  <meta name="robots" content="noindex">
  <link rel="canonical" href="{canonical}">
  <meta property="og:url" content="{canonical}">
  <title>{title}</title>
  <style>{style}</style>
</head>
<body>
<main>
<nav>{nav}</nav>
<div class="doc-shell">
<aside class="content-overview" aria-label="Content overview">
  <div class="content-overview-title">On this page</div>
  {overview}
</aside>
<article class="doc-content">
<h1>{title}</h1>
<p class="lead">{_html(report.get("lead", ""))}</p>
<div class="grid">{cards}</div>
<div class="tree-legend" aria-label="Execution tree color legend">
  <div class="legend-group" role="group" aria-label="Visible execution tree columns">
    <button type="button" class="logic-badge column-toggle tensor" data-column="io" aria-controls="execution-flow-tree" aria-label="Tensor input to tensor output column" aria-pressed="true">Tensor input &darr; tensor output</button>
    <button type="button" class="logic-badge column-toggle state" data-column="state" aria-controls="execution-flow-tree" aria-label="Logical parameter state column" aria-pressed="true">Logical parameter state</button>
    <button type="button" class="logic-badge column-toggle flops" data-column="flops" aria-controls="execution-flow-tree" aria-label="100K prefill FLOPs column" aria-pressed="true">100K prefill FLOPs</button>
  </div>
  {branch_legend}
</div>
<h2 id="execution-tree">Collapsed Execution Tree</h2>
{_html(report.get("intro_html", ""))}
{_render_tree(report["tree"])}
{sections}
<script>
{script}
</script>
<p class="footer">{_html(report.get("footer_html", ""))}</p>
</article>
</div>
</main>
<script defer src="../assets/maas-annotator.js" data-maas-annotator data-page-key="{PAGE_KEY}"></script>
</body>
</html>
'''
