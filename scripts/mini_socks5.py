#!/usr/bin/env python3
"""一个最小可用的 SOCKS5 服务器 —— W03 的教具。

它只做 CONNECT（不支持 BIND / UDP ASSOCIATE），不做认证，
目的是让你**看清楚** SOCKS5 的每一个字节。

用法：
  python scripts/mini_socks5.py --verbose
  curl --socks5-hostname 127.0.0.1:1080 https://example.com

对照阅读：RFC 1928 §3（方法协商）、§4（请求）、§6（应答）
"""
from __future__ import annotations

import argparse
import socket
import struct
import sys
import threading

VER = 0x05
CMD_CONNECT = 0x01
ATYP_IPV4 = 0x01
ATYP_DOMAIN = 0x03
ATYP_IPV6 = 0x04

# 应答码
REP_OK = 0x00
REP_GENERAL_FAILURE = 0x01
REP_HOST_UNREACHABLE = 0x04
REP_CONNECTION_REFUSED = 0x05
REP_COMMAND_NOT_SUPPORTED = 0x07
REP_ADDRESS_TYPE_NOT_SUPPORTED = 0x08


def read_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("对端关闭了连接")
        buf += chunk
    return buf


def send_reply(sock: socket.socket, rep: int) -> None:
    """VER REP RSV ATYP BND.ADDR BND.PORT —— 最小实现里绑定地址填 0。"""
    sock.sendall(bytes([VER, rep, 0x00, ATYP_IPV4]) + b"\x00" * 4 + b"\x00" * 2)


def relay(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def handle(client: socket.socket, verbose: bool) -> None:
    peer = client.getpeername()
    try:
        # ---- 阶段一：方法协商 -------------------------------------------
        ver, nmethods = read_exact(client, 2)
        if ver != VER:
            client.close()
            return
        methods = read_exact(client, nmethods)
        if verbose:
            print(f"[{peer}] 协商: VER={ver} NMETHODS={nmethods} "
                  f"METHODS={methods.hex(' ')} -> 回 05 00 (无认证)")
        client.sendall(bytes([VER, 0x00]))

        # ---- 阶段二：请求 -----------------------------------------------
        ver, cmd, _rsv, atyp = read_exact(client, 4)
        if atyp == ATYP_IPV4:
            host = socket.inet_ntoa(read_exact(client, 4))
        elif atyp == ATYP_DOMAIN:
            length = read_exact(client, 1)[0]
            host = read_exact(client, length).decode("ascii", "replace")
        elif atyp == ATYP_IPV6:
            host = socket.inet_ntop(socket.AF_INET6, read_exact(client, 16))
        else:
            send_reply(client, REP_ADDRESS_TYPE_NOT_SUPPORTED)
            client.close()
            return

        port = struct.unpack("!H", read_exact(client, 2))[0]

        if verbose:
            kind = {ATYP_IPV4: "IPv4", ATYP_IPV6: "IPv6", ATYP_DOMAIN: "域名"}[atyp]
            print(f"[{peer}] 请求: CMD={cmd} ATYP={atyp}({kind}) "
                  f"HOST={host} PORT={port}")

        if cmd != CMD_CONNECT:
            send_reply(client, REP_COMMAND_NOT_SUPPORTED)
            client.close()
            return

        # ---- 阶段三：连接目标 -------------------------------------------
        try:
            remote = socket.create_connection((host, port), timeout=10)
        except socket.timeout:
            send_reply(client, REP_HOST_UNREACHABLE)
            client.close()
            return
        except OSError:
            send_reply(client, REP_CONNECTION_REFUSED)
            client.close()
            return

        send_reply(client, REP_OK)
        if verbose:
            print(f"[{peer}] 已连通 {host}:{port}，开始转发")

        # ---- 阶段四：双向转发 -------------------------------------------
        t = threading.Thread(target=relay, args=(remote, client), daemon=True)
        t.start()
        relay(client, remote)
        t.join(timeout=5)
        remote.close()

    except (ConnectionError, OSError):
        pass
    finally:
        try:
            client.close()
        except OSError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description="最小 SOCKS5 服务器（仅 CONNECT）")
    ap.add_argument("--bind", default="127.0.0.1", help="监听地址，默认 127.0.0.1")
    ap.add_argument("--port", type=int, default=1080, help="监听端口，默认 1080")
    ap.add_argument("--verbose", "-v", action="store_true", help="打印每一个字段")
    args = ap.parse_args()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.bind, args.port))
    srv.listen(32)

    print(f"SOCKS5 listening on {args.bind}:{args.port}")
    print(f"测试: curl --socks5-hostname {args.bind}:{args.port} https://example.com")
    print("Ctrl+C 退出\n")

    try:
        while True:
            client, _ = srv.accept()
            threading.Thread(target=handle, args=(client, args.verbose),
                             daemon=True).start()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        srv.close()
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
