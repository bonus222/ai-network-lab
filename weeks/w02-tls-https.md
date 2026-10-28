# W02 · TLS 与 HTTPS 握手

> **阶段一 · 基础层** ｜ 预计 6–8 小时 ｜ 前置：[W01](w01-packet-journey.md)
>
> [← W01](w01-packet-journey.md) ｜ [W03 →](w03-proxy-model.md)

## 为什么学这个

今天的抗审查协议，**绝大多数都是「假装成 TLS」**。所以你必须先彻底搞懂真正的 TLS 长什么样——包括它哪里是明的、哪里是暗的。

这一周的核心结论只有一句：**TLS 加密了内容，但 ClientHello 里的 SNI 是明文的。** 这一句话解释了后面一半的封锁手段。

## 核心概念

### 1. 对称与非对称的分工

- **非对称**（RSA / ECDHE）：用来**协商**出一个临时密钥，慢，但不用事先共享秘密
- **对称**（AES-GCM / ChaCha20-Poly1305）：用协商出的密钥**加密数据**，快
- TLS 1.3 强制使用 **ECDHE**（前向保密：私钥泄露也解不开历史流量）

### 2. 证书链与信任

```
根 CA（系统内置，自签名）
  └── 中间 CA（由根签发）
        └── 服务器证书（由中间 CA 签发，含域名 SAN）
```

浏览器验证的是：**这条链能不能走到一个我信任的根**，以及证书里的域名是否匹配、是否过期、是否被吊销。

### 3. 握手流程差异

| | TLS 1.2 | TLS 1.3 |
|:--|:--|:--|
| 往返 | 2-RTT | 1-RTT（恢复时 0-RTT） |
| ClientHello 之后 | 大量明文（ServerHello、Certificate、ServerKeyExchange） | **ServerHello 之后全部加密** |
| 密钥交换 | 可选 RSA / ECDHE | 只有 (EC)DHE |
| 密码套件 | 一大堆历史包袱 | 精简为 5 个 AEAD 套件 |

**关键**：即使 TLS 1.3 加密了证书，**ClientHello 仍然是明文**，因为服务器要先看到 SNI 才知道该出示哪张证书（虚拟主机）。

### 4. ClientHello 里有什么

| 字段 | 作用 | 是否明文 |
|:--|:--|:--|
| `random` | 随机数，参与密钥派生 | 明文 |
| `cipher_suites` | 客户端支持的加密套件列表 | 明文 |
| `extensions` → **`server_name` (SNI)** | 我要访问哪个域名 | **明文** |
| `extensions` → `ALPN` | 我要用 h2 还是 http/1.1 | 明文 |
| `extensions` → `supported_versions` | 支持 TLS 1.3 吗 | 明文 |

**这张表的明文部分，就是「TLS 指纹」（JA3/JA4）的原材料**——不同客户端（Chrome / Firefox / curl / Go）的字段顺序、套件列表、扩展组合都不一样，拼起来就是一个近乎唯一的指纹。

### 5. ECH（Encrypted Client Hello）

思路：把真实的 SNI 用服务器公钥加密，外面套一个「外层 SNI」（通常是 CDN 的通用域名）。
为什么没普及：需要 DNS 的 `HTTPS` 记录分发公钥、需要 CDN 全链路支持、外层 SNI 本身仍可能被针对。

## 任务清单

- [ ] T02.1 用 `openssl s_client -connect example.com:443 -servername example.com -showcerts` 打印证书链，找出根 CA 是谁
- [ ] T02.2 在 Wireshark 里过滤 `tls.handshake.extensions_server_name`，确认 **SNI 是明文可见的**，截图
- [ ] T02.3 分别用 `curl --tlsv1.2 -v` 和 `curl --tlsv1.3 -v` 访问同一站点，数一数握手往返次数差异
- [ ] T02.4 用 `openssl x509 -in cert.pem -text -noout` 查看 SAN 字段与有效期
- [ ] T02.5 用 `curl --resolve example.com:443:<某个IP>` 强制指定 IP，观察证书校验是否仍然通过（以及为什么）
- [ ] T02.6 写 200 字回答：SNI 为什么注定是审查抓手？ECH 想解决什么，代价是什么？

## 实验：亲眼看见 SNI

1. 开 Wireshark，过滤 `tls.handshake.type == 1`（ClientHello）。
2. 浏览器访问任意 HTTPS 站点。
3. 展开 `Transport Layer Security → TLSv1.3 Record Layer → Handshake Protocol: Client Hello → Extensions`。
4. 找到 `server_name`，它的值就是你要访问的域名，**完全明文**。

这一步的震撼感很重要：你以为「HTTPS 加密了」，但**你访问了哪个网站，路上所有中间人都知道**。

> 再做一个对照：用 `curl` 和用 Chrome 访问同一个站点，把两次 ClientHello 的 `cipher_suites` 和 `extensions` 列表对比。差异就是「指纹」。

## 自测

1. TLS 1.3 加密了证书，那审查方还能靠什么识别你访问的域名？（提示：看上面那张表）
2. 为什么 TLS 1.3 要去掉 RSA 密钥交换？
3. `--resolve` 指定了 IP，为什么证书校验还能过？（提示：证书绑的是域名，不是 IP）
4. ALPN 协商失败会怎样？
5. 会话恢复（session ticket / PSK）为什么能省一个 RTT？它有什么隐私代价？

## 延伸阅读

- RFC 8446（TLS 1.3）——重点读 4.1.2 Client Hello
- RFC 9180（HPKE，ECH 的密码学基础）
- Cloudflare Blog：*Encrypted Client Hello: the future of SNI privacy*
- 《Bulletproof SSL and TLS》第 2–4 章

---

> 打卡：`python scripts/checkin.py done T02.1`
