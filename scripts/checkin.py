#!/usr/bin/env python3
"""打卡 CLI —— 勾选任务、记录日期、刷新进度。

用法：
  python scripts/checkin.py status              # 总览
  python scripts/checkin.py next                # 下一个该做的任务
  python scripts/checkin.py list                # 全部任务
  python scripts/checkin.py list -w 3           # 只看第 3 周
  python scripts/checkin.py list --todo         # 只看没做的
  python scripts/checkin.py done T03.2          # 打勾（可一次多个）
  python scripts/checkin.py undo T03.2          # 取消
  python scripts/checkin.py done T03.2 --date 2026-10-28   # 补打卡
  python scripts/checkin.py note "REALITY shortId 要一致"
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_progress as bp  # noqa: E402

CHECK_RE = re.compile(r"\[([ xX])\]")
NOTES = ROOT / "checkins" / "notes.md"


# --------------------------------------------------------------------------
# 读取
# --------------------------------------------------------------------------

def all_tasks() -> list[dict]:
    """按周次、序号排序的全部任务，附带周信息。"""
    out = []
    for w in bp.parse_weeks():
        for t in w["tasks"]:
            out.append({**t, "week": w["week"], "file": w["file"], "title": w["title"]})
    return out


def find_task(tid: str) -> dict | None:
    tid = tid.upper()
    for t in all_tasks():
        if t["id"] == tid:
            return t
    return None


# --------------------------------------------------------------------------
# 写入
# --------------------------------------------------------------------------

def set_task(tid: str, checked: bool) -> bool:
    """改 weeks/*.md 里对应那一行的复选框。返回是否发生变化。"""
    task = find_task(tid)
    if not task:
        raise KeyError(tid)

    path = ROOT / task["file"]
    # newline="" 让 CRLF 原样保留（read_text 会把 \r\n 规范化成 \n）
    with open(path, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    # keepends=True 保留每行原来的换行符，避免改动整份文件的行尾
    lines = text.splitlines(keepends=True)
    idx = task["line"] - 1
    if idx < 0 or idx >= len(lines):
        raise IndexError(f"{tid} 行号越界")

    old = lines[idx]
    new = CHECK_RE.sub("[x]" if checked else "[ ]", old, count=1)
    if new == old:
        return False

    lines[idx] = new
    bp.write_text(path, "".join(lines))
    return True


def apply_backdate(tid: str, date_str: str) -> None:
    entries = bp.load_log()
    today = bp.today_local().isoformat()
    changed = False
    for e in entries:
        if e["id"] == tid and e["date"] == today:
            e["date"] = date_str
            changed = True
    if changed:
        bp.save_log(entries)


# --------------------------------------------------------------------------
# 子命令
# --------------------------------------------------------------------------

def cmd_status(_: argparse.Namespace) -> int:
    weeks = bp.parse_weeks()
    entries = bp.load_log()
    prog = bp.compute(weeks, entries)

    print()
    print(f"  总进度   {prog['done']}/{prog['total']}  ({prog['percent']}%)")
    print(f"  连续打卡 {prog['streak']['current']} 天   最长 {prog['streak']['longest']} 天   活跃 {prog['active_days']} 天")
    print()
    for p in prog["phases"]:
        lo, hi = p["weeks"]
        print(f"  {bp.bar(p['percent'])} {p['percent']:5.1f}%  {p['name']} (W{lo}-W{hi})"
              f"  {p['done']}/{p['total']}")
    print()

    nxt = next_task(prog)
    if nxt:
        print(f"  → 下一个：{nxt['id']}  {nxt['text'][:52]}")
        print(f"             ({nxt['file']})")
    else:
        print("  🎉 全部完成！")
    print()
    return 0


def next_task(prog: dict | None = None) -> dict | None:
    done_ids = set(prog["done_ids"]) if prog else {t["id"] for t in all_tasks() if t["done"]}
    for t in all_tasks():
        if t["id"] not in done_ids:
            return t
    return None


def cmd_next(_: argparse.Namespace) -> int:
    t = next_task()
    if not t:
        print("🎉 全部完成，去写终期报告吧。")
        return 0
    print()
    print(f"  [{t['id']}]  {t['text']}")
    print(f"  第 {t['week']} 周 · {t['title']}")
    print(f"  文件：{t['file']}  第 {t['line']} 行")
    print()
    print(f"  完成后：python scripts/checkin.py done {t['id']}")
    print()
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    tasks = all_tasks()
    if args.week:
        tasks = [t for t in tasks if t["week"] == args.week]
    if args.todo:
        tasks = [t for t in tasks if not t["done"]]
    if args.done:
        tasks = [t for t in tasks if t["done"]]

    if not tasks:
        print("（没有匹配的任务）")
        return 0

    current_week = None
    for t in tasks:
        if t["week"] != current_week:
            current_week = t["week"]
            print(f"\n  W{t['week']:02d} · {t['title']}")
        mark = "x" if t["done"] else " "
        print(f"   [{mark}] {t['id']}  {t['text'][:60]}")
    print()
    return 0


def cmd_done(args: argparse.Namespace) -> int:
    changed = []
    for raw in args.ids:
        tid = raw.upper()
        t = find_task(tid)
        if not t:
            print(f"[error] 找不到任务 {tid}，用 `list` 看看有哪些", file=sys.stderr)
            return 1
        try:
            if set_task(tid, True):
                changed.append(tid)
            else:
                print(f"[skip] {tid} 已经是勾选状态")
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {tid}: {exc}", file=sys.stderr)
            return 1

    bp.main()

    if args.date:
        try:
            date.fromisoformat(args.date)
        except ValueError:
            print(f"[error] 日期格式应为 YYYY-MM-DD，收到 {args.date}", file=sys.stderr)
            return 1
        for tid in changed:
            apply_backdate(tid, args.date)
        if changed:
            bp.main()

    if changed:
        print(f"[done] {', '.join(changed)}")
    return 0


def cmd_undo(args: argparse.Namespace) -> int:
    changed = []
    for raw in args.ids:
        tid = raw.upper()
        if not find_task(tid):
            print(f"[error] 找不到任务 {tid}", file=sys.stderr)
            return 1
        if set_task(tid, False):
            changed.append(tid)
    bp.main()
    if changed:
        print(f"[undo] {', '.join(changed)}")
    else:
        print("[skip] 本来就是未完成")
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    text = " ".join(args.text).strip()
    if not text:
        print("[error] note 内容不能为空", file=sys.stderr)
        return 1
    stamp = bp.now_local().strftime("%Y-%m-%d %H:%M")
    day = bp.today_local().isoformat()
    header = f"\n## {day}\n"

    existing = NOTES.read_text(encoding="utf-8") if NOTES.exists() else "# 学习笔记\n"
    if header.strip() in existing:
        existing = existing.rstrip("\n") + f"\n- {stamp[11:]} {text}\n"
    else:
        existing = existing.rstrip("\n") + header + f"\n- {stamp[11:]} {text}\n"
    bp.write_text(NOTES, existing)
    print(f"[note] {day} {stamp[11:]} {text}")
    return 0


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="checkin", description="16 周网络对抗实验室 · 打卡工具")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="总览进度").set_defaults(func=cmd_status)
    sub.add_parser("next", help="下一个未完成任务").set_defaults(func=cmd_next)

    p_list = sub.add_parser("list", help="列出任务")
    p_list.add_argument("-w", "--week", type=int, help="只看某一周")
    g = p_list.add_mutually_exclusive_group()
    g.add_argument("--todo", action="store_true", help="只看未完成")
    g.add_argument("--done", action="store_true", help="只看已完成")
    p_list.set_defaults(func=cmd_list)

    p_done = sub.add_parser("done", help="标记完成")
    p_done.add_argument("ids", nargs="+", help="任务编号，如 T03.2")
    p_done.add_argument("--date", help="补打卡日期 YYYY-MM-DD")
    p_done.set_defaults(func=cmd_done)

    p_undo = sub.add_parser("undo", help="取消完成")
    p_undo.add_argument("ids", nargs="+")
    p_undo.set_defaults(func=cmd_undo)

    p_note = sub.add_parser("note", help="记一条学习笔记")
    p_note.add_argument("text", nargs="+")
    p_note.set_defaults(func=cmd_note)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
