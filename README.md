# Paper Reading

[打开论文索引](https://get1024.github.io/paper-reading/)

收录已读论文的中英对照批注和论证分析。索引支持搜索论文标题、简介、作者和关键词，可按主题筛选，默认按标题 A–Z 排序，也可切换到 Z–A。首页同时提供阅读材料与批注分布的统计，以及能回溯到文献条目的库内引用关系。

新增论文时，把 HTML 文件放在 `paper/` 目录并推送到 `main`。GitHub Actions 会自动扫描此目录及其子目录，提取标题和简介，在根目录生成索引并发布到 GitHub Pages。删除或改名也会在下一次构建时反映到索引中。

标题优先使用 HTML 的第一个 `<h1>`，其次使用 `<title>`，最后使用文件名。简介和搜索关键词分别读取 `<meta name="description">` 与 `<meta name="keywords">`。封面优先使用 `assets/` 中与 HTML 文件同名的小写图片（如 `paper/Vision-OPD.html` 对应 `assets/vision-opd.png`），否则直接引用第一张内嵌的 PNG、JPEG、WebP 或 GIF。

`papers.json` 可覆盖单篇论文的 `description`、`tag`、`short_title`、`topics`、`authors` 与 `year`。主题是依据原文手工整理的方法概念；新 HTML 会自动收录，无需在此文件中登记。

页面模板位于 `templates/index.html`，生成脚本为 `scripts/generate-index.py`。本地预览使用 Python 3，无需安装依赖。

```sh
python3 scripts/generate-index.py
python3 -m http.server 8000
```

打开 `http://localhost:8000/`。构建只生成根目录的 `index.html`，该文件已加入 Git 忽略。GitHub Actions 将索引、`paper/` 和 `assets/` 直接打包发布。

## 统计口径

所有统计在构建时读取本地 HTML，不请求外部服务。作者优先读取 `citation_author` 元数据，否则读取 `.author-line` 第一行，排除换行后的单位和共同一作符号；同名作者按大小写归一后去重。年份来自论文日期元数据或页头、版本说明中的 arXiv 编号，不使用文件修改时间或书目中其他论文的年份。

- 阅读段落：有类型标记的版本统计 `.reading-row[data-kind="paragraph"]`；INSID3 版式统计 `.unit.paragraph`；旧版 Vision-OPD 统计英文区的 `p.ltx_p`。不重复统计中文译文、图注、批注和参考文献。段落总数随收录论文变化，首页显示本次构建的统计值。
- 编号图：分别统计 `.reading-row[data-kind="figure"]`、`.unit.figure` 或旧版英文区的 `.ltx_tag_figure`，不按 `<img>` 数量计数；子图、放大镜占位图和案例插图不会放大编号图总数。
- 参考文献：统计 `li.ltx_bibitem`。总数是各篇书目条目相加，跨篇引用的同一文献会重复计入，不代表去重后的文献数。
- 五类高亮：统计整篇笔记中对应类别的 `<mark>`，包括正文、图表、算法、脚注和附加材料里的标注，排除图例；两套版式的“让步与反驳”和“让步与边界”统一归入“讨论”。它反映译注者的标记片段数量，不代表正文篇幅、论文质量或作者的研究投入。
- 库内引用：只在参考文献中精确匹配另一篇已收录论文的 arXiv 编号或完整标题，并保留真实条目锚点；正文提及、主题相近和共同作者不会被当作引用。

未识别版式的段落、图和参考文献数量保留为未知值；高亮体系与阅读版式均未识别时，五类高亮也保留为未知值，不等同于零。合计只加总已识别的计数，不猜测数量。新增版式可在生成脚本中扩展明确的选择器。轻量核验运行：

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
```

## 页面资源与许可

首页的两张 SVG 统计图基于 [Lieflat Charts](https://github.com/larashero3-dotcom/lieflat-charts) 的 L4 Arc Matrix 与 F5 Tick Rows，选型和核验基线见 [说明](docs/index-visualization.md)。相关模板代码遵循 [PolyForm Noncommercial 1.0.0](assets/lieflat-charts-LICENSE.txt)。Inter 可变字体来自 [Inter 官方仓库](https://github.com/rsms/inter)，随页面本地加载，许可见 [SIL OFL 1.1](assets/fonts/Inter-LICENSE.txt)。首页不依赖在线脚本或字体服务。

### 封面图来源

- Qianhao Yuan 等，《Vision-OPD》，[arXiv v4，图 4](https://arxiv.org/abs/2605.18740v4)。
- Lai Wei 等，《Zooming without Zooming》，[arXiv v2，图 2](https://arxiv.org/abs/2602.11858v2)。

上述两张封面图来自原论文，按 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 使用。其他自动提取的封面来自对应 HTML 内嵌的图片，来源和许可见各篇文档中的说明。
