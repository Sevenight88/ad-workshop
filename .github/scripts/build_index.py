#!/usr/bin/env python3
"""
AD Workshop 索引构建脚本

遍历 items/<type>/<id>/，逐件校验，生成 items/index.json。
坏一件跳过一件，而不是让整次构建失败——一件坏文件不该让所有人的列表停更。

用法（由 GitHub Actions 调用）：
    python .github/scripts/build_index.py

输出：items/index.json
"""
import hashlib, json, os, re, sys
from datetime import datetime, timezone

ITEMS_DIR = "items"
INDEX_PATH = os.path.join(ITEMS_DIR, "index.json")
TYPES = {"vehicle", "compartment", "plate", "cannon"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[0-9a-f]{32}$")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build():
    items = []
    issues = []
    tag_pool = {}

    if not os.path.isdir(ITEMS_DIR):
        print("WARN: items/ 目录不存在，建一个空的索引。")
        write_index(items, tag_pool, issues)
        return

    for t in sorted(os.listdir(ITEMS_DIR)):
        typedir = os.path.join(ITEMS_DIR, t)
        if not os.path.isdir(typedir):
            continue
        if t not in TYPES:
            issues.append(f"跳过未知类型目录: {t}")
            continue

        for id_name in sorted(os.listdir(typedir)):
            itemdir = os.path.join(typedir, id_name)
            if not os.path.isdir(itemdir):
                continue

            meta_path = os.path.join(itemdir, "meta.json")
            blueprint_path = os.path.join(itemdir, "item.blueprint")
            preview_path = os.path.join(itemdir, "preview.png")

            if not os.path.isfile(meta_path):
                issues.append(f"{t}/{id_name}: 缺 meta.json，跳过")
                continue
            if not os.path.isfile(blueprint_path):
                issues.append(f"{t}/{id_name}: 缺 item.blueprint，跳过")
                continue

            try:
                meta = load_json(meta_path)
            except Exception as e:
                issues.append(f"{t}/{id_name}: meta.json 解析失败: {e}")
                continue

            # 基本字段检查
            if meta.get("type") != t:
                issues.append(f"{t}/{id_name}: type 写的是 {meta.get('type')}，却放在 {t}/ 下，跳过")
                continue
            if meta.get("id") != id_name:
                issues.append(f"{t}/{id_name}: id 是 {meta.get('id')}，目录却叫 {id_name}，跳过")
                continue
            sha = meta.get("sha256", "")
            if not SHA256_RE.match(sha):
                issues.append(f"{t}/{id_name}: sha256 格式不对 ({sha[:16]}...)，跳过")
                continue

            # 用磁盘上的真实大小覆盖 meta 里的 bytes（防止手改）
            real_bytes = os.path.getsize(blueprint_path)
            real_sha = check_sha256(blueprint_path)
            if real_sha != sha:
                issues.append(
                    f"{t}/{id_name}: sha256 对不上（meta={sha[:16]}..., disk={real_sha[:16]}...），跳过"
                )
                continue

            # 归一化标签，同时更新全局 tag 池
            raw_tags = meta.get("tags") or []
            tags = sorted({tag.strip() for tag in raw_tags if isinstance(tag, str) and tag.strip()})
            for tag in tags:
                tag_pool[tag] = tag_pool.get(tag, 0) + 1

            entry = {
                "id": id_name,
                "kind": t,
                "name": meta.get("name", id_name),
                "author": meta.get("author", "unknown"),
                "desc": meta.get("desc") or None,
                "gameVersion": meta.get("gameVersion") or None,
                "format": meta.get("format") or None,
                "era": meta.get("era") or None,
                "tags": tags,
                "bytes": real_bytes,
                "sha256": real_sha,
                "license": meta.get("license") or None,
                "created": meta.get("created") or "1970-01-01",
                "params": meta.get("params") or {},
                "hasPreview": os.path.isfile(preview_path),
            }
            items.append(entry)

    # 按 created 倒序排，新的在上
    items.sort(key=lambda x: x["created"], reverse=True)

    write_index(items, tag_pool, issues)


def write_index(items, tag_pool, issues):
    doc = {
        "schema": 1,
        "commit": os.environ.get("GITHUB_SHA", ""),
        "built": datetime.now(timezone.utc).isoformat(),
        "items": items,
        "tags": tag_pool,
    }
    os.makedirs(ITEMS_DIR, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print(f"OK: 索引已写入 {INDEX_PATH} — 共 {len(items)} 件作品，{len(tag_pool)} 个标签")
    if issues:
        print(f"WARN: 跳过 {len(issues)} 个问题项")
        for issue in issues:
            print(f"  - {issue}")

    # 把 issues 写进环境变量，后面的步骤可以拿它去开 GitHub Issue
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"## 索引构建结果\n\n- 有效作品: {len(items)}\n- 标签数: {len(tag_pool)}\n")
            if issues:
                f.write(f"- 跳过项: {len(issues)}\n")
                for issue in issues:
                    f.write(f"  - {issue}\n")
            f.write("\n")

    # 如果有跳过的项，让工作流标黄（但不失败）
    if issues:
        print(f"::warning::索引构建跳过了 {len(issues)} 个问题项")


if __name__ == "__main__":
    build()
