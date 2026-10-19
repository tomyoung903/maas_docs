#!/usr/bin/env python3
"""Build the static interview page. Run after editing content.json/questions.json."""
import hashlib
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'docs' / 'zhang-chao-interview'
OUT.mkdir(parents=True, exist_ok=True)
for asset in ('styles.css', 'app.js'):
    shutil.copy2(ROOT / asset, OUT / asset)
esc = lambda value: html.escape(str(value), quote=True)
content = json.loads((ROOT / 'content.json').read_text())
raw = json.loads((ROOT / 'questions.json').read_text())
source_questions = raw['questions'] if isinstance(raw, dict) else raw
anchors = {}
for project, section in enumerate(content['sections'], start=1):
    for index, excerpt in enumerate(section['excerpts']):
        assert excerpt['id'] not in anchors, 'duplicate excerpt anchor'
        anchors[excerpt['id']] = (project, index, section['title'], excerpt['text'])

questions = []
for number, q in enumerate(source_questions, start=1):
    assert q['anchorId'] in anchors, f"Unknown anchor: {q['anchorId']}"
    project, index, label, text = anchors[q['anchorId']]
    questions.append({**q, 'number': number, 'project': project, 'blockIndex': index,
        'projectLabel': label, 'claim': text, 'expectedAnswer': q.get('expected', []),
        'sources': [{'label': s.get('title', s.get('label', '参考资料')), 'url': s['url']}
            for s in q.get('sources', [])]})
assert len({q['id'] for q in questions}) == len(questions), 'duplicate question IDs'
by_anchor = {anchor: [q for q in questions if q['anchorId'] == anchor] for anchor in anchors}
assert all(by_anchor.values()), 'every excerpt needs at least one question pin'

paper = []
for project, section in enumerate(content['sections'], start=1):
    paper.append(f'<article class="project" id="project-{project}" aria-labelledby="project-title-{project}">')
    paper.append(f'<h2 class="section-heading" id="project-title-{project}">{esc(section["title"])}</h2>')
    if section.get('subtitle'):
        paper.append(f'<header class="project-heading"><h2>{esc(section["subtitle"])}</h2></header>')
    paper.append('<ol class="experience">')
    for excerpt in section['excerpts']:
        pins = ''.join(f'<button class="question-pin" type="button" data-question="{esc(q["id"])}" aria-haspopup="dialog" aria-controls="question-dialog" aria-label="问题 {q["number"]}：{esc(q["title"])}">{q["number"]}</button>' for q in by_anchor[excerpt['id']])
        paper.append(f'<li value="{excerpt["number"]}" data-anchor="{esc(excerpt["id"])}">{esc(excerpt["text"])}<span class="mark-cluster">{pins}</span></li>')
    paper.append('</ol></article>')

