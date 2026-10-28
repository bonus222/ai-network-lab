# GitHub 从零到第一次 push

> 目标：把 `ai-network-lab` 推上 GitHub，并让「改一个勾选 → 徽章自动更新」这条链路跑通。
>
> 你已经有账号（`bonus222`），但很少操作。本文按 Windows 写，命令可以直接复制。

---

## 0. 先搞懂三个词

| 词 | 含义 | 类比 |
|:--|:--|:--|
| **仓库（Repository）** | 一个文件夹 + 它的全部历史版本 | 一个带时间机器的文件夹 |
| **提交（Commit）** | 一次「存档」，记录你改了什么 | 游戏存档点 |
| **远程（Remote）** | GitHub 上的那份副本 | 云备份 |

日常操作就三步：**改文件 → 提交 → 推送**。

---

## 1. 装 Git

下载：<https://git-scm.com/download/win>（选 64-bit）。

安装时一路默认即可，只有一处建议改：

> **Adjusting your PATH environment** → 选 **Git from the command line and also from 3rd-party software**（默认就是这个）

装完**新开一个 PowerShell 窗口**（旧窗口不认新 PATH），验证：

```powershell
git --version
```

看到 `git version 2.4x.x` 就成功。

---

## 2. 配置身份

每台机器只需做一次。Git 要知道「这个提交是谁做的」：

```powershell
git config --global user.name "bonus222"
git config --global user.email "1538413776@qq.com"
git config --global init.defaultBranch main
git config --global core.autocrlf true
```

检查：

```powershell
git config --global --list
```

> `core.autocrlf true` 是 Windows 专用：自动处理换行符差异，避免每次提交都提示 `LF will be replaced by CRLF`。

---

## 3. 配 SSH 密钥（推荐）

SSH 配好之后，push 不用每次输密码。

### 3.1 生成密钥

```powershell
ssh-keygen -t ed25519 -C "1538413776@qq.com"
```

连按三次回车（路径默认、密码留空）。

得到两个文件：

```
C:\Users\<你>\.ssh\id_ed25519       ← 私钥，绝对不要外传
C:\Users\<你>\.ssh\id_ed25519.pub   ← 公钥，可以给任何人
```

### 3.2 把公钥贴到 GitHub

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | Set-Clipboard
```

然后浏览器打开：**GitHub → 右上角头像 → Settings → SSH and GPG keys → New SSH key**

- Title：随便写，比如 `my-pc`
- Key type：`Authentication Key`
- Key：粘贴（Ctrl+V）
- 点 **Add SSH key**

### 3.3 验证

```powershell
ssh -T git@github.com
```

第一次会问 `Are you sure you want to continue connecting?` → 输入 `yes` 回车。

成功会显示：

```
Hi bonus222! You've successfully authenticated, but GitHub does not provide shell access.
```

> **连不上的话**：22 端口可能被挡。试 443 端口：
>
> ```powershell
> ssh -T -p 443 git@ssh.github.com
> ```
>
> 能通就再写一个配置文件 `C:\Users\<你>\.ssh\config`（无扩展名）：
>
> ```
> Host github.com
>   HostName ssh.github.com
>   Port 443
>   User git
> ```

---

## 4. 在 GitHub 上建仓库

1. 打开 <https://github.com/new>
2. **Repository name**：`ai-network-lab`
3. **Description**：`16 周网络对抗实验室 · 从数据包到 REALITY`
4. 选 **Public**
5. ⚠️ **不要勾** "Add a README file"、不要选 .gitignore、不要选 license
   （本地已经有了，勾了会冲突）
6. 点 **Create repository**

建完页面会显示一堆命令，先别管，往下走。

---

## 5. 把本地仓库推上去

### 5.1 先确认你在这里

```powershell
cd "D:\dsh工作区类别\工作区\ai-network-lab"
```

### 5.2 初始化 + 提交 + 推送

逐行执行：

```powershell
git init
git add -A
git commit -m "init: 16 周网络对抗实验室"
git remote add origin git@github.com:bonus222/ai-network-lab.git
git branch -M main
git push -u origin main
```

**每一行的作用**：

| 命令 | 作用 |
|:--|:--|
| `git init` | 把当前文件夹变成 git 仓库（生成隐藏的 `.git/`） |
| `git add -A` | 把所有文件加入「待提交」 |
| `git commit -m "..."` | 存一个档，附一句说明 |
| `git remote add origin ...` | 告诉 git「远程仓库在哪」 |
| `git branch -M main` | 把主分支命名为 `main`（GitHub 默认） |
| `git push -u origin main` | 推上去，并记住这个默认目标 |

> 第一次 push 可能比较慢（国内直连 GitHub 经常卡）。如果卡住超过 1 分钟：
> ```powershell
> git config --global http.lowSpeedLimit 1000
> git config --global http.lowSpeedTime 60
> ```
> 或者用你已有的代理：
> ```powershell
> git config --global http.https://github.com.proxy http://127.0.0.1:7890
> ```

推送成功后刷新仓库页面，应该能看到 README 渲染出来。

---

## 6. ⚠️ 打开 Actions 写权限（关键一步，不做必失败）

默认情况下，GitHub Actions 里的 `GITHUB_TOKEN` **只有读权限**，机器人无法把更新后的 `progress.json` 提交回仓库。

设置路径：

> **仓库页 → Settings → Actions → General → 拉到最下面 Workflow permissions**
> → 选 **Read and write permissions**
> → 点 **Save**

同一页上方，确认 **Actions permissions** 是 `Allow all actions and reusable workflows`。

---

## 7. 验证整条链路

### 7.1 手动触发一次

> **仓库页 → Actions 标签 → 左侧 `progress` → 右侧 `Run workflow` → `Run workflow`**

等 20 秒左右，应该看到一个绿色 ✓。

### 7.2 检查产物

回到仓库首页：

- 徽章应该显示 `进度 2.7%`
- 日历图应该有一格绿色（你打卡的那天）
- `progress.json`、`assets/progress.svg` 应该已被机器人更新

### 7.3 走一遍真实打卡

```powershell
cd "D:\dsh工作区类别\工作区\ai-network-lab"
python scripts/checkin.py done T01.4
git add -A
git commit -m "checkin: T01.4"
git push
```

回到 GitHub，等 Action 跑完，首页进度应该从 3/112 变成 4/112。

---

## 8. 它是怎么自动更新的

```
你 push 一个勾选
      ↓
