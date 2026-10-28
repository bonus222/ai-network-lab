# W06 · VMess / VLESS / XTLS：套进 TLS 之后的新问题

> **阶段二 · 协议层** ｜ 预计 7–9 小时 ｜ 前置：[W05](w05-shadowsocks.md)
>
> [← W05](w05-shadowsocks.md) ｜ [W07 →](w07-trojan.md)

## 为什么学这个

Shadowsocks 被识别之后，所有人的第一反应是：**那就套一层 TLS**。

套上之后发现：**TLS 里面再跑 TLS，反而更容易被认出来。** 这就是著名的 TLS-in-TLS 问题，也是 XTLS 诞生的原因。

这一周你会理解一个反直觉的事实：**伪装得越像，细节就越重要。**

## 核心概念

### 1. VMess：自带加密的协议

VMess 是 V2Ray 的原创协议，特点：

- 用 **UUID** 标识用户，请求头里有时间戳（防重放，但也带来时钟同步问题）
- **自带加密**（AES-128-GCM / ChaCha20-Poly1305）
- 有请求头和响应头，格式比 SS 复杂
- 常见用法：VMess + TLS + WebSocket（`ws`）

问题：**自带加密 + 外层 TLS = 双重加密**。这不仅是性能浪费，更是**指纹来源**。

### 2. VLESS：把加密交出去

VLESS 的设计哲学是「**什么都不做**」：

| | VMess | VLESS |
|:--|:--|:--|
| 自带加密 | ✅ | ❌（依赖外层 TLS） |
| 头部开销 | 较大 | 极小（2 字节版本 + UUID + 少量字段） |
| 状态 | 有状态 | **无状态** |
| 时钟依赖 | 有 | 无 |

VLESS 的头部几乎是明文（UUID 在里面），**所以它必须跑在 TLS 里**，否则 UUID 会裸奔。

好处：没有双重加密，性能好，流量形态更接近「纯 TLS」。

### 3. TLS-in-TLS：伪装带来的新破绽

设想：你的代理跑在 TLS 里，而你访问的目标网站也是 TLS。

```
外层 TLS（代理自己的）
  └── 内层 TLS（你访问的网站）
```

从外面看，这条连接里**嵌着另一个 TLS 握手**。而 TLS 握手有非常固定的模式：

- ClientHello 通常 200–600 字节
- ServerHello + Certificate 通常是几个 1000+ 字节的包
- 这些包的**长度分布**和**方向交替模式**，与外层 TLS 的正常数据传输显著不同

2019 年 Frolov & Wustrow 的论文《Detecting TLS Tunnels in the Wild》证明：**仅靠包长序列，就能高准确率地区分「TLS 里跑的是普通数据」还是「TLS 里跑的是另一个 TLS」。**

> 这就是「越像越难」的含义：你伪装成 TLS，就得连 TLS 的**内部行为统计**也一起伪装。

### 4. XTLS：把内层字节直接搬过去

XTLS 的核心思路叫 **splice**（拼接）：

```
普通 VLESS+TLS：
  读密文 → 解密 → 再加密 → 写出     （两次加解密，包长被改变）

XTLS：
  读密文 → 直接写出                （零拷贝，包长保持不变）
```

因为外层和内层都是 TLS，**如果代理不做解密，直接把内层 TLS 的密文字节透传**，那么从外部看，包长分布就和「一个正常的 TLS 连接」完全一致——因为没有中间层在重新分片。

XTLS 的演进：
- 最初的 `xtls-rprx-direct`：有兼容性问题
- 后来的 **`xtls-rprx-vision`**：加入流控，解决了「splice 之后无法插入控制信息」的问题，成为现在的标准用法

### 5. 为什么还需要 REALITY

VLESS + TLS + Vision 已经很好了，但它仍然需要一个**你自己的域名和证书**。而：

- 域名要备案/解析，会被 SNI 黑名单针对
- 自签证书一眼假（证书链走不到公共 CA）
- Let's Encrypt 证书也可以用，但你的域名一旦被标记，就废了

**REALITY 解决的就是「证书从哪来」这个问题**——下周讲。

## 任务清单

- [ ] T06.1 用 `sing-box` 在本机起一个 VLESS + TLS（自签证书即可）的入站，让 `curl` 走通
- [ ] T06.2 抓包对比：SS 的首包 vs VLESS+TLS 的首包，填一张对照表
- [ ] T06.3 读 Frolov & Wustrow 论文的 Abstract + §3（方法），用 5 句话总结「它靠什么特征分类」
- [ ] T06.4 画出 TLS-in-TLS 的嵌套结构图，标出「哪一层是代理的、哪一层是网站的」
- [ ] T06.5 用 Wireshark 统计一次 TLS 会话的 **record 长度分布**（`tls.record.length`），做成直方图
- [ ] T06.6 写 200 字解释：splice 省掉的是「性能」还是「特征」？还是两者都有？
- [ ] T06.7 `[研究]` 对比开/关 Vision 时的包长分布差异

## 实验：看见「套娃」

1. 起一个 VLESS+TLS 入站（自签证书）。
2. 用这个入站访问一个 HTTPS 网站。
3. Wireshark 过滤这条连接的所有包。
4. 看 `tls.record.length` 序列——你会看到**明显不自然的分布**：一堆 ~1400 的大包，中间夹杂着特定长度的小包。

对比：直接访问同一个网站（不经过代理），record 长度分布要「自然」得多。

> 这就是「结构指纹」。它不需要解密，只需要统计。

## 自测

1. VMess 和 VLESS 最本质的区别是什么？
2. 为什么 VLESS 必须跑在 TLS 里？
3. TLS-in-TLS 靠什么被识别？为什么加密强度再高也没用？
4. splice 为什么能保持包长不变？它牺牲了什么？
5. Vision 的「流控」在解决什么问题？

## 延伸阅读

- Xray-core 文档：*VLESS*、*XTLS*、*Vision* 章节
- 《Detecting TLS Tunnels in the Wild》（Frolov & Wustrow, USENIX Security 2019）
- V2Ray 设计文档：*VMess 协议*
- sing-box 文档：*VLESS inbound*

---

> 打卡：`python scripts/checkin.py done T06.1`
