# 故障排查

> 按「现象 → 原因 → 解决」组织。Git 相关的问题看 [00-github-beginner.md](00-github-beginner.md#10-常见错误对照表)。

## 脚本类

### `python` 不是内部或外部命令

**原因**：Python 没装，或没加进 PATH。

**解决**：

1. 装 Python 3.10+（<https://www.python.org/downloads/>），安装时**勾选 Add python.exe to PATH**
2. 重开 PowerShell
3. 验证：`python --version`

### 脚本输出中文乱码（`锟斤拷` / `?????`）

**原因**：Windows 控制台默认代码页是 GBK（936）。

**解决**：

```powershell
chcp 65001
```

或者在 PowerShell 配置文件里持久化：

```powershell
"chcp 65001 > `$null" | Add-Content $PROFILE
```

> 注意：**文件本身**是 UTF-8 的，乱码只发生在显示层。用 VS Code 打开看是正常的。

### `checkin.py done T03.2` 报 "找不到任务"

**原因**：编号不对，或者周文件里的格式被改坏了。

**解决**：

```powershell
python scripts/checkin.py list -w 3
```

看第 3 周到底有哪些编号。格式必须是：

```markdown
- [ ] T03.2 任务描述
```

即：`- ` + `[ ]` + 空格 + `T03.2` + 空格 + 描述。编号必须紧跟方括号。

### 勾选了但进度没变

依次检查：

1. 格式对不对（见上一条）
2. 有没有跑 `python scripts/build_progress.py`
3. `git add -A` 了吗（新文件不 add 不会提交）
4. push 成功了吗

### 日历一直是空的

**原因**：`checkins/log.json` 里没有记录。

**解决**：正常情况下 `build_progress.py` 会自动补记录（根据勾选状态，日期记为当天）。如果还是空：

```powershell
python scripts/build_progress.py
```

它会打印 `[log] 补齐 N 条打卡记录`。

补历史日期：

```powershell
python scripts/checkin.py done T01.1 --date 2026-10-20
```

### `progress.json` 里 `repo` 还是 `__REPO_SLUG__`

**原因**：本地没有配置 git remote，脚本取不到 `owner/repo`。

**解决**：

```powershell
git remote add origin git@github.com:你的用户名/ai-network-lab.git
python scripts/build_progress.py
```

或者设环境变量：

```powershell
$env:DSH_REPO_SLUG = "你的用户名/ai-network-lab"
python scripts/build_progress.py
```

## Actions 类

### Actions 页面什么都没有

**原因**：workflow 文件没推上去，或者仓库设置里禁用了 Actions。

**解决**：

1. 确认 `.github/workflows/progress.yml` 在仓库里（注意是 `.github` 不是 `github`）
2. Settings → Actions → General → 确认是 `Allow all actions`

### 报错 `403` / `Resource not accessible by integration`

**原因**：`GITHUB_TOKEN` 只有读权限。

**解决**：Settings → Actions → General → Workflow permissions → **Read and write permissions** → Save。

然后重新跑一次：Actions → progress → Run workflow。

### 提交了两次，第二次是机器人

正常。第一次是你的提交，第二次是机器人把 `progress.json` 写回来。**这是设计行为。**

### 机器人提交失败，报 `protected branch`

**原因**：`main` 开了分支保护。

**解决**：Settings → Branches → 删掉保护规则，或者给 `github-actions[bot]` 加白名单。

## 显示类

### 徽章不显示 / 显示 `invalid`

**原因**：shields.io 读不到 `progress.json`。

**检查**：直接访问

```
https://raw.githubusercontent.com/你的用户名/ai-network-lab/main/progress.json
```

- 404 → 文件不在 main 分支，或仓库是 private
- 能打开 → shields 缓存问题，等 5 分钟

### README 里进度区没更新

**原因**：`<!-- PROGRESS:START -->` 或 `<!-- PROGRESS:END -->` 标记被删了。

**解决**：把这两个标记加回去，位置随意，脚本会替换它们之间的内容。

## 环境自检

一条命令检查所有依赖：

```powershell
python --version; git --version; python -c "import json,sys;print('json ok')"
```

然后在仓库根目录跑：

```powershell
python scripts/build_progress.py
```

看到 `[ok] N/112 (x%)` 就说明脚本链路没问题。

---

> 还是解决不了？用 `checkin.py note` 把现象记下来，然后去仓库开一个 Issue。**记录失败的过程本身就是学习。**
