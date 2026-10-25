#!/usr/bin/env python3
"""Read-only, per-lens photo exposure statistics using ExifTool."""

import argparse
import csv
import json
import math
from collections import Counter
from fractions import Fraction
from pathlib import Path
import shutil
import subprocess
import sys

from html_report import write_html

EXTENSIONS = (
    "jpg", "jpeg", "jpe", "tif", "tiff", "heic", "heif", "hif", "avif",
    "dng", "cr2", "cr3", "crw", "nef", "nrw", "arw", "srf", "sr2",
    "raf", "orf", "rw2", "raw", "pef", "srw", "3fr", "fff", "iiq", "rwl",
)
JPEG_EXTENSIONS = {"jpg", "jpeg", "jpe"}
RAW_EXTENSIONS = set(EXTENSIONS) - JPEG_EXTENSIONS - {
    "tif", "tiff", "heic", "heif", "hif", "avif",
}
METRICS = (
    ("FocalLengthIn35mmFormat", "35mm 等效焦距", "mm"),
    ("ISO", "ISO", ""),
    ("FNumber", "光圈", ""),
    ("ExposureTime", "快门速度", "s"),
)
UNKNOWN = "未知"


def positive_number(value):
    """Accept EXIF numbers and fractions, but never guess from descriptive text."""
    if isinstance(value, bool):
        return None
    try:
        number = float(Fraction(str(value)))
        return number if math.isfinite(number) and number > 0 else None
    except (ValueError, TypeError, ZeroDivisionError, OverflowError):
        return None


def lens_name(record):
    for tag in ("LensModel", "Lens", "LensID", "LensInfo"):
        value = record.get(tag)
        if value is not None and str(value).strip() not in ("", "0", "Unknown", "Unknown (0)"):
            return str(value).strip()
    return "未知镜头"


def deduplicate(records):
    """Merge only RAW/JPEG pairs with the same parent and case-folded stem."""
    buckets = {}
    for index, record in enumerate(records):
        source = record.get("SourceFile")
        path = Path(source) if source else None
        extension = path.suffix[1:].lower() if path else ""
        if extension in RAW_EXTENSIONS | JPEG_EXTENSIONS:
            key = (str(path.parent), path.stem.casefold())
        else:
            key = ("unpaired", index)
        buckets.setdefault(key, []).append((extension, record))

    result = []
    removed = 0
    for entries in buckets.values():
        has_raw = any(ext in RAW_EXTENSIONS for ext, _ in entries)
        has_jpeg = any(ext in JPEG_EXTENSIONS for ext, _ in entries)
        if not (has_raw and has_jpeg):
            result.extend(record for _, record in entries)
            continue
        # Stable ordering when more than one RAW/JPEG variant shares the stem.
        ordered = sorted(entries, key=lambda item: (
            item[0] not in RAW_EXTENSIONS, str(item[1].get("SourceFile", "")),
        ))
        readable = [record for _, record in ordered if not record.get("Error")]
        if not readable:
            result.append(ordered[0][1])
        else:
            merged = dict(readable[0])
            # Select a whole lens identity, rather than mixing tags across files.
            for tag in ("LensModel", "Lens", "LensID", "LensInfo"):
                merged.pop(tag, None)
            for record in readable:
                if lens_name(record) != "未知镜头":
                    merged["LensModel"] = lens_name(record)
                    break
            for tag, _, _ in METRICS:
                merged.pop(tag, None)
                for record in readable:
                    if positive_number(record.get(tag)) is not None:
                        merged[tag] = record[tag]
                        break
            result.append(merged)
        removed += len(entries) - 1
    return result, removed


def aggregate(records):
    groups = {}
    failed = 0
    for record in records:
        if record.get("Error"):
            failed += 1
            continue
        lens = lens_name(record)
        group = groups.setdefault(lens, {"count": 0, "metrics": {tag: Counter() for tag, _, _ in METRICS}})
        group["count"] += 1
        for tag, _, _ in METRICS:
            group["metrics"][tag][positive_number(record.get(tag))] += 1
    return groups, failed


def format_value(tag, value):
    if value is None:
        return UNKNOWN
    if tag == "ExposureTime":
        if value < 1:
            return f"1/{1 / value:.6g} s"
        return f"{value:.6g} s"
    if tag == "FNumber":
        return f"f/{value:g}"
    if tag == "FocalLengthIn35mmFormat":
        return f"{value:g} mm"
    return f"{value:g}"


