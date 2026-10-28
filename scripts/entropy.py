#!/usr/bin/env python3
"""计算字节熵 —— W05 用。

用法：
  python scripts/entropy.py --file capture.bin
  python scripts/entropy.py --text "hello world"
  python scripts/entropy.py --hex 16030100

熵的单位是 bit/byte，理论上限 8.0。
  ~4.5  自然语言
  ~7.9  压缩数据
  ~8.0  加密数据

注意：熵高只说明「看起来随机」，不代表「不可识别」。
正常 TLS 也对齐 8.0，真正暴露协议的是包长分布与时序结构。
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from pathlib import Path


def shannon(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def byte_histogram(data: bytes, top: int = 8) -> list[tuple[int, int]]:
    counts = Counter(data)
    return counts.most_common(top)


def report(name: str, data: bytes) -> None:
    ent = shannon(data)
    unique = len(set(data))
    print(f"\n{name}")
    print(f"  字节数     : {len(data)}")
    print(f"  唯一字节值 : {unique} / 256")
    print(f"  香农熵     : {ent:.4f} bit/byte  ({ent / 8 * 100:.1f}%)")
    print("  最常见字节 : " + ", ".join(f"0x{b:02x}×{c}" for b, c in byte_histogram(data, 5)))

    if ent > 7.95:
        verdict = "接近纯随机（加密数据或压缩数据）"
    elif ent > 7.0:
        verdict = "高熵（压缩/加密混合）"
    elif ent > 4.0:
        verdict = "中等（自然语言或结构化数据）"
    else:
        verdict = "低熵（重复度高）"
    print(f"  判读       : {verdict}")


def main() -> int:
    ap = argparse.ArgumentParser(description="计算字节熵")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", type=Path, help="二进制文件")
    src.add_argument("--text", help="直接给文本")
    src.add_argument("--hex", help="十六进制字符串，如 16030100")
    args = ap.parse_args()

    if args.file:
        if not args.file.exists():
            print(f"[error] 文件不存在：{args.file}", file=sys.stderr)
            return 1
        report(str(args.file), args.file.read_bytes())
    elif args.text is not None:
        report("文本", args.text.encode("utf-8"))
    else:
        try:
            data = bytes.fromhex(args.hex.replace(" ", "").replace("\n", ""))
        except ValueError:
            print("[error] 不是合法的十六进制", file=sys.stderr)
            return 1
        report("十六进制输入", data)

    print()
    print("提示：把 Wireshark 里某条 TCP 流的载荷 Export Packet Bytes 出来，")
    print("      分别对 Shadowsocks 流和 TLS 流跑一次，对比二者的熵。")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