# Keep this entirely static: no build/runtime CDN and no external fonts.
(OUT/'data.js').write_text('window.INTERVIEW_QUESTIONS = ' + json.dumps(questions, ensure_ascii=False, indent=2) + ';\n')
hash_for = lambda name: hashlib.sha256((OUT/name).read_bytes()).hexdigest()[:12]
page = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light"><meta name="description" content="张超简历中划线内容与对应的面试问题。"><title>张超 · 面试准备</title><link rel="stylesheet" href="styles.css?v=CSSHASH"></head>
<body><header class="toolbar"><a class="brand" href="#resume">张超 <span>／ 面试准备</span></a><p>点击编号，查看问题与参考答案</p><div class="toolbar-actions"><span id="pin-count">COUNT 个问题 · 5 处简历节选</span><button type="button" id="toggle-pins" aria-pressed="true">隐藏问题标记</button><button type="button" id="add-question" aria-haspopup="dialog" aria-controls="question-editor">添加问题</button></div></header>
<p id="custom-storage-warning" class="storage-warning" role="status" aria-live="polite" hidden></p>
<main class="paper" id="resume"><div class="resume-heading"><h1>张超</h1><p>简历节选</p><p class="paper-subtitle">仅保留所标注的项目经历与个人总结，编号沿用原简历。</p></div>PAPER<footer class="paper-footer">简历内容为候选人的自述；参考答案是面试核验要点，不代表已核实的个人贡献。自定义问题仅保存在当前浏览器。</footer></main>
<dialog id="question-dialog" aria-labelledby="question-title" aria-describedby="question-text"><div class="dialog-inner"><header class="dialog-header"><div><span id="question-project"></span><span id="question-index"></span></div><button type="button" id="close-dialog" aria-label="关闭问题">×</button></header><h2 id="question-title"></h2><blockquote id="source-claim"></blockquote><p class="label">面试问题</p><p id="question-text"></p><button type="button" id="edit-question" aria-haspopup="dialog" aria-controls="question-editor" hidden>编辑问题</button><button type="button" id="answers-toggle" aria-expanded="false" aria-controls="expected-answer">展开参考答案</button><section id="expected-answer" hidden><p class="label">参考答案 · 核验要点</p><p class="reference-note">用于核对回答，请结合候选人本人的代码、配置或脱敏记录判断。</p><ul id="answer-checkpoints"></ul><div id="judgement-block"><p class="label">如何判断</p><p id="judgement"></p></div><div id="evidence-block"><p class="label">请他提供的证据</p><p id="evidence"></p></div><div id="followup-block"><p class="label">可选追问</p><p id="followup"></p></div><div id="interviewer-hint-block"><p class="label">面试官提示</p><p id="interviewer-hint"></p></div><div id="study-sources-block"><p class="label">你的已有学习笔记</p><div id="question-study-sources"></div></div><div id="technical-sources-block"><p class="label">技术参考</p><div id="question-sources"></div></div></section><footer class="dialog-nav"><button type="button" id="prev-question">← 上一个</button><button type="button" id="next-question">下一个 →</button></footer></div></dialog>
<dialog id="question-editor" aria-labelledby="question-editor-title" aria-describedby="editor-storage-note"><form id="question-editor-form"><header class="dialog-header"><h2 id="question-editor-title">添加问题</h2><button type="button" id="editor-close" aria-label="关闭问题编辑器">×</button></header><p id="editor-storage-note" class="editor-note">自定义问题仅保存在当前浏览器。</p><div class="editor-field-row"><div class="editor-field"><label for="editor-project">章节</label><select id="editor-project" name="project"><option value="1">项目经历 · 腾讯项目</option><option value="2">个人总结</option></select></div><div class="editor-field"><label for="editor-paragraph">关联简历段落</label><select id="editor-paragraph" name="paragraph" aria-describedby="editor-quote" required></select></div></div><blockquote id="editor-quote" aria-live="polite"></blockquote><div class="editor-field"><label for="editor-question">面试问题 <span class="field-requirement">必填</span></label><textarea id="editor-question" name="question" required maxlength="5000" rows="4" placeholder="写下你想核验的问题……"></textarea></div><div class="editor-field"><label for="editor-answer">参考答案 <span class="field-requirement">选填</span></label><textarea id="editor-answer" name="answer" maxlength="10000" rows="4" placeholder="记录期望回答或核验要点……"></textarea></div><footer class="editor-actions"><button type="button" id="editor-cancel">取消</button><button type="submit" id="editor-save">保存问题</button></footer></form></dialog>
<script src="data.js?v=DATAHASH"></script><script src="app.js?v=APPHASH"></script>
  <script defer src="../assets/maas-annotator.js" data-maas-annotator data-page-key="/zhang-chao-interview/"></script>
</body></html>'''
page = page.replace('CSSHASH', hash_for('styles.css')).replace('DATAHASH', hash_for('data.js')).replace('APPHASH', hash_for('app.js')).replace('PAPER', ''.join(paper)).replace('COUNT', str(len(questions)))
(OUT/'index.html').write_text(page)
print(f'Built {len(questions)} questions across {len(anchors)} excerpts.')
