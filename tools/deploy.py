#!/usr/bin/env python3
"""把 longyan_water 集成一键部署到远程 Home Assistant（SSH 流式传输，无需 SFTP/Samba）。

用法:
    pip install paramiko
    python tools/deploy.py                        # 用下面的默认配置
    python tools/deploy.py --host 192.168.1.10 --user root --key ~/.ssh/id_rsa_ha
    python tools/deploy.py --password 你的密码

可选参数:
    --host       HA 主机地址（默认 192.168.1.10）
    --port       SSH 端口（默认 22）
    --user       SSH 用户（默认 root）
    --key        SSH 私钥路径（与 --password 二选一）
    --password   SSH 密码
    --no-restart 只上传文件，不重启 HA

原理: 本地打包 tar.gz → 通过 SSH stdin 流式写入远程 /tmp → 解压到
      /homeassistant/custom_components/ → ha core restart
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import tarfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PACKAGE = "longyan_water"
TARGET_DIR = "/homeassistant/custom_components"
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "custom_components", PACKAGE)


def build_tar(src: str) -> tuple[bytes, int]:
    """把集成目录打包为 tar.gz（顶层目录名为 longyan_water/）"""
    buf = io.BytesIO()
    n = 0
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for root, _dirs, files in os.walk(src):
            for f in files:
                if f.endswith(".pyc") or "__pycache__" in root:
                    continue
                full = os.path.join(root, f)
                arc = PACKAGE + "/" + os.path.relpath(full, src).replace("\\", "/")
                info = tarfile.TarInfo(arc)
                info.size = os.path.getsize(full)
                info.mode = 0o644
                with open(full, "rb") as fh:
                    tf.addfile(info, fh)
                n += 1
    return buf.getvalue(), n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="192.168.1.10")
    ap.add_argument("--port", type=int, default=22)
    ap.add_argument("--user", default="root")
    ap.add_argument("--key", default=None, help="SSH 私钥路径")
    ap.add_argument("--password", default=None, help="SSH 密码")
    ap.add_argument("--no-restart", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(SRC):
        print(f"找不到源码目录: {SRC}")
        return 1

    try:
        import paramiko
    except ImportError:
        print("需要 paramiko: pip install paramiko")
        return 1

    payload, n = build_tar(SRC)
    print(f"[1/4] 打包完成: {len(payload)} bytes, {n} 个文件")

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kw = dict(port=args.port, username=args.user, timeout=20,
              allow_agent=False, look_for_keys=False)
    if args.key:
        kw["key_filename"] = os.path.expanduser(args.key)
    if args.password:
        kw["password"] = args.password
    print(f"[2/4] 连接 {args.user}@{args.host}:{args.port} ...")
    c.connect(args.host, **kw)

    # 远程执行：接收 tar → 解压 → 校验
    cmd = (
        "cat > /tmp/lw.tar.gz && echo RECEIVED && "
        f"rm -rf {TARGET_DIR}/{PACKAGE} && "
        f"tar xzf /tmp/lw.tar.gz -C {TARGET_DIR}/ && "
        "rm -f /tmp/lw.tar.gz && echo EXTRACTED && "
        f"ls {TARGET_DIR}/{PACKAGE}/ && "
        f"grep version {TARGET_DIR}/{PACKAGE}/manifest.json"
    )
    _i, o, _e = c.exec_command(cmd, timeout=180)
    o.channel.sendall(payload)
    o.channel.shutdown_write()
    out = o.read().decode("utf-8", "replace")
    print(out.strip())
    if "EXTRACTED" not in out:
        print("[!] 上传/解压似乎失败，请检查上面的输出")
        c.close()
        return 1
    print("[3/4] 上传并解压完成")

    if args.no_restart:
        print("[4/4] 已跳过重启（--no-restart）。记得在 HA 里重载集成。")
    else:
        print("[4/4] 重启 HA ...")
        _i, o, _e = c.exec_command("ha core restart && echo RESTARTED", timeout=300)
        print(o.read().decode("utf-8", "replace").strip())

    c.close()
    print("\n✅ 完成。验证：HA → 开发者工具 → 状态 → 搜 zi_lai_shui")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
