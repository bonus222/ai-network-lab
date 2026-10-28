# W10 · 部署 Xray + REALITY 全流程

> **阶段三 · 工程层** ｜ 预计 8–12 小时 ｜ 前置：[W08](w08-reality-quic.md) [W09](w09-vps.md)
>
> [← W09](w09-vps.md) ｜ [W11 →](w11-routing-dns.md)

## 为什么学这个

前面所有原理，这周落地成**五台设备都能用的东西**。

这一周的目标不是「抄一份能跑的配置」，而是：**每一个字段你都知道为什么在那里**，坏了能自己修。

## 核心概念

### 1. 服务端配置的骨架

Xray 的配置永远是三个部分：

```json
{
  "inbounds":  [ /* 别人怎么连进来 */ ],
  "outbounds": [ /* 出去怎么走 */ ],
  "routing":   { /* 谁走哪条 outbound */ }
}
```

REALITY 入站的关键字段：

| 字段 | 含义 | 注意 |
|:--|:--|:--|
| `port` | 监听端口 | 用 443，最不显眼 |
| `protocol: vless` | 协议 | REALITY 目前主要配 VLESS |
| `decryption: none` | VLESS 不加密 | 加密交给 TLS 层 |
| `flow: xtls-rprx-vision` | 流控模式 | 客户端必须一致 |
| `dest` | 借用的真实站点 | 必须支持 TLS1.3 + H2 |
| `serverNames` | 允许的 SNI 列表 | 必须包含 `dest` 的域名 |
| `privateKey` | 服务端私钥 | `xray x25519` 生成 |
| `shortIds` | 短 ID | 0–16 位十六进制，可多个 |
| `clients[].id` | 客户端 UUID | `xray uuid` 生成 |

### 2. 密钥与 ID 的关系

```
xray x25519
  → Private key: xxx   （只放服务端）
  → Public key:  yyy   （给客户端）
```

- **私钥/公钥**：用于 REALITY 的握手认证，**不是** TLS 证书
- **UUID**：标识用户
- **shortId**：额外的区分因子，客户端服务端必须一致

> 常见错误：把 public key 填到服务端的 `privateKey` 里。结果是握手永远失败，日志里看不出明显原因。

### 3. `dest` 怎么选

三个硬条件：

1. 支持 **TLS 1.3**
2. 支持 **HTTP/2**（ALPN 里有 `h2`）
3. **不在**你所在的审查区域内被封锁，且**不是你自己的域名**

推荐思路：选大型 CDN 上的站点（同一域名天然对应大量 IP，「这个 IP 在冒充这个域名」的异常感被稀释）。

测试方法：

```bash
openssl s_client -connect <dest域名>:443 -servername <dest域名> -alpn h2 </dev/null 2>&1 | grep -E "Protocol|ALPN"
```

### 4. 客户端：四平台对应

| 平台 | 推荐客户端 | 备注 |
|:--|:--|:--|
| Windows | v2rayN / NekoRay | 图形化，支持 REALITY |
| macOS | V2RayXS / sing-box | 注意系统代理权限 |
| Android | v2rayNG / NekoBox | 支持分应用代理 |
| iOS | Shadowrocket / sing-box | 需外区 Apple ID 购买 |

**iOS 的现实**：国区 App Store 没有这类客户端。这是「先有鸡还是先有蛋」的问题，通常的解法是注册一个外区账号——这属于平台条款问题，自己权衡（见 `docs/03-compliance.md`）。

### 5. 排错顺序

出问题按这个顺序查，不要跳：

1. **端口通不通**：`nc -vz <IP> 443` 或 `telnet`
2. **TLS 握手成不成**：`openssl s_client -connect <IP>:443 -servername <dest域名>`
3. **服务端日志有没有报错**：`journalctl -u xray -f`
4. **时间对不对**：`date`，差超过 90 秒会失败
5. **UUID / shortId / flow / publicKey 四处是否完全一致**

## 任务清单

- [ ] T10.1 用 `xray x25519` 生成密钥对，`xray uuid` 生成 UUID，**记录在本地 `private/` 目录**（不要提交）
- [ ] T10.2 写出完整服务端配置，逐字段注释它的作用
- [ ] T10.3 启动服务，用 `openssl s_client` 验证端口返回的是 `dest` 的真实证书
- [ ] T10.4 生成 Windows 客户端配置并连通，浏览器能打开网页
- [ ] T10.5 生成 Android 客户端配置并连通
- [ ] T10.6 生成 macOS 与 iOS 客户端配置并连通（iOS 没有客户端就先跳过，记一笔）
- [ ] T10.7 故意改错一个字段（比如 shortId），观察客户端报什么错，把现象记进 `checkins/` 的 note
- [ ] T10.8 把服务端配置做一份备份（去掉敏感字段后可以进仓库）

## 实验：把「不可区分」验证一遍

```bash
# 1. 从外部看，这个端口像什么？
nmap -sV -p443 <你的IP>

# 2. 它给出的证书是谁的？
echo | openssl s_client -connect <你的IP>:443 -servername <dest域名> 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates

# 3. 用 HTTP 访问，看它返回什么
curl -sk https://<你的IP>/ -H "Host: <dest域名>" | head -20
```

三条命令的输出，应该**全都指向那个真实站点**，没有任何信息指向「这是一台代理服务器」。

## 自测

1. `privateKey` 和证书私钥是一回事吗？
2. `flow: xtls-rprx-vision` 如果服务端开了客户端没开，会怎样？
3. `dest` 为什么不能选自己的域名？
4. shortId 的作用是什么？可以为空吗？
5. 为什么端口建议用 443 而不是 8443？

## 延伸阅读

- Xray-core 官方示例配置（GitHub: XTLS/Xray-examples）
- Xray 文档：*REALITY* 配置详解
- v2rayN / v2rayNG 的 REALITY 配置说明

---

> 打卡：`python scripts/checkin.py done T10.1`
