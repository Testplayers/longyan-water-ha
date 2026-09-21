#!/usr/bin/env python3
"""把本仓库内容同步到 GitHub（一次提交，自动删除远端多余文件）。

用法:
    # token 优先取环境变量 GH_TOKEN
    set GH_TOKEN=ghp_xxx            # Windows
    export GH_TOKEN=ghp_xxx         # Linux/macOS
    python tools/publish.py

    # 或显式传入
    python tools/publish.py --token ghp_xxx
    python tools/publish.py --token ghp_xxx --repo longyan-water-ha --msg "fix: 适配网厅改版"

Token 权限: Classic token 勾 repo；Fine-grained token 需 Contents(Read/Write)
            + Administration(Read/Write，仅首次建仓库时需要)。

说明:
    - 全部文件走 blob API（对 1.9 MB 的 captcha_templates.json 也稳）
    - 会自动删掉远端已删除的本地文件（以本地为准）
    - 首次对空仓库会自动引导一次提交
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://api.github.com"
HERE = pathlib.Path(__file__).resolve().parent.parent   # 仓库根目录


def default_token() -> str:
    """取 token：优先环境变量；Windows 下若进程环境未刷新则回退读用户级注册表。"""
    t = os.environ.get("GH_TOKEN", "")
    if t or os.name != "nt":
        return t
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, "GH_TOKEN")[0]
    except OSError:
        return ""


def req(method: str, path: str, token: str, data=None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    r = urllib.request.Request(API + path, data=body, method=method)
    r.add_header("Authorization", "Bearer " + token)
    r.add_header("Accept", "application/vnd.github+json")
    r.add_header("User-Agent", "lw-publisher")
    if body:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=180) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} {method} {path}: "
                           f"{e.read().decode('utf-8', 'replace')[:300]}") from None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=default_token())
    ap.add_argument("--repo", default="longyan-water-ha")
    ap.add_argument("--msg", default="chore: 同步本地更新")
    ap.add_argument("--desc", default="龙岩水发自来水 Home Assistant 集成"
                                      "（自动识别验证码，含部署脚本与完整教程）")
    args = ap.parse_args()
    if not args.token:
        print("缺少 token：设置环境变量 GH_TOKEN 或传 --token")
        return 1

    me = req("GET", "/user", args.token)
    owner = me["login"]
    print(f"账号: {owner}")

    try:
        req("POST", "/user/repos", args.token, {
            "name": args.repo, "description": args.desc, "private": False,
            "has_issues": True, "has_wiki": False})
        print(f"✅ 新建仓库 {owner}/{args.repo}")
    except RuntimeError as e:
        if "422" in str(e):
            print("仓库已存在，继续同步")
        else:
            print(f"建仓库失败: {e}")
            return 1

    files = sorted(p for p in HERE.rglob("*") if p.is_file()
                   and "__pycache__" not in p.parts
                   and not p.name.endswith((".pyc", ".pyo")))

    # 空仓库需要先 bootstrap
    parent = None
    try:
        ref = req("GET", f"/repos/{owner}/{args.repo}/git/ref/heads/main", args.token)
        parent = ref["object"]["sha"]
        print(f"当前 HEAD: {parent[:8]}")
    except RuntimeError:
        boot = next((p for p in files if p.name == "README.md"), files[0])
        req("PUT", f"/repos/{owner}/{args.repo}/contents/"
            + urllib.parse.quote(boot.relative_to(HERE).as_posix()), args.token, {
                "message": "chore: bootstrap repository",
                "content": base64.b64encode(boot.read_bytes()).decode(),
                "branch": "main"})
        ref = req("GET", f"/repos/{owner}/{args.repo}/git/ref/heads/main", args.token)
        parent = ref["object"]["sha"]
        print("空仓库 → 已引导首次提交")

    tree = []
    for p in files:
        rel = p.relative_to(HERE).as_posix()
        raw = p.read_bytes()
        blob = req("POST", f"/repos/{owner}/{args.repo}/git/blobs", args.token,
                   {"content": base64.b64encode(raw).decode(), "encoding": "base64"})
        tree.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print(f"   ✓ {rel:<52} {len(raw):>9} B")

    new_tree = req("POST", f"/repos/{owner}/{args.repo}/git/trees", args.token,
                   {"tree": tree})       # 不带 base_tree → 远端多余文件自动消失
    commit = req("POST", f"/repos/{owner}/{args.repo}/git/commits", args.token,
                 {"message": args.msg, "tree": new_tree["sha"], "parents": [parent]})
    req("PATCH", f"/repos/{owner}/{args.repo}/git/refs/heads/main", args.token,
        {"sha": commit["sha"]})

    print(f"\n✅ 完成 {commit['sha'][:8]}")
    print(f"https://github.com/{owner}/{args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
