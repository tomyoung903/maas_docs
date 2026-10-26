# 孙世牛面试准备页

只展示简历第一项核心项目「推理框架开发与模型部署」：保留项目日期、角色、背景、8 条一级 bullet 和 5 条嵌套 bullet。第二项 MaxKB / RAG 项目及个人联系方式、年龄、教育和工作履历未纳入。

从仓库根目录重建：

```bash
python3 tools/sun_shiniu_interview/build.py
```

源数据为 `content.json` 和 `questions.json`，输出仅写入 `docs/sun-shiniu-interview/`。页面沿用陈琦面试准备页的布局、添加/编辑问题和答案展开功能，初始问题列表为空。

每个一级或嵌套 bullet 都有独立稳定的 `id`；编辑器依原层级标为第 1、6.1、6.2 项等，引用时只取该 bullet 自身文字，避免重复包含子项。问题通过这些 ID 关联，浏览器存储键为 `sun-shiniu-interview:custom-questions:v1`，批注键为 `/sun-shiniu-interview/`，与其他候选人互不影响。

原文只去掉 PDF 水印和换行，未重新措辞或核实候选人的技术/性能主张。PDF 末项原有的 `23%–65%ß。` 按原文保留；`PP2/TP8` 经 PDF 页面目视核对，排除了布局提取中混入的水印数字。

共享批注脚本由 `docs/assets/maas-annotator.js` 提供。此目录不修改共享资源或首页。
