#!/usr/bin/env python3
"""解析 weeks/*.md 的勾选状态，生成进度数据与图形。

产出：
  progress.json        进度数据（供 shields.io 动态徽章读取）
  assets/progress.svg  进度条
  assets/calendar.svg  打卡日历热力图
  README.md            更新 <!-- PROGRESS:START --> 与 <!-- PROGRESS:END --> 之间的内容

无第三方依赖，Python 3.9+。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEEKS_DIR = ROOT / "weeks"
README = ROOT / "README.md"
ASSETS = ROOT / "assets"
LOG = ROOT / "checkins" / "log.json"
PROGRESS = ROOT / "progress.json"

BLOCK_START = "<!-- PROGRESS:START -->"
BLOCK_END = "<!-- PROGRESS:END -->"

# 打卡时区：固定 +08:00，避免 GitHub Actions 用 UTC 导致日期错一天
LOCAL_TZ = timezone(timedelta(hours=8))

TASK_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s*(T(\d{2})\.(\d{1,2}))\b\s*(.*)$")
WEEK_FILE_RE = re.compile(r"^w(\d{2})-[a-z0-9-]+\.md$")
TITLE_RE = re.compile(r"^#\s*W(\d{2})\s*[·:：]\s*(.+?)\s*$", re.M)

PHASES = [
    {"id": "P1", "name": "基础层", "weeks": (1, 4), "color": "#2ea44f"},
    {"id": "P2", "name": "协议层", "weeks": (5, 8), "color": "#2b6cb0"},
    {"id": "P3", "name": "工程层", "weeks": (9, 11), "color": "#6b46c1"},
    {"id": "P4", "name": "风控层", "weeks": (12, 13), "color": "#c05621"},
    {"id": "P5", "name": "研究层", "weeks": (14, 16), "color": "#b83280"},
]

BAR_CELLS = 6


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------

def today_local() -> date:
    return datetime.now(LOCAL_TZ).date()


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def repo_slug() -> str:
    """从 git remote 里取 owner/repo，取不到就返回占位符。"""
    env = os.environ.get("DSH_REPO_SLUG", "").strip()
    if env:
        return env
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=5,
        )
        url = out.stdout.strip()
    except Exception:
        url = ""
    if not url:
        return "__REPO_SLUG__"
    url = url.removesuffix(".git")
    m = re.search(r"github\.com[:/]+([^/]+)/([^/]+)$", url)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return "__REPO_SLUG__"


# --------------------------------------------------------------------------
# 解析
# --------------------------------------------------------------------------

def parse_weeks() -> list[dict]:
    weeks: list[dict] = []
    if not WEEKS_DIR.is_dir():
        return weeks
    for path in sorted(WEEKS_DIR.glob("*.md")):
        m = WEEK_FILE_RE.match(path.name)
        if not m:
            continue
        number = int(m.group(1))
        text = read_text(path)

        title = ""
        tm = TITLE_RE.search(text)
        if tm:
            title = tm.group(2)

        tasks = []
        # splitlines() 同时兼容 LF / CRLF，避免 Windows 检出后多出 \r
        for line_no, line in enumerate(text.splitlines(), start=1):
            t = TASK_RE.match(line)
            if not t:
                continue
            tasks.append({
                "id": t.group(2),
                "done": t.group(1).lower() == "x",
                "text": t.group(5).strip(),
                "line": line_no,
            })

        weeks.append({
            "week": number,
            "title": title or path.stem,
            "file": f"weeks/{path.name}",
            "tasks": tasks,
            "total": len(tasks),
            "done": sum(1 for t in tasks if t["done"]),
        })
    return weeks


def phase_of(week: int) -> dict:
    for p in PHASES:
        lo, hi = p["weeks"]
        if lo <= week <= hi:
            return p
    return PHASES[-1]


# --------------------------------------------------------------------------
# 日志
# --------------------------------------------------------------------------

def load_log() -> list[dict]:
    if not LOG.exists():
        return []
    try:
        data = json.loads(read_text(LOG))
    except (json.JSONDecodeError, OSError):
        return []
    entries = data.get("entries", []) if isinstance(data, dict) else []
    return [e for e in entries if isinstance(e, dict) and "id" in e and "date" in e]


def save_log(entries: list[dict]) -> None:
    entries = sorted(entries, key=lambda e: (e["date"], e["id"]))
    write_text(LOG, json.dumps({"version": 1, "entries": entries},
                               ensure_ascii=False, indent=2) + "\n")


def sync_log(weeks: list[dict], entries: list[dict]) -> tuple[list[dict], int]:
    """让日志与勾选状态保持一致。

    - 新勾选但日志里没有的任务 -> 用今天的日期补一条
    - 已取消勾选但日志里还有的   -> 删掉对应记录
    """
    done_ids = {t["id"] for w in weeks for t in w["tasks"] if t["done"]}
    logged_ids = {e["id"] for e in entries}

    today = today_local().isoformat()
    added = 0
    for tid in sorted(done_ids - logged_ids):
        entries.append({"id": tid, "date": today})
        added += 1

    kept = [e for e in entries if e["id"] in done_ids]
    return kept, added


# --------------------------------------------------------------------------
# 统计
# --------------------------------------------------------------------------

def compute(weeks: list[dict], entries: list[dict]) -> dict:
    total = sum(w["total"] for w in weeks)
    done = sum(w["done"] for w in weeks)
    percent = round(done / total * 100, 1) if total else 0.0

    activity: dict[str, int] = {}
    for e in entries:
        activity[e["date"]] = activity.get(e["date"], 0) + 1

    active_days = sorted(activity)
    streak = compute_streak([date.fromisoformat(d) for d in active_days])

    phases = []
    for p in PHASES:
        lo, hi = p["weeks"]
        pw = [w for w in weeks if lo <= w["week"] <= hi]
        pt = sum(w["total"] for w in pw)
        pd = sum(w["done"] for w in pw)
        phases.append({
            "id": p["id"], "name": p["name"], "color": p["color"],
            "weeks": [lo, hi],
            "total": pt, "done": pd,
            "percent": round(pd / pt * 100, 1) if pt else 0.0,
        })

    done_ids = sorted(t["id"] for w in weeks for t in w["tasks"] if t["done"])

    return {
        "schema": 1,
        "repo": repo_slug(),
        "total": total,
        "done": done,
        "percent": percent,
        "streak": streak,
        "active_days": len(active_days),
        "activity": dict(sorted(activity.items())),
        "phases": phases,
        "weeks": [{
            "week": w["week"], "title": w["title"], "file": w["file"],
            "total": w["total"], "done": w["done"],
            "percent": round(w["done"] / w["total"] * 100, 1) if w["total"] else 0.0,
        } for w in weeks],
        "done_ids": done_ids,
    }


def compute_streak(days: list[date]) -> dict:
    if not days:
        return {"current": 0, "longest": 0, "last": None}
    ds = sorted(set(days))
    longest = cur = 1
    for prev, nxt in zip(ds, ds[1:]):
        if (nxt - prev).days == 1:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 1

    today = today_local()
    s = set(ds)
    anchor = today if today in s else (today - timedelta(days=1) if (today - timedelta(days=1)) in s else None)
    current = 0
    if anchor:
        d = anchor
        while d in s:
            current += 1
            d -= timedelta(days=1)
    return {"current": current, "longest": longest, "last": ds[-1].isoformat()}


# --------------------------------------------------------------------------
# README
# --------------------------------------------------------------------------

def bar(pct: float, cells: int = 10) -> str:
    filled = int(round(pct / 100 * cells))
    filled = max(0, min(cells, filled))
    return "▰" * filled + "▱" * (cells - filled)


def render_readme_block(prog: dict) -> str:
    lines = []
    upd = prog["updated"].replace("T", " ")[:16]
    streak = prog["streak"]["current"]
    lines.append(
        f"> 🕒 更新于 {upd} (+08:00) ｜ ✅ **{prog['done']} / {prog['total']}** 项 ｜ "
        f"🔥 连续 **{streak}** 天 ｜ 活跃 {prog['active_days']} 天"
    )
    lines.append("")
    lines.append("| 阶段 | 进度 | 完成 |")
    lines.append("|:--|:--|:--:|")
    for p in prog["phases"]:
        lo, hi = p["weeks"]
        lines.append(
            f"| **{p['name']}** W{lo}–W{hi} | `{bar(p['percent'])}` {p['percent']:g}% | "
            f"{p['done']} / {p['total']} |"
        )
    lines.append("")
    lines.append("**每周进度**")
    lines.append("")
    lines.append("```")
    chips = [
        f"W{w['week']:02d} {bar(w['percent'], BAR_CELLS)} {w['done']}/{w['total']}"
        for w in prog["weeks"]
    ]
    for i in range(0, len(chips), 4):
        lines.append("    ".join(chips[i:i + 4]))
    lines.append("```")
    return "\n".join(lines)


def replace_block(text: str, inner: str) -> str:
    i = text.find(BLOCK_START)
    j = text.find(BLOCK_END)
    if i == -1 or j == -1 or j < i:
        return text
    head = text[: i + len(BLOCK_START)]
    tail = text[j:]
    return f"{head}\n{inner}\n{tail}"


# --------------------------------------------------------------------------
# SVG：进度条
# --------------------------------------------------------------------------

def render_progress_svg(prog: dict) -> str:
    W, H = 900, 208
    bar_x, bar_y, bar_w, bar_h = 292, 74, 574, 30

    segs = []
    labels = []
    cursor = bar_x
    total = prog["total"] or 1
    for p in prog["phases"]:
        seg_w = bar_w * (p["total"] / total)
        fill_w = seg_w * (p["done"] / p["total"]) if p["total"] else 0
        if fill_w > 0:
            segs.append(
                f'<rect x="{cursor:.2f}" y="{bar_y}" width="{fill_w:.2f}" '
                f'height="{bar_h}" fill="{p["color"]}" class="seg"/>'
            )
        cx = cursor + seg_w / 2
        labels.append(
            f'<text x="{cx:.1f}" y="{bar_y + bar_h + 22}" class="lab" '
            f'text-anchor="middle">{escape(p["name"])}</text>'
            f'<text x="{cx:.1f}" y="{bar_y + bar_h + 38}" class="lab2" '
            f'text-anchor="middle">{p["done"]}/{p["total"]}</text>'
        )
        cursor += seg_w

    upd = prog["updated"].replace("T", " ")[:16]
    streak = prog["streak"]["current"]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="学习进度 {prog['percent']}%">
  <style>
    .title {{ font: 700 13px -apple-system,BlinkMacSystemFont,'Segoe UI',Noto Sans,sans-serif; fill:#57606a; letter-spacing:.6px; }}
    .pct   {{ font: 800 58px -apple-system,BlinkMacSystemFont,'Segoe UI',Noto Sans,sans-serif; fill:#1f2328; }}
    .sub   {{ font: 500 14px -apple-system,BlinkMacSystemFont,'Segoe UI',Noto Sans,sans-serif; fill:#57606a; }}
    .lab   {{ font: 600 11px -apple-system,BlinkMacSystemFont,'Segoe UI',Noto Sans,sans-serif; fill:#57606a; }}
    .lab2  {{ font: 500 10px -apple-system,BlinkMacSystemFont,'Segoe UI',Noto Sans,sans-serif; fill:#8b949e; }}
    .track {{ fill:#eaeef2; }}
    .foot  {{ font: 400 11px -apple-system,BlinkMacSystemFont,'Segoe UI',Noto Sans,sans-serif; fill:#8b949e; }}
    .bg    {{ fill:#ffffff; }}
    @media (prefers-color-scheme: dark) {{
      .title,.sub,.lab {{ fill:#8b949e; }}
      .pct   {{ fill:#e6edf3; }}
      .lab2,.foot {{ fill:#6e7681; }}
      .track {{ fill:#21262d; }}
      .bg    {{ fill:#0d1117; }}
    }}
  </style>
  <defs>
    <clipPath id="rounded"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_h / 2}"/></clipPath>
  </defs>

  <rect class="bg" x="0" y="0" width="{W}" height="{H}" rx="14"/>

  <text x="36" y="42" class="title">学习进度 · 16 周网络对抗实验室</text>
  <text x="34" y="110" class="pct">{prog['percent']:g}%</text>
  <text x="38" y="136" class="sub">{prog['done']} / {prog['total']} 项任务已完成</text>
  <text x="38" y="158" class="sub">🔥 连续 {streak} 天 ｜ 活跃 {prog['active_days']} 天</text>

  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_h / 2}" class="track"/>
  <g clip-path="url(#rounded)">
    {''.join(segs)}
  </g>

  {''.join(labels)}

  <text x="36" y="{H - 12}" class="foot">更新于 {upd} (+08:00)</text>
</svg>
"""


