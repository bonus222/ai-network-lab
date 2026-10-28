# W09 · VPS 选型与初始化

> **阶段三 · 工程层** ｜ 预计 6–8 小时 ｜ 前置：[W08](w08-reality-quic.md)
>
> [← W08](w08-reality-quic.md) ｜ [W10 →](w10-deploy-reality.md)

## 为什么学这个

协议选对了，线路选错了，体验照样稀烂。这一周是**工程周**：你会明白为什么同样 100Mbps 的机器，有人用着像专线，有人卡成 PPT。

## 核心概念

### 1. 线路：决定体验的第一因素

从中国大陆出去，常见的「回国/出国」线路质量排序（大致）：

| 线路 | 代号 | 特点 | 价格 |
|:--|:--|:--|:--|
| **IPLC / IEPL** | 专线 | 不过公网，几乎不丢包，延迟稳定 | ¥¥¥¥ |
| **CN2 GIA** | AS4809 全程 | 去回程都走 CN2，晚高峰依然稳 | ¥¥¥ |
| **CN2 GT** | AS4809 半程 | 只有去程或回程走 CN2 | ¥¥ |
| **CUII / 9929** | 联通精品网 | 联通用户体验好 | ¥¥ |
| **CMI** | AS58453 移动国际 | 移动用户友好 | ¥ |
| **163 骨干** | ChinaNet | 便宜，晚高峰爆炸 | ¥ |

**关键认知**：**回程比去程重要**。你发的请求很小（去程无所谓），你收的数据很大（回程决定体验）。很多「便宜 VPS」去程 CN2、回程 163，晚上就废了。

### 2. 原生 IP vs 广播 IP

- **原生 IP**：该 IP 的 whois 归属地与机房实际位置一致
- **广播 IP**：把别处的 IP 段广播到本地机房

对普通代理影响不大，但**对流媒体解锁和平台风控影响巨大**（W12 会展开）。买之前问清楚，或者买完自己查。

### 3. ASN：IP 的「户口」

每个 IP 属于一个自治系统（AS），比如：

| ASN | 归属 | 类型 |
|:--|:--|:--|
| AS16509 | Amazon AWS | 机房 |
| AS14061 | DigitalOcean | 机房 |
| AS20473 | Vultr / Choopa | 机房 |
| AS4134 | China Telecom 163 | 运营商 |
| AS4809 | China Telecom CN2 | 运营商 |

查法：`whois <IP>` 或 [ipinfo.io](https://ipinfo.io)。

### 4. 初始化加固清单

刚买的机器默认是「裸奔」的。按顺序做：

1. **改 SSH 端口**（可选）+ **只用密钥登录** + 禁用 root 密码登录
2. **防火墙**只开必要端口（22 + 443）
3. **fail2ban** 防爆破
4. **时间同步**（`systemd-timesyncd`）——VMess 对时间敏感，差 90 秒就失败
5. **BBR** 拥塞控制（对高延迟链路提升明显）
6. **IPv6** 按需开启（有时是泄漏源，有时是救命通道）

## 任务清单

- [ ] T09.1 列出 3 家候选 VPS，做成对比表：机房位置 / 线路 / 带宽 / 流量 / 价格 / 是否原生 IP
- [ ] T09.2 买一台（**务必月付**，先测一个月再考虑年付）
- [ ] T09.3 配置 SSH 密钥登录，`PasswordAuthentication no`，验证能登进去后再关掉密码
- [ ] T09.4 配防火墙：只放行 SSH 端口和 443，其余全 drop，验证生效
- [ ] T09.5 开启 BBR：`net.core.default_qdisc=fq` + `net.ipv4.tcp_congestion_control=bbr`，用 `sysctl net.ipv4.tcp_congestion_control` 验证
- [ ] T09.6 跑 `bench.sh` 或 `iperf3` 测一次基线，把结果存进 `results/w09-baseline.txt`
- [ ] T09.7 `[研究]` 用 `mtr -rwzbc 100 <你的IP>` 对比去程和回程经过的 AS，找出瓶颈在哪一跳

## 实验：给你的机器做体检

```bash
# 系统与内核
uname -a && cat /etc/os-release

# 虚拟化类型（KVM / OpenVZ 决定能不能改内核）
systemd-detect-virt

# 磁盘 IO
dd if=/dev/zero of=test bs=64k count=16k conv=fdatasync

# 到国内三大运营商的回程
mtr -rwzbc 50 223.5.5.5    # 阿里 DNS（电信/联通/移动混合）
mtr -rwzbc 50 119.29.29.29 # 腾讯 DNS

# BBR 是否生效
sysctl net.ipv4.tcp_congestion_control
```

> 判读：如果回程在**第 5–8 跳**就出现 30%+ 丢包或 200ms+ 延迟跳变，这台机器晚高峰基本没救。

## 自测

1. 为什么说「回程比去程重要」？
2. CN2 GT 和 CN2 GIA 的区别是什么？怎么判断自己买的是哪个？
3. 原生 IP 和广播 IP 对代理本身有影响吗？对什么有影响？
4. OpenVZ 架构为什么可能开不了 BBR？
5. 为什么强烈建议先月付？

## 延伸阅读

- 各大 VPS 测评站的「回程路由」文章（搜 `mtr 回程 分析`）
- Cloudflare Blog：*BBR congestion control*
- `bench.sh` 项目 README

---

> 打卡：`python scripts/checkin.py done T09.1`
