# 阅读清单

> 按周次排。标 ⭐ 的是必读，其余按兴趣选。
>
> **读论文的方法**见 [W15](../weeks/w15-papers-toy-protocol.md)：只回答五个问题——问题、威胁模型、方法、评估、局限。

## 论文

| # | 论文 | 年份 | 读它为了 | 对应周 |
|:--:|:--|:--:|:--|:--:|
| 1 ⭐ | *Detecting TLS Tunnels in the Wild* (Frolov & Wustrow, USENIX Security) | 2019 | 理解 TLS-in-TLS 为什么被统计特征识别 | W06 |
| 2 ⭐ | *Examining How the Great Firewall Discovers Hidden Circumvention Servers* (IMC) | 2015 | 主动探测的完整方法论 | W04 / W14 |
| 3 | *How China Detects and Blocks Shadowsocks* (gfw.report) | 2020 | 真实世界的 SS 检测手段 | W05 |
| 4 | *The Parrot is Dead: Observing Unobservable Network Communications* (IEEE S&P) | 2013 | 「不可观测性」的理论边界 | W05 / W15 |
| 5 | *Detecting Probe-Resistant Proxies* (Fifield et al., NDSS) | 2015 | 探测抵抗的评估方法 | W14 |
| 6 | *Domain Fronting is Dead, Long Live Domain Fronting* | 2018 | 为什么依赖第三方基础设施不可持续 | W07 |
| 7 | *TLS Fingerprinting in the Wild* / JA3 原始提案 | 2017+ | 指纹是怎么被工程化的 | W08 |
| 8 | *Geneva: Evolving Censorship Evasion* | 2019 | 用遗传算法自动发现规避策略 | W15 |

## RFC 与规范

| 编号 | 标题 | 什么时候读 |
|:--|:--|:--|
| RFC 9293 | TCP | W01（只读握手与 RST 部分） |
| RFC 1035 | DNS | W01（只读查询格式） |
| RFC 8446 | TLS 1.3 | W02 ⭐（重点 4.1.2 Client Hello） |
| RFC 1928 | SOCKS5 | W03 ⭐（§3 §4 必须逐字读） |
| RFC 9113 | HTTP/2 | W07（CONNECT 语义） |
| RFC 9000 | QUIC | W08（只需知道它跑在 UDP 上） |
| RFC 9180 | HPKE | W02（ECH 的密码学基础，选读） |

## 官方文档（比博客可靠）

| 项目 | 读什么 | 对应周 |
|:--|:--|:--:|
| [Xray-core](https://xtls.github.io/) | VLESS、XTLS、REALITY、Routing、DNS | W06–W11 |
| [sing-box](https://sing-box.sagernet.org/) | Inbound/Outbound、DNS、FakeIP | W06 / W11 |
| [Hysteria2](https://v2.hysteria.network/) | 协议设计与 Brutal 拥塞控制 | W08 |
| [uTLS](https://github.com/refraction-networking/utls) | ClientHello 定制 | W08 |
| [JA4](https://github.com/FoxIO-LLC/ja4) | 指纹规范 | W08 / W12 |
| [Trojan](https://github.com/trojan-gfw/trojan) | protocol.md | W07 |

## 持续更新的情报源

| 来源 | 内容 | 频率 |
|:--|:--|:--|
| [gfw.report](https://gfw.report) | 中国网络审查的实测研究 | 不定期，质量高 |
| [censorship.ai](https://censorship.ai) | 抗审查研究的论文索引 | —— |
| [OONI](https://ooni.org/reports/) | 全球网络干扰测量报告 | 季度 |
| [USENIX Security](https://www.usenix.org/conference/usenixsecurity24) / [NDSS](https://www.ndss-symposium.org/) / [FOCI](https://foci.community/) | 顶会论文 | 每年 |
| [PT Project](https://github.com/net4people/bbs) | 实践者讨论区 | 活跃 |

## 书

| 书 | 适合 | 说明 |
|:--|:--|:--|
| 《计算机网络：自顶向下方法》 | W01–W02 | 分层讲得最清楚 |
| 《HTTP 权威指南》 | W03 | 代理那章必读 |
| 《Bulletproof SSL and TLS》 | W02 | TLS 细节，偏厚 |
| 《Systems Performance》 | W13 | 指标与统计方法 |

---

> 建议：**不要一次全读完**。每周只读本周标 ⭐ 的那一篇，读完写 5 句话的笔记放进 `checkins/notes.md`。
