# 术语表

> 按学习顺序排列，标了 `W##` 的是该术语第一次出现的周。

## 网络基础（W01–W02）

| 术语 | 英文 | 一句话解释 |
|:--|:--|:--|
| 封装 | Encapsulation | 每层协议给数据加自己的头，像套娃 |
| MTU | Maximum Transmission Unit | 一个帧能装的最大数据量，以太网 1500 字节 |
| MSS | Maximum Segment Size | TCP 单段最大数据量，通常 MTU−40=1460 |
| NAT | Network Address Translation | 把内网地址换成公网地址，全家共用一个出口 IP |
| TTL | Time To Live | 包还能经过几跳，每过一个路由器减 1 |
| ASN | Autonomous System Number | 一个 IP 段所属的「自治系统」编号，如 AS4134 |
| BGP | Border Gateway Protocol | 各 AS 之间交换路由的协议 |
| 递归查询 | Recursive query | 你的 DNS 服务器替你跑完全程 |
| DoH / DoT | DNS over HTTPS/TLS | 把 DNS 查询也加密 |
| TLS | Transport Layer Security | 加密传输层，HTTPS 的「S」 |
| SNI | Server Name Indication | ClientHello 里明文的域名，审查的核心抓手 |
| ALPN | Application-Layer Protocol Negotiation | 握手时协商用 h2 还是 http/1.1 |
| 证书链 | Certificate chain | 服务器证书 → 中间 CA → 根 CA |
| CA | Certificate Authority | 签发证书的机构 |
| 前向保密 | Forward secrecy | 私钥泄露也解不开历史流量（ECDHE 提供） |
| ECH | Encrypted Client Hello | 加密 SNI 的提案，部署有限 |

## 代理与协议（W03–W08）

| 术语 | 英文 | 一句话解释 |
|:--|:--|:--|
| 正向代理 | Forward proxy | 代表客户端去访问外部 |
| 反向代理 | Reverse proxy | 代表服务器接受外部访问 |
| CONNECT | HTTP CONNECT | 让代理建一条透明 TCP 隧道 |
| SOCKS5 | — | 通用代理协议，支持 IPv4/域名/IPv6 |
| ATYP | Address Type | SOCKS5 请求里的地址类型：1=IPv4, 3=域名, 4=IPv6 |
| 透明代理 | Transparent proxy | 在网络层劫持流量，程序无感知 |
| DPI | Deep Packet Inspection | 解析到应用层做匹配与统计 |
| 中间盒 | Middlebox | 链路上做额外处理的设备（审查、NAT、负载均衡） |
| RST 注入 | RST injection | 伪造 TCP 重置包，强行掐断连接 |
| 主动探测 | Active probing | 主动去连可疑服务器，看它怎么回应 |
| 熵 | Entropy | 数据的不确定性；加密数据接近 8 bit/byte |
| 流量指纹 | Traffic fingerprint | 包长分布、时序、方向比例等统计特征 |
| TLS-in-TLS | — | TLS 里套 TLS，握手模式可被统计识别 |
| AEAD | Authenticated Encryption with Associated Data | 同时保证机密性与完整性（AES-GCM 等） |
| salt | — | 每次连接随机的盐，防重放与密钥复用 |
| VMess / VLESS | — | V2Ray/Xray 的两种协议，前者自带加密，后者不加密 |
| XTLS | — | 让代理不解密直接透传内层 TLS 字节 |
| splice | — | 零拷贝转发，保持包长不变 |
| REALITY | — | 借用真实站点的 TLS 握手，无需自有证书 |
| uTLS | — | 自定义 ClientHello 以模仿浏览器指纹 |
| JA3 / JA4 | — | TLS 客户端指纹的哈希方案 |
| 回落 | Fallback | 认证失败时转发给真实网站 |
| 域前置 | Domain fronting | SNI 与 Host 不一致，借 CDN 绕过，已基本失效 |
| QUIC | — | 基于 UDP 的传输协议，HTTP/3 的底座 |
| Hysteria2 / TUIC | — | 基于 QUIC 的代理协议 |
| Brutal | — | Hysteria2 的拥塞控制，按设定带宽忽略丢包 |

## 工程与运维（W09–W11）

| 术语 | 英文 | 一句话解释 |
|:--|:--|:--|
| CN2 GIA | — | 电信优质国际线路，去回程都走 CN2 |
| CN2 GT | — | CN2 的「半程」版本，通常只走单向 |
| 163 | ChinaNet | 电信普通骨干网，便宜但晚高峰差 |
| CMI | China Mobile International | 移动国际线路，AS58453 |
| IPLC / IEPL | — | 国际专线，不过公网 |
| 原生 IP | Native IP | whois 归属地与机房实际位置一致 |
| 广播 IP | Broadcast IP | 把别处 IP 段广播到本地 |
| BBR | Bottleneck Bandwidth and RTT | Google 的拥塞控制算法，高延迟链路提升明显 |
| 分流 | Routing | 按域名/IP 决定走代理还是直连 |
| fakeip | — | 返回假 IP，靠映射表还原，快但排错难 |
| DNS 泄漏 | DNS leak | DNS 查询没走代理，暴露你访问了谁 |
| WebRTC 泄漏 | WebRTC leak | WebRTC 直连 UDP，绕过代理暴露真实 IP |
| IPv6 泄漏 | IPv6 leak | 代理只处理 IPv4，IPv6 走原生 |

## 风控与评测（W12–W16）

| 术语 | 英文 | 一句话解释 |
|:--|:--|:--|
| 住宅 IP | Residential IP | 归属运营商、分配给家庭用户的 IP |
| 机房 IP | Datacenter IP | 云厂商/IDC 的 IP，默认低信任 |
| 滥用历史 | Abuse history | 这个 IP 过去被用来干过什么 |
| 地理一致性 | Geo consistency | IP、时区、语言、支付方式指向同一地区 |
| 浏览器指纹 | Browser fingerprint | Canvas、WebGL、字体等组合出的标识 |
| P50 / P95 | Percentile | 中位数 / 95 分位；代理看 P95 更有意义 |
| 抖动 | Jitter | 延迟的波动程度 |
| TTFB | Time To First Byte | 发出请求到收到第一个字节 |
| KL 散度 | KL divergence | 衡量两个概率分布的差异 |
| 威胁模型 | Threat model | 对手能做什么、不能做什么的明确假设 |

---

> 遇到不认识的词，先回这张表查；表里没有的，用 `checkin.py note` 记下来，攒够一批再补。
