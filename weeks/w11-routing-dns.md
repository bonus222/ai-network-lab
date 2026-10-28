# W11 · 分流、DNS 与泄漏自测

> **阶段三 · 工程层** ｜ 预计 6–8 小时 ｜ 前置：[W10](w10-deploy-reality.md)
>
> [← W10](w10-deploy-reality.md) ｜ [W12 →](w12-ip-reputation.md)

## 为什么学这个

配好代理只是「能出去」。这一周解决「出去得对不对」：

- 国内网站不走代理（否则又慢又浪费流量，还可能触发风控）
- DNS 不泄漏（否则你访问了谁，本地 ISP 全知道）
- 没有 WebRTC / IPv6 旁路（否则代理形同虚设）

## 核心概念

### 1. 分流：谁走代理，谁直连

典型规则集：

```json
{
  "routing": {
    "domainStrategy": "IPIfNonMatch",
    "rules": [
      { "type": "field", "domain": ["geosite:cn"],        "outboundTag": "direct" },
      { "type": "field", "ip":     ["geoip:cn", "geoip:private"], "outboundTag": "direct" },
      { "type": "field", "domain": ["geosite:geolocation-!cn"],   "outboundTag": "proxy"  }
    ]
  }
}
```

三条规则的顺序**很重要**：先判断「是不是国内的」，再判断「是不是国外的」，最后兜底。

常见坑：

| 坑 | 现象 | 解法 |
|:--|:--|:--|
| 只匹配域名不匹配 IP | 国内 CDN 用 IP 直连时走了代理 | 加 `geoip:cn` |
| `domainStrategy` 设成 `AsIs` | 域名不解析，规则匹配不到 IP | 改 `IPIfNonMatch` |
| 规则顺序反了 | 国外站点被 `geosite:cn` 误伤 | 把具体规则放前面 |

### 2. DNS：最容易被忽略的泄漏点

代理只转发**流量**，不自动接管**DNS 查询**。如果你的系统 DNS 还是运营商的，那么：

```
你 → (代理) → 目标网站        ✅ 内容被保护
你 → (运营商 DNS) → 查询记录  ❌ 你访问了谁，ISP 一清二楚
```

三种解法：

| 方案 | 做法 | 优点 | 缺点 |
|:--|:--|:--|:--|
| **远端解析** | 域名交给代理解析（ATYP=3） | 简单、无泄漏 | 每次都要等一次远端 DNS |
| **DoH/DoT** | 系统 DNS 指向加密 DNS | 全局生效 | 加密 DNS 服务器本身可能被封 |
| **fakeip** | 返回一个假 IP（如 `198.18.x.x`），靠映射表还原 | 快，无泄漏 | 某些程序不兼容，排错困难 |

**fakeip 的坑**：它劫持了 DNS 返回值，所有拿到假 IP 的程序都必须经过代理才能还原。如果某个程序绕过代理直连 `198.18.x.x`，就会莫名其妙失败。

### 3. 三类泄漏

| 泄漏 | 原理 | 检测 |
|:--|:--|:--|
| **DNS 泄漏** | DNS 查询没走代理 | [browserleaks.com/dns](https://browserleaks.com/dns) |
| **WebRTC 泄漏** | WebRTC 直连 UDP，绕过代理暴露真实 IP | [browserleaks.com/webrtc](https://browserleaks.com/webrtc) |
| **IPv6 泄漏** | 代理只处理 IPv4，IPv6 走原生 | [test-ipv6.com](https://test-ipv6.com) |

**WebRTC 最阴险**：它能在你毫不知情的情况下，让网页拿到你的局域网 IP 甚至公网 IP。很多「明明开了代理却还是被识别出真实位置」的案例，根源在这。

### 4. 稳定性：让它自己活着

- `systemd` 的 `Restart=always` + `RestartSec=3`
- 日志轮转，别让日志撑爆磁盘
- 一个简单的存活检测脚本（curl 一个固定 URL，失败就重启）
- 记录每天的可用性（W13 会用到这些数据）

## 任务清单

- [ ] T11.1 配一套分流规则：国内直连、国外走代理、私有地址直连，逐条验证生效
- [ ] T11.2 打开 [browserleaks.com/dns](https://browserleaks.com/dns)，确认 DNS 查询来自你的代理出口而不是本地 ISP
- [ ] T11.3 打开 [browserleaks.com/webrtc](https://browserleaks.com/webrtc)，如果暴露了真实 IP，在浏览器里关掉 WebRTC 再测
- [ ] T11.4 打开 [test-ipv6.com](https://test-ipv6.com)，判断是否存在 IPv6 旁路；有的话在系统或代理层禁用
- [ ] T11.5 给 Xray 配 `Restart=always`，手动 `kill` 进程验证能自动拉起
- [ ] T11.6 连续 7 天，每天记录一次「能不能打开目标站点 + 大致延迟」，存进 `results/w11-uptime.csv`
- [ ] T11.7 `[研究]` 对比 fakeip 与远端解析两种模式下，同一批网站的首次打开耗时

## 实验：三个泄漏，一次查完

按顺序做，每步都截图存证：

1. **DNS**：browserleaks → DNS。看 "Country" 和 "ISP" 是不是你的代理出口。
2. **WebRTC**：browserleaks → WebRTC。看 "Public IP" 有没有出现你的真实 IP。
3. **IPv6**：test-ipv6。如果显示你有 IPv6 而代理只走 IPv4，那就是旁路。

> 三个都干净之后，再做一次「关掉代理」的对照测试——你应该能看到三处都变回真实信息。**能复现泄漏，才算真的会测泄漏。**

## 自测

1. `domainStrategy` 的三个取值分别是什么意思？
2. 为什么「域名交给代理解析」能防 DNS 泄漏？
3. fakeip 快在哪？它的兼容性问题从哪来？
4. WebRTC 为什么能绕过代理？在浏览器层面怎么关？
5. IPv6 泄漏为什么常被忽略？

## 延伸阅读

- Xray 文档：*Routing*、*DNS* 章节
- sing-box 文档：*DNS rules*、*FakeIP*
- browserleaks.com 各项测试的原理说明

---

> 打卡：`python scripts/checkin.py done T11.1`
