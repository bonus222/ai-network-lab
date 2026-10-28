# 打卡记录

这个目录存两样东西：

| 文件 | 内容 | 谁来写 |
|:--|:--|:--|
| `log.json` | 每个任务「哪天完成的」 | `build_progress.py` 自动维护 |
| `notes.md` | 学习笔记、踩坑记录 | `checkin.py note "..."` |

## log.json 的结构

```json
{
  "version": 1,
  "entries": [
    { "id": "T01.1", "date": "2026-10-29" },
    { "id": "T01.2", "date": "2026-10-29" },
    { "id": "T03.2", "date": "2026-11-02" }
  ]
}
```

- `id`：任务编号，必须和 `weeks/*.md` 里的一致
- `date`：完成日期，格式 `YYYY-MM-DD`，**固定按 +08:00 计算**

日历热力图就是用这个文件画的：同一天完成 3 项，那格就深一点。

## 为什么日期不用 UTC

GitHub Actions 跑在 UTC 时区。如果直接用 `date.today()`，你在北京时间晚上 11 点打的卡会被记到「昨天」。

所以脚本里固定用 `timezone(timedelta(hours=8))`。如果你在别的时区，改 `scripts/build_progress.py` 里的 `LOCAL_TZ`。

## 三条规则

1. **不要手工编辑 `log.json`**。改了也会被下次运行覆盖。
2. **取消勾选会自动删掉对应记录**。所以「打卡后反悔」不会污染日历。
3. **补打卡用 `--date`**：

```powershell
python scripts/checkin.py done T01.1 --date 2026-10-25
```

## 它和「勾选状态」的关系

```
weeks/*.md 里的 - [x]   ←→   log.json 里的 entries
        ↑                            ↑
     你手动改                  脚本自动同步
```

脚本每次运行都会对账：

- 新勾选但没记录 → 补一条（日期=今天）
- 有记录但已取消 → 删掉

所以**你可以在任何地方勾选**（本地命令行、GitHub 网页、手机），同步都是自动的。

## notes.md 长什么样

```markdown
# 学习笔记

## 2026-10-29

- 23:14 REALITY 的 shortId 必须客户端服务端完全一致，不一致时客户端只报 timeout
- 23:40 Wireshark 里 `tls.handshake.extensions_server_name` 能直接过滤出 SNI
```

`checkin.py note "..."` 会自动按当天日期分组追加。
