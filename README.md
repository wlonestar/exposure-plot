# 相机照片参数统计

按镜头分组，统计每个 35mm 等效焦距、ISO、光圈、快门速度的**照片数和组内占比**。终端输出完整分布，可另存 CSV。只读取照片元数据，不修改照片。

## 安装

需要 Python 3.9+ 和 [ExifTool](https://exiftool.org/)，无需安装 Python 第三方包。

```bash
# macOS
brew install exiftool

# Ubuntu / Debian
sudo apt install libimage-exiftool-perl
```

Windows 请安装 ExifTool 并将可执行文件命名为 `exiftool.exe`，加入 PATH。

## 虚拟环境

使用 uv 创建项目内的虚拟环境（无需安装 Python 第三方包）：

```bash
uv venv .venv

# bash / zsh
source .venv/bin/activate

# fish
# source .venv/bin/activate.fish
```

Windows PowerShell 激活命令为 `.venv\Scripts\Activate.ps1`。激活后，下文的 `python` 命令均使用虚拟环境。ExifTool 是系统工具，不安装在 Python 虚拟环境中。

## 使用

```bash
# 默认递归扫描，路径包含空格时加引号
python photo_stats.py "/path/to/photos"

# 同时导出 CSV，适合在 Excel 中筛选或制作透视图
python photo_stats.py "/path/to/photos" --csv lens-stats.csv

# 不扫描子目录
python photo_stats.py "/path/to/photos" --no-recursive
```

输出示例：

```text
共统计 100 张照片，1 个镜头分组。

【FE 24-70mm F2.8 GM】100 张（全部照片的 100.0%）
  35mm 等效焦距：
               24 mm      60 张   60.0%
               70 mm      40 张   40.0%
...
```

## HTML 四图报告

```bash
python photo_stats.py "/path/to/photos" --html report.html

# 可以同时导出 CSV
python photo_stats.py "/path/to/photos" --html report.html --csv stats.csv
```

用浏览器打开生成的 HTML 即可查看焦段、ISO、光圈、快门四张堆叠柱状图。每种颜色代表一个镜头，可勾选筛选，悬停、轻触或键盘聚焦柱段查看次数与组内占比。桌面为 2×2 布局，手机为单列；取值较多时图内横向滚动。

报告是单个离线文件，无 CDN、无需联网，也不需安装 Python 第三方库。横轴按数值排序，以等间距展示每个实际取值，不代表连续比例尺；柱高为照片数，未知值独立显示。导出会覆盖同名 HTML，父目录需已存在。

当前测试目录的报告：`reports/2026.html`。

## 统计口径与限制

- 支持 JPEG、TIFF、HEIC/HEIF/HIF、AVIF 和常见 RAW（CR2/CR3、NEF、ARW、RAF、DNG 等）。实际解码能力取决于 ExifTool 版本；扩展名不区分大小写。
- **同一目录、同一主文件名的 RAW + JPEG 只算一张照片**，扩展名及主文件名匹配不区分大小写。例如 `DSC001.ARW` 和 `DSC001.JPG` 会合并。优先使用 RAW 参数，缺失或无效的参数从 JPEG 补充；RAW 读取失败时可使用 JPEG。不同目录的同名文件不会合并。
- 只有同时存在 RAW 和 JPEG 时才合并；单独的 RAW、JPEG 以及其他格式仍按文件统计。同名的多个 RAW/JPEG 变体在有配对时也归为一张，优先级相同时按文件路径排序选择。改过主文件名的副本无法自动识别，误用同名的不同照片也无法自动区分。
- 递归扫描采用 ExifTool 默认规则，不进入隐藏子目录。
- 焦段直接取 EXIF 的 `FocalLengthIn35mmFormat`（35mm 等效焦距，mm），终端、CSV、HTML 统一使用这个口径。缺失时归为“未知”，不使用实际焦距代替、不自行乘裁切系数。保留相机记录的数值（可能经过取整），不自动合并为焦距区间。
- 镜头名依次取 LensModel、Lens、LensID、LensInfo；无法识别的归入“未知镜头”。不同相机写出的不同名称不会自动合并，同名的不同实体镜头无法区分。
- 每个参数缺失或无效时归为“未知”，占比分母仍为该镜头的全部照片数。缺少 EXIF 的可读图片也计入。
- ExifTool 的读取错误会报告；配对中有可读文件时仍统计这张照片，全部不可读才跳过。部分文件失败时仍输出可用统计。未识别镜头不代表读取失败。
- 快门以秒统计，短于一秒显示为倒数，例如 `1/125 s`。数值排序按曝光时间从短到长。
- CSV 每行是一项参数的一个取值；占比为 0–1 的小数，快门原始数值单位为秒。使用 UTF-8 BOM 以方便 Excel 读取中文。
- CSV 会覆盖同名文件，父目录需已存在；只允许使用 `.csv` 后缀。
- 批量读取的元数据会载入内存；超大图库建议分目录运行。

## 测试

```bash
python -m unittest discover -s tests -v
```
