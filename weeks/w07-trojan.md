# W07 · Trojan 与「像 HTTPS」的极限

> **阶段二 · 协议层** ｜ 预计 6–8 小时 ｜ 前置：[W06](w06-vmess-vless.md)
>
> [← W06](w06-vmess-vless.md) ｜ [W08 →](w08-reality-quic.md)

## 为什么学这个

Trojan 是对「伪装成 HTTPS」这条路线最纯粹的一次尝试：**它不发明新的握手，它就用真的 TLS。**

它的优雅之处在于**回落（fallback）**——一个设计上极其聪明的防守动作。理解它，你就理解了「主动探测」该怎么防。

## 核心概念

### 1. 设计：一条真的 TLS 连接

```
客户端 → [TLS 握手，用真实域名和真实证书] → 服务端
       → [在 TLS 内部发送: 密码哈希 + SOCKS5 请求]
```

和 VLESS 的区别：

| | VLESS + TLS | Trojan |
|:--|:--|:--|
| TLS 证书 | 自签或自己的域名 | **自己的域名 + 公共 CA 签发的真证书** |
| 认证方式 | UUID（明文，靠 TLS 保护） | 密码哈希（在 TLS 内） |
| 对外表现 | 一个 TLS 服务 | 一个**真实的 HTTPS 网站** |
| 探测者看到 | 握手成功但内容无意义 | 握手成功，且能看到一个正常网页 |

### 2. 回落（Fallback）：这一招值一整个协议

问题：如果探测者连上来，发一个不是 Trojan 的请求，服务端怎么办？

- 直接断开 → 可疑（正常网站不会这样）
- 返回错误 → **非常可疑**（直接暴露这是代理）
- **转发给一个真实的 Web 服务器** → 完美（探测者看到一个正常网站）

配置大概长这样：

```json
{
  "run_type": "server",
  "local_addr": "0.0.0.0",
  "local_port": 443,
  "remote_addr": "127.0.0.1",
  "remote_port": 80,
  "password": ["..."],
  "ssl": { "cert": "/path/fullchain.pem", "key": "/path/privkey.pem" }
}
```

`remote_addr: 127.0.0.1:80` 就是回落目标——一台普通的 nginx，上面放个静态页。

**结果**：认证通过 → 代理；认证失败 → 你看到的是那个静态页。探测者无从分辨。

### 3. 但「完全像 HTTPS」并不等于安全

Trojan 仍然可能被识别，原因不在握手，而在**行为**：

| 破绽 | 说明 |
|:--|:--|
| 流量方向 | 正常浏览下行远大于上行；代理常出现大量持续上行 |
| 连接时长 | 长连接、长时间空闲但不关闭 |
| 并发模式 | 一个客户端开几十条到同一 IP 的连接 |
| ALPN 一致性 | 声称是网站，却从不用 `h2` 的 HTTP/2 语义 |
| 证书与内容匹配 | 证书是 A 域名，回落页面却是默认页 |
| IP 归属 | 证书域名解析到的 IP 与你连的 IP 长期不一致 |

> 这就是「元数据打不败」的现实：**你可以伪装每一个字节，但很难伪装行为模式。**

### 4. 域前置（Domain Fronting）：一个已死的技术

原理：TLS 的 SNI 写 `allowed.example.com`（CDN 上的白名单域名），HTTP 的 `Host` 头写 `blocked.example.com`。CDN 按 `Host` 路由，于是审查方看到的是合法 SNI，实际访问的是被封站点。

**为什么死了**：

- 2018 年起 Cloudflare、AWS、Google 陆续拒绝 SNI 与 Host 不一致的请求
- 检测成本极低（比对 SNI 和 Host 即可）
- 现在只有极少数 CDN 还留着口子，且随时会关

**教训**：依赖第三方基础设施的「漏洞」做规避，生命周期由别人决定。

### 5. NaiveProxy：另一条路

不做自定义协议，而是**直接把 Chromium 的网络栈拿来用**：HTTP/2 CONNECT over TLS。

优点：TLS 指纹、HTTP/2 行为、优先级、流量整形**全部是真实浏览器的**，几乎无法从协议层区分。
缺点：需要服务端配合（Caddy 的 `forwardproxy` 插件），配置复杂，性能一般。

## 任务清单

- [ ] T07.1 读 Trojan 官方 `protocol.md`，把「请求格式」和「认证失败后的行为」抄成笔记
- [ ] T07.2 搭一个最小回落：nginx 静态页 + Trojan 服务端，用 `curl` 直接访问代理端口，确认返回的是网页
- [ ] T07.3 复述域前置的原理，并说明它为什么在 2018 年后基本失效
- [ ] T07.4 对比 Trojan 与 VLESS+TLS：从「探测者视角」看，两者分别暴露了什么
- [ ] T07.5 `[研究]` 用 Trojan 传一个大文件，抓包统计上下行字节比，和正常浏览对比
- [ ] T07.6 写 200 字：如果只能改一处配置来提升 Trojan 的抗探测性，你改哪里？为什么？

## 实验：把自己当成探测者

假设你不知道这台服务器是什么，你会怎么判断？

```bash
# 1. 标准 TLS 握手，看证书
openssl s_client -connect your-server:443 -servername your-domain.com

# 2. 发一个普通 HTTP 请求，看返回什么
curl -v https://your-domain.com/

# 3. 发垃圾数据，看它是否立刻断开
printf 'GARBAGE\r\n\r\n' | openssl s_client -quiet -connect your-server:443

# 4. 用错误的密码连（如果你有客户端）
```

**判据**：如果 2 返回一个像样的网页、3 表现得像个 Web 服务器，你就很难断定它是代理。

> 反过来想：如果你的服务端对 3 直接 RST，那它就暴露了。

## 自测

1. 回落机制为什么能对抗主动探测？它的前提条件是什么？
2. Trojan 的密码是在 TLS 之内还是之外传输的？这带来什么保证？
3. 域前置为什么依赖 CDN？为什么 CDN 厂商有动力封掉它？
4. 「证书是真的」能证明「这是真网站」吗？为什么？
5. NaiveProxy 相比 Trojan，优势到底在哪一层？

## 延伸阅读

- Trojan 官方文档（GitHub: trojan-gfw/trojan）
- 《Domain Fronting is Dead, Long Live Domain Fronting》（2018 后的分析文章）
- Caddy `forwardproxy` / NaiveProxy 项目 README
- RFC 9113（HTTP/2）——理解 CONNECT 在 h2 里的语义

---

> 打卡：`python scripts/checkin.py done T07.1`