def sorted_values(counter):
    return sorted(counter.items(), key=lambda item: (item[0] is None, item[0] or 0))


def print_report(groups):
    total = sum(group["count"] for group in groups.values())
    print(f"共统计 {total} 张照片，{len(groups)} 个镜头分组。")
    for lens, group in sorted(groups.items()):
        count = group["count"]
        print(f"\n【{lens}】{count} 张（全部照片的 {count / total:.1%}）")
        for tag, label, _ in METRICS:
            print(f"  {label}：")
            for value, frequency in sorted_values(group["metrics"][tag]):
                print(f"    {format_value(tag, value):>16}  {frequency:>6} 张  {frequency / count:6.1%}")


def write_csv(path, groups):
    # utf-8-sig lets Excel recognize Chinese column names reliably.
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["镜头", "镜头照片数", "参数", "数值", "单位", "显示值", "照片数", "组内占比"])
        for lens, group in sorted(groups.items()):
            for tag, label, unit in METRICS:
                for value, frequency in sorted_values(group["metrics"][tag]):
                    writer.writerow([
                        lens, group["count"], label, "" if value is None else value,
                        unit, format_value(tag, value), frequency, frequency / group["count"],
                    ])


def read_metadata(directory, recursive=True):
    executable = shutil.which("exiftool")
    if not executable:
        raise RuntimeError("未找到 ExifTool。macOS: brew install exiftool；Ubuntu/Debian: sudo apt install libimage-exiftool-perl")
    # Keep LensID's interpreted name, but request numeric exposure values.
    command = [executable, "-json", "-charset", "filename=UTF8"]
    if recursive:
        command.append("-r")
    for extension in EXTENSIONS:
        command.extend(["-ext", extension])
    command.extend([
        "-LensModel", "-Lens", "-LensID", "-LensInfo",
        "-FocalLengthIn35mmFormat#", "-ISO#", "-FNumber#", "-ExposureTime#",
        str(directory),
    ])
    result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", check=False)
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    try:
        records = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ExifTool 未返回有效 JSON（退出码 {result.returncode}）") from exc
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise RuntimeError("ExifTool 返回了非预期的数据结构")
    if result.returncode and not records:
        raise RuntimeError(f"ExifTool 读取失败（退出码 {result.returncode}）")
    if result.returncode:
        print("警告：部分文件读取失败，以下仅统计成功读取的文件。", file=sys.stderr)
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description="按镜头统计照片的焦段、ISO、光圈和快门速度（只读）")
    parser.add_argument("directory", type=Path, help="照片目录，默认递归包含子目录")
    parser.add_argument("--no-recursive", action="store_true", help="只扫描指定目录，不含子目录")
    parser.add_argument("--csv", type=Path, metavar="FILE", help="另存为 CSV 文件（会覆盖同名文件）")
    parser.add_argument("--html", type=Path, metavar="FILE", help="导出离线 HTML 四图报告（会覆盖同名文件）")
    args = parser.parse_args(argv)
    directory = args.directory.expanduser().resolve()
    if not directory.is_dir():
        parser.error(f"目录不存在或不是目录：{directory}")
    if args.csv:
        args.csv = args.csv.expanduser().resolve()
        if args.csv.suffix.lower() != ".csv":
            parser.error("导出文件必须使用 .csv 扩展名，以免误覆盖照片")
    if args.html:
        args.html = args.html.expanduser().resolve()
        if args.html.suffix.lower() not in (".html", ".htm"):
            parser.error("HTML 导出文件必须使用 .html 或 .htm 扩展名")
    try:
        records, removed = deduplicate(read_metadata(directory, not args.no_recursive))
        groups, failed = aggregate(records)
        if removed:
            print(f"已合并同名 RAW/JPEG，减少 {removed} 份重复文件。")
        print_report(groups)
        if failed:
            print(f"跳过 {failed} 张读取失败且无可用配对文件的照片。", file=sys.stderr)
        if args.csv:
            write_csv(args.csv, groups)
            print(f"\nCSV 已保存：{args.csv}")
        if args.html:
            write_html(args.html, groups, directory, removed, failed)
            print(f"\nHTML 已保存：{args.html}")
    except (RuntimeError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