.github/workflows/progress.yml 被触发
      ↓
在 GitHub 的机器上跑 python scripts/build_progress.py
      ↓
重新生成 progress.json + assets/*.svg + README 进度区
      ↓
发现有变化 → 以 checkin-bot 身份提交并 push 回你的仓库
      ↓
shields.io 读取 progress.json → 徽章数字变化
```

两个细节：

- **为什么不会死循环**：workflow 里有 `if: github.actor != 'github-actions[bot]'`，机器人自己的提交不会再触发。
- **徽章为什么可能慢**：shields.io 有缓存，通常 5 分钟内刷新。

---

## 9. 日常 5 步循环

```powershell
cd "D:\dsh工作区类别\工作区\ai-network-lab"   # 1. 进目录
python scripts/checkin.py next                  # 2. 看下一步做什么
#   …… 学习、做实验 ……
python scripts/checkin.py done T03.2            # 3. 打卡（顺便刷新进度）
git add -A                                      # 4. 暂存
git commit -m "checkin: T03.2"                  # 5. 提交并推送
git push
```

**懒人版**（一条命令）：

```powershell
python scripts/checkin.py done T03.2; git add -A; git commit -m "checkin"; git push
```

**完全不想开电脑？** 直接手机上：

1. 打开 `github.com/bonus222/ai-network-lab`
2. 进 `weeks/w03-proxy-model.md`
3. 点右上角铅笔图标 → 把 `- [ ] T03.2` 改成 `- [x] T03.2`
4. 拉到底 → **Commit changes**

Actions 会自动补上打卡日期。

---

## 10. 常见错误对照表

| 报错 / 现象 | 原因 | 解决 |
|:--|:--|:--|
| `git: command not found` | PATH 没生效 | 关掉 PowerShell 重开 |
| `Permission denied (publickey)` | SSH key 没配好 | 重做第 3 步；`ssh -T git@github.com` 先测通 |
| `remote origin already exists` | 之前加过 remote | `git remote set-url origin <新地址>` |
| `failed to push some refs` | 远程有你本地没有的提交 | `git pull --rebase origin main` 再 push |
| `LF will be replaced by CRLF` | Windows 换行符 | 只是警告，忽略；或设 `core.autocrlf true` |
| Actions 报 `403` / `Resource not accessible` | 没开写权限 | 重做第 6 步 |
| Actions 成功但徽章不变 | shields 缓存 | 等 5 分钟，或强刷 `Ctrl+F5` |
| 徽章显示 `OWNER/REPO` | `__REPO_SLUG__` 没被替换 | 本地跑一次 `python scripts/build_progress.py` 再 push |
| 勾选了但进度没变 | 格式不对 | 必须是 `- [x] T03.2`，方括号里一个 x，编号紧跟 |
| `python: command not found` | 没装 Python | 装 Python 3.10+，勾选 "Add to PATH" |
| 中文乱码 | 终端编码 | PowerShell 执行 `chcp 65001` |

---

## 11. 改错了怎么回滚

**撤销上一次提交（保留改动）**：

```powershell
git reset --soft HEAD~1
```

**丢弃所有未提交的改动**：

```powershell
git restore .
```

**看历史**：

```powershell
git log --oneline -10
```

**回到某个历史版本**（谨慎）：

```powershell
git revert <commit-id>
```

> 原则：**已经 push 的东西，用 `revert` 而不是 `reset`**——后者会给协作者（包括 Actions）制造麻烦。

---

## 12. 建议接下来做的三件事

1. **加一个仓库描述和 topics**：Settings 页面顶部可以改 Description；右侧 About 里加 `networking` `censorship-circumvention` `learning-roadmap`。
2. **开 Issues 记问题**：遇到卡壳的地方开一个 issue，解决后关掉。这比记在脑子里靠谱。
3. **用 Projects 做看板**（可选）：把 16 周做成卡片，拖来拖去。

---

## 附：私有仓库怎么办

如果你后来觉得公开不合适：

> Settings → 最下面 **Danger Zone → Change repository visibility → Change to private**

注意：私有仓库的 shields.io 徽章**读不到** `progress.json`（因为 raw 地址需要认证），徽章会失效。届时可以改成静态徽章，或者干脆不放徽章。
