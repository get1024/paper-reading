# Paper Reading

[打开论文索引](https://get1024.github.io/paper-reading/)

收录已读论文的中英对照批注和论证分析。索引支持搜索论文标题、简介和关键词，默认按标题 A–Z 排序，也可切换到 Z–A。

新增论文时，把 HTML 文件放在仓库根目录并推送到 `main`。GitHub Actions 会自动扫描这些文件，提取标题和简介，生成索引并发布到 GitHub Pages。删除或改名也会在下一次构建时反映到索引中。

标题优先使用 HTML 的第一个 `<h1>`，其次使用 `<title>`，最后使用文件名。简介和搜索关键词分别读取 `<meta name="description">` 与 `<meta name="keywords">`。封面优先使用 `assets/` 中与 HTML 文件同名的小写图片（如 `Vision-OPD.html` 对应 `assets/vision-opd.png`），否则提取第一张内嵌的 PNG、JPEG、WebP 或 GIF。

`papers.json` 保留了原有两篇论文的中文简介和主题标签，也可用于覆盖单篇论文的这两个字段。新 HTML 会自动收录，无需在此文件中登记。

页面模板位于 `templates/index.html`，生成脚本为 `scripts/generate-index.py`。本地预览使用 Python 3，无需安装依赖。

```sh
python3 scripts/generate-index.py
python3 -m http.server 8000 --directory dist
```

打开 `http://localhost:8000/`。`dist/` 是每次构建重新生成的发布目录，已加入 Git 忽略。

## 封面图来源

- Qianhao Yuan 等，《Vision-OPD》，[arXiv v4，图 4](https://arxiv.org/abs/2605.18740v4)。
- Lai Wei 等，《Zooming without Zooming》，[arXiv v2，图 2](https://arxiv.org/abs/2602.11858v2)。

上述两张封面图来自原论文，按 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 使用。其他自动提取的封面来自对应 HTML 内嵌的图片，来源和许可见各篇文档中的说明。
