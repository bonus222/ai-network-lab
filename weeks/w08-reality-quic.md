# W08 · REALITY / uTLS / QUIC：借一张真证书

> **阶段二 · 协议层** ｜ 预计 8–10 小时 ｜ 前置：[W07](w07-trojan.md)
>
> [← W07](w07-trojan.md) ｜ [W09 →](w09-vps.md)

## 为什么学这个

到 W07 为止，所有方案都卡在同一个问题上：**证书**。

- 自签证书 → 一眼假
- 自己域名 + Let's Encrypt → 真的，但域名会被 SNI 黑名单针对

REALITY 的答案很激进：**我不需要自己的证书，我借一个真实网站的。**

这一周是协议线的收官，也是整个路线里技术密度最高的一周。

## 核心概念

### 1. REALITY 的核心把戏

服务端不持有任何「自己的」证书。它做的是：

```
客户端 ClientHello（SNI = www.真实的网站.com）
        │
        ▼
   ┌─────────┐   ① 尝试用私钥解密 ClientHello 里的认证数据
   │ REALITY │
   │  服务端  │   ② 解密成功？→ 劫持这条连接，当作代理会话
   └─────────┘   ③ 解密失败？→ 把整条 TCP 连接转发给真实的 www.真实的网站.com
```

**对探测者的效果**：

| 探测者做什么 | 看到什么 |
|:--|:--|
| 标准 TLS 握手 | 一个**完全正常**的握手，证书是那个真实网站的**真证书** |
| 发 HTTP 请求 | 那个真实网站的**真实页面** |
| 发垃圾数据 | 真实网站的反应（404 / 400） |
| 反复扫描 | 和扫一个普通网站没区别 |

这是「不可区分性」的一次真正的工程实现：**探测者拿不到任何区分信号，因为他连的就是真网站。**

### 2. 认证藏在哪

客户端用**服务端的 X25519 公钥**，把认证信息加密后塞进 ClientHello 的某个字段（具体是 `session_id` 一类的位置）。

- 服务端用私钥尝试解密
- 解得开 → 是自己人
- 解不开 → 当普通流量转发

关键：这段加密数据在**外观上是随机的**，和正常的 session_id 无法区分。

### 3. uTLS：指纹也得是假的

就算协议对了，如果 ClientHello 的字段组合不像浏览器，JA3/JA4 指纹仍然会暴露你。

**uTLS** 是 Go 的一个库，允许完全自定义 ClientHello：

- 密码套件列表及**顺序**
- 扩展列表及顺序
- `key_share` 的椭圆曲线组合
- GREASE 值（Chrome 用来防僵化的随机扩展）
- ALPN 顺序

REALITY 客户端默认就用 uTLS 模仿 Chrome 的指纹。

**JA3 / JA4 是什么**：

- **JA3**：把 ClientHello 的 `version,ciphers,extensions,elliptic_curves,ec_point_formats` 拼成字符串再取 MD5
- **JA4**：JA3 的改进版，抗随机化、更能区分真实客户端

访问 [tlsfingerprint.io](https://tlsfingerprint.io) 可以看到你自己的指纹。

### 4. QUIC 系：换个维度打

TCP 系协议都在「怎么伪装 TCP」上内卷。另一条路是：**不用 TCP**。

| 协议 | 传输 | 特点 |
|:--|:--|:--|
| **Hysteria2** | QUIC (UDP) | 自定义拥塞控制（Brutal），按设定带宽**忽略丢包**猛推 |
| **TUIC** | QUIC (UDP) | 更轻，0-RTT，多路复用 |
| Shadowsocks 2022 | TCP/UDP | 老牌，改进版 |

**优势**：

- QUIC 是加密的，天然抗明文 DPI
- 没有 TCP 的 RST 注入问题
- 高丢包、高延迟链路上，Brutal 的暴力带宽策略效果惊人

**代价**：

- UDP 在很多网络里被 QoS 限速甚至完全阻断
- 部分运营商对 UDP 大流量有特殊照顾（你懂的）
- 晚高峰 UDP 丢包可能比 TCP 更严重

> 经验结论：**TCP 系求稳，QUIC 系求快**。两条腿走路，按网络环境切换。

### 5. 四协议对照（这一周的产出）

| | SS | VMess+TLS | Trojan | REALITY |
|:--|:--|:--|:--|:--|
| 需要域名 | ❌ | ✅ | ✅ | ❌ |
| 需要证书 | ❌ | ✅ | ✅（公共 CA） | ❌（借） |
| 抗 SNI 封锁 | ❌ | ❌ | ❌ | ✅ |
| 抗主动探测 | ❌ | 中 | ✅（回落） | ✅✅ |
| 抗 TLS-in-TLS 检测 | — | ❌ | 中 | ✅（Vision） |
| 部署复杂度 | 低 | 中 | 中 | 中高 |

## 任务清单

- [ ] T08.1 安装 Xray-core，配置一个 REALITY 入站（`dest` 选一个支持 TLS1.3 + H2 的真实站点），本地先跑通
- [ ] T08.2 访问 [tlsfingerprint.io](https://tlsfingerprint.io)，记录你常用浏览器的 JA3/JA4，存进 `results/`
- [ ] T08.3 用 `openssl s_client -connect <你的服务器>:443 -servername <dest域名>`，确认返回的证书是**目标站点的真证书**
- [ ] T08.4 写 300 字：REALITY 与「自签证书 + TLS」的本质区别是什么？为什么前者不可区分？
- [ ] T08.5 部署 Hysteria2，在模拟丢包（`clumsy` 5–10%）下对比 TCP 系协议的实际吞吐
- [ ] T08.6 完成上面那张四协议对照表，并给每一格写一句理由
- [ ] T08.7 `[研究]` 用 `nmap -sV -p 443 <你的服务器>` 扫自己的端口，看它被识别成什么服务

## 实验：让探测者无话可说

```bash
# 用浏览器指纹去握手（uTLS 的近似效果）
curl -v --tlsv1.3 https://<你的服务器>:443 --resolve <dest域名>:443:<你的服务器IP>

# 看证书链
openssl s_client -connect <你的服务器>:443 -servername <dest域名> -showcerts </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer

# 结论应该是：subject 和 issuer 都是那个真实网站的，和你毫无关系
```

> 自检问题：如果审查方把「你的服务器 IP」和「dest 域名」做了关联，会发生什么？
> 答案：会发现这个 IP 在冒充一个不属于它的域名。**所以 `dest` 要选一个本身就在大量 IP 上提供服务的站点**（比如大型 CDN 上的站点），这样「同一域名对应多个 IP」是常态。

## 自测

1. REALITY 服务端为什么不需要自己的证书？
2. 认证信息放在 ClientHello 的哪里？为什么探测者看不出来？
3. uTLS 在伪造什么？JA3 和 JA4 的区别是什么？
4. QUIC 系协议为什么天然抗 RST 注入？它又引入了什么新问题？
5. `dest` 的选择有什么讲究？选错了会怎样？

## 延伸阅读

- Xray-core 文档：*REALITY*（含设计动机与配置说明）
- uTLS 项目 README（GitHub: refraction-networking/utls）
- JA3 / JA4 规范（GitHub: FoxIO-LLC/ja4）
- Hysteria2 官方文档
- RFC 9000（QUIC 传输）

---

> 打卡：`python scripts/checkin.py done T08.1`
> 阶段门：完成 W05–W08 后，回到 [ROADMAP](../ROADMAP.md#阶段二--协议层w5w8) 做一次自检。
