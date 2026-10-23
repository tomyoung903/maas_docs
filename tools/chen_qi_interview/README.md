# 陈琦（Jason）面试准备页

从 `content.json` 和 `questions.json` 生成两项项目经历与对应问题。

```bash
python3 tools/chen_qi_interview/build.py
```

只写入 `docs/chen-qi-interview/`。每节支持可选的 `context` 文本（日期、职责或项目背景），放在副标题之后。问题默认折叠答案，支持前后切换、隐藏标记和浏览器本地自定义问题；存储命名空间为 `chen-qi-interview`。沿用 `docs/assets/maas-annotator.js` 批注工具。

初始不预填问题。用户在页面中按项目段落添加自己的问题，新问题从 1 开始编号；已有浏览器问题保持原编号。

项目原文按 PDF 保留顺序，每项四个原始 bullet，不合并或重排。自定义问题用稳定段落 ID 关联，以免展示结构调整后错位。