# --------------------------------------------------------------------------
# SVG：打卡日历
# --------------------------------------------------------------------------

CAL_COLS = 17
CELL = 11
GAP = 3
STEP = CELL + GAP
LEFT = 26
TOP = 32


def render_calendar_svg(prog: dict) -> str:
    today = today_local()
    end = today + timedelta(days=6 - today.weekday())      # 本周周日
    start = end - timedelta(days=CAL_COLS * 7 - 1)

    activity = prog["activity"]
    width = LEFT + CAL_COLS * STEP + 8
    height = TOP + 7 * STEP + 46

    def level(n: int) -> int:
        if n <= 0:
            return 0
        if n == 1:
            return 1
        if n == 2:
            return 2
        if n == 3:
            return 3
        return 4

    cells = []
    month_labels = []
    seen_month = None
    for col in range(CAL_COLS):
        col_first = start + timedelta(days=col * 7)
        if col_first.month != seen_month:
            month_labels.append(
                f'<text x="{LEFT + col * STEP}" y="{TOP - 7}" class="mon">{col_first.month}月</text>'
            )
            seen_month = col_first.month

        for row in range(7):
            d = start + timedelta(days=col * 7 + row)
            if d > today:
                continue
            n = activity.get(d.isoformat(), 0)
            cells.append(
                f'<rect x="{LEFT + col * STEP}" y="{TOP + row * STEP}" '
                f'width="{CELL}" height="{CELL}" rx="2" class="l{level(n)}">'
                f'<title>{d.isoformat()} · {n} 项</title></rect>'
            )

    # 只在周一/三/五标星期
    day_labels = []
    for row, name in ((0, "一"), (2, "三"), (4, "五")):
        day_labels.append(
            f'<text x="4" y="{TOP + row * STEP + CELL - 2}" class="dow">{name}</text>'
        )

    legend_x = LEFT
    legend_y = TOP + 7 * STEP + 22
    legend = [
        f'<text x="{legend_x}" y="{legend_y + 9}" class="dow">少</text>'
    ]
    lx = legend_x + 20
    for lv in range(5):
        legend.append(
            f'<rect x="{lx}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2" class="l{lv}"/>'
        )
        lx += STEP
    legend.append(f'<text x="{lx + 4}" y="{legend_y + 9}" class="dow">多</text>')

    total_marks = sum(activity.values())
    summary = (
        f'<text x="{width - 8}" y="{legend_y + 9}" class="dow" text-anchor="end">'
        f'{total_marks} 次打卡 · 最长连续 {prog["streak"]["longest"]} 天</text>'
    )

    upd = prog["updated"].replace("T", " ")[:16]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="打卡日历">
  <style>
    .mon {{ font: 500 9px -apple-system,BlinkMacSystemFont,'Segoe UI',Noto Sans,sans-serif; fill:#8b949e; }}
    .dow {{ font: 400 9px -apple-system,BlinkMacSystemFont,'Segoe UI',Noto Sans,sans-serif; fill:#8b949e; }}
    .l0 {{ fill:#ebedf0; }}
    .l1 {{ fill:#9be9a8; }}
    .l2 {{ fill:#40c463; }}
    .l3 {{ fill:#30a14e; }}
    .l4 {{ fill:#216e39; }}
    .bg {{ fill:#ffffff; }}
    @media (prefers-color-scheme: dark) {{
      .l0 {{ fill:#21262d; }}
      .l1 {{ fill:#0e4429; }}
      .l2 {{ fill:#006d32; }}
      .l3 {{ fill:#26a641; }}
      .l4 {{ fill:#39d353; }}
      .mon,.dow {{ fill:#6e7681; }}
      .bg {{ fill:#0d1117; }}
    }}
  </style>
  <rect class="bg" x="0" y="0" width="{width}" height="{height}" rx="12"/>
  <text x="{LEFT}" y="12" class="mon">打卡日历 · 最近 {CAL_COLS} 周 ｜ 更新 {upd}</text>
  {''.join(month_labels)}
  {''.join(day_labels)}
  {''.join(cells)}
  {''.join(legend)}
  {summary}
</svg>
"""


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------

def load_prev_progress() -> dict | None:
    if not PROGRESS.exists():
        return None
    try:
        return json.loads(read_text(PROGRESS))
    except (json.JSONDecodeError, OSError):
        return None


def main() -> int:
    weeks = parse_weeks()
    if not weeks:
        print(f"[warn] 没有在 {WEEKS_DIR} 找到周文件", file=sys.stderr)
        return 1

    entries = load_log()
    entries, added = sync_log(weeks, entries)
    if added:
        print(f"[log] 补齐 {added} 条打卡记录（来自勾选状态）")
    save_log(entries)

    prog = compute(weeks, entries)

    # 只有「实质内容」变了才刷新时间戳。
    # 否则每次 push 都会产生一条只改 updated 的机器人提交，历史全是噪音。
    stamp = now_local().isoformat(timespec="seconds")
    prev = load_prev_progress()
    if prev:
        core = {k: v for k, v in prog.items() if k != "updated"}
        prev_core = {k: v for k, v in prev.items() if k != "updated"}
        if core == prev_core and prev.get("updated"):
            stamp = prev["updated"]
    prog["updated"] = stamp

    # 先全部渲染成字符串，再和磁盘逐字节比对，只写真正有差异的文件
    wanted: list[tuple[Path, str]] = [
        (PROGRESS, json.dumps(prog, ensure_ascii=False, indent=2) + "\n"),
        (ASSETS / "progress.svg", render_progress_svg(prog)),
        (ASSETS / "calendar.svg", render_calendar_svg(prog)),
    ]

    if README.exists():
        original = read_text(README).replace("__REPO_SLUG__", prog["repo"])
        wanted.append((README, replace_block(original, render_readme_block(prog))))

    dirty = [(p, c) for p, c in wanted if not p.exists() or read_text(p) != c]

    for path, content in dirty:
        write_text(path, content)

    if dirty:
        print(f"[write] 更新 {len(dirty)} 个文件：" + "、".join(p.name for p, _ in dirty))
    else:
        print("[skip] 进度无变化，未改动任何文件")

    print(
        f"[ok] {prog['done']}/{prog['total']} ({prog['percent']}%) · "
        f"连续 {prog['streak']['current']} 天 · 活跃 {prog['active_days']} 天"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
