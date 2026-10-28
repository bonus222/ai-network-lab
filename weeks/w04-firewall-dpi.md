# W04 · 防火墙与 DPI：检测到底在检测什么

> **阶段一 · 基础层** ｜ 预计 7–9 小时 ｜ 前置：[W02](w02-tls-https.md) [W03](w03-proxy-model.md)
>
> [← W03](w03-proxy-model.md) ｜ [W05 →](w05-shadowsocks.md)

## 为什么学这个

这是整条路线的**分水岭**。前面三周学的都是「正常的网络」，这一周开始学「对手」。

学完这一周，你脑子里应该有一张表：**每一种封锁手法，它在看什么，什么能骗过它**。后面 12 周的所有协议，都是在填这张表的「反制」列。

## 核心概念

### 1. 三代防火墙

| 代际 | 看什么 | 例子 | 弱点 |
|:--|:--|:--|:--|
| 包过滤（无状态） | 五元组：源/目的 IP、端口、协议 | 早期 iptables | 不跟踪连接，容易误伤 |
| 状态检测 | 五元组 + 连接状态表 | conntrack、现代防火墙 | 仍看不到应用层 |
| 应用层网关 / DPI | **应用层内容与行为** | GFW、企业上网行为管理 | 算力贵，加密后看不见内容 |

DPI（Deep Packet Inspection）不是一种技术，是**一类技术**：在中间盒里解析到应用层，做匹配、统计、分类。

### 2. 七种检测手法

| # | 手法 | 它观察什么 | 典型表现 |
|:--:|:--|:--|:--|
| 1 | IP / 端口封锁 | 目的地址 | 直接连不上 |
| 2 | DNS 污染 | DNS 查询的域名 | 返回错误 IP，或抢在真响应前伪造 |
| 3 | SNI 关键字阻断 | ClientHello 里的 `server_name` | 握手到一半被 RST |
| 4 | TCP RST 注入 | 连接元组 | 双方都收到伪造的 RST，连接被强杀 |
| 5 | 流量特征识别 | 包长分布、熵、时序、上下行比例 | 连接能用但很快被掐 |
| 6 | 主动探测 | 主动连你的服务器，看它怎么回应 | 服务器「露馅」后被封 IP |
| 7 | TLS 指纹（JA3/JA4） | ClientHello 的字段组合 | 非浏览器指纹被区别对待 |

### 3. 为什么「RST 注入」这么有效

审查方不需要阻断链路，只需要**伪造一个 RST 包**发给双方。双方都以为对方要断开，于是连接被关闭。

- 成本极低（一个包）
- 不需要在链路上做队列
- 对 TCP 天然有效（TCP 没有「验证 RST 来源」的机制）

**这解释了为什么后来的协议都想往 UDP / QUIC 走**——UDP 没有 RST 这个概念。

### 4. 熵检测：为什么「随机」反而是特征

加密后的数据看起来是随机的。但**正常 TLS 流量并不完全随机**：

- TLS 记录头是固定格式（`0x17 0x03 0x03` + 长度）
- 包长分布有明显的峰（受 MSS、应用写入模式影响）
- 时序有规律（请求-响应节奏）

而一个「纯随机流」的协议，首包就是密文、没有握手、包长均匀分布——这在统计上**非常显眼**。

> 这是理解 W05 的关键：**Shadowsocks 的问题不是加密不够强，而是它「太干净了」。**

### 5. 主动探测

被动观察有极限。于是审查方会**主动出击**：

1. 发现一个可疑 IP:端口
2. 用各种方式去连它：正常握手、残缺握手、重放旧包、发垃圾数据
3. 观察响应：像代理？像网站？还是直接超时？

「像网站」和「超时」都是安全的；**「返回了一个奇怪的错误」才是最危险的**——这直接证明了这是个代理。

## 任务清单

- [ ] T04.1 在 Windows 上用 `New-NetFirewallRule -DisplayName "block-8080" -Direction Outbound -Protocol TCP -LocalPort 8080 -Action Block` 建一条出站阻断，验证后删除
- [ ] T04.2 抓包时过滤 `tcp.flags.reset == 1`，想办法触发一次（访问一个被阻断的域名），观察 RST 由谁发出
- [ ] T04.3 读 gfw.report 上的《How China Detects and Blocks Shadowsocks》，做一页笔记
- [ ] T04.4 做出你自己的「检测手法 → 观察什么 → 反制思路」三列表（至少 7 行）
- [ ] T04.5 `[研究]` 用 `clumsy`（Windows）或 `tc netem`（Linux）模拟 5% 丢包 + 100ms 延迟，观察 TLS 握手需要多久、会不会失败
- [ ] T04.6 写 300 字：如果让你设计一个审查系统，预算有限，你优先部署哪三种检测？为什么？

## 实验：亲手封掉一个端口

```powershell
# 1. 先确认端口通
Test-NetConnection -ComputerName example.com -Port 443

# 2. 加一条出站阻断（把 443 换成一个你正在用的测试端口，别封 443）
New-NetFirewallRule -DisplayName "block-test" -Direction Outbound -Protocol TCP -LocalPort 8080 -Action Block

# 3. 验证：应该超时
Test-NetConnection -ComputerName 127.0.0.1 -Port 8080

# 4. 清理（重要！）
Remove-NetFirewallRule -DisplayName "block-test"
```

> 体验一下「包过滤」这一层的效果：连接直接超时，没有任何错误信息。**这就是最朴素的封锁**，也是后面所有「伪装」要绕过的第一道墙。

## 自测

1. 无状态包过滤和有状态检测的区别是什么？为什么后者更省规则？
2. RST 注入为什么不需要在链路上排队？它利用了 TCP 的什么特点？
3. 为什么「加密到完全随机」反而会被识别？正常 TLS 流量有哪些「不随机」的特征？
4. 主动探测和被动观察的本质区别是什么？
5. 如果一个协议对**所有**非法连接都直接超时，它对主动探测的抵抗性如何？代价是什么？

## 延伸阅读

- gfw.report：*Research* 栏目全部文章
- 《Examining How the Great Firewall Discovers Hidden Circumvention Servers》（2015）
- RFC 793 / RFC 9293 中关于 RST 的处理
- censorship.ai 的 *Bibliography*

---

> 打卡：`python scripts/checkin.py done T04.1`
> 阶段门：完成 W01–W04 后，回到 [ROADMAP](../ROADMAP.md#阶段一--基础层w1w4) 做一次自检。
