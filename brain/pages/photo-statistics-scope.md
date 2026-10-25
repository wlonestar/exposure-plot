---
id: photo-statistics-scope
title: "照片参数统计的需求边界"
category: project
status: active
created: "2026-10-25T21:23:28"
updated: "2026-10-25T21:49:34"
---

<!-- compiled_truth -->
用户需要统计指定目录中的相机照片，以镜头为分组维度，统计 35mm 等效焦距、ISO、光圈和快门速度的使用分布。焦距直接读取 EXIF FocalLengthIn35mmFormat，保留相机记录值，缺失时标为未知，不使用实际焦距代替或自行猜测裁切系数。

同一目录中同名主文件的 JPG 与 RAW 只计一张，优先 RAW，缺失参数用 JPG 补充，不跨目录合并。

可视化只包含等效焦距、ISO、光圈、快门四张图，导出离线单个 HTML，参考 ExposurePlot 四象限布局。


## Timeline

- time: 2026-10-25T21:23:28
  kind: decision
  summary: "Created this page: 照片参数统计的需求边界"
  source: "用户初始需求"
  affects: [photo-statistics-scope]

- time: 2026-10-25T21:23:29
  kind: decision
  summary: "记录用户明确提出的分组与统计需求"
  source: "用户初始需求"
  affects: [photo-statistics-scope]

- time: 2026-10-25T21:25:41
  kind: decision
  summary: "用户确认 JPG 与 RAW 需要去重统计"
  source: "用户确认选项 1"
  affects: [photo-statistics-scope]

- time: 2026-10-25T21:46:02
  kind: decision
  summary: "用户要求可视化仅包含焦段、ISO、光圈、快门四张图，导出单个 HTML，参考 ExposurePlot 四象限布局"
  source: "用户提供截图及导出要求"
  affects: [photo-statistics-scope]

- time: 2026-10-25T21:49:34
  kind: decision
  summary: "按用户要求将焦段口径从实际焦距改为 EXIF 35mm 等效焦距，保留配对及四图导出要求"
  source: "用户要求等效焦距；实际照片确认存在该 EXIF 字段"
  affects: [photo-statistics-scope]
