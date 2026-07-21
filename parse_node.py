#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import re
import subprocess
from urllib.parse import urlparse, parse_qs

def parse_vless(link):
    try:
        if not link.startswith('vless://'):
            return None
        parsed = urlparse(link)
        if parsed.scheme != 'vless':
            return None

        netloc = parsed.netloc
        if '@' in netloc:
            uuid, host_port = netloc.split('@', 1)
        else:
            uuid, host_port = '', netloc

        host = ''
        port = '443'
        bracket_match = re.match(r'^\[([^\]]+)\](?::(\d+))?$', host_port)
        if bracket_match:
            host = bracket_match.group(1)
            if bracket_match.group(2):
                port = bracket_match.group(2)
        else:
            if host_port.count(':') > 1:
                host = host_port
            else:
                if ':' in host_port:
                    host, port = host_port.split(':', 1)
                else:
                    host = host_port
        if not host:
            return None

        params = parse_qs(parsed.query)
        sni = params.get('sni', [''])[0] or host
        fp = params.get('fp', [''])[0] or 'chrome'
        flow = params.get('flow', [''])[0] or 'xtls-rprx-vision'
        type_ = params.get('type', ['tcp'])[0]
        security = params.get('security', [''])[0]

        outbound = {
            "type": "vless",
            "tag": "vless-out",
            "server": host,
            "server_port": int(port),
            "uuid": uuid,
            "flow": flow,
            "tls": {
                "enabled": True,
                "server_name": sni,
                "insecure": False,
                "utls": {"enabled": True, "fingerprint": fp}
            },
            "packet_encoding": "packetaddr"
        }
        if type_ != 'tcp':
            outbound["transport"] = {"type": type_}
        if security == 'reality':
            pbk = params.get('pbk', [''])[0]
            sid = params.get('sid', [''])[0]
            outbound['tls']['reality'] = {"enabled": True, "public_key": pbk, "short_id": sid}

        return outbound
    except Exception as e:
        print(f"解析 vless 异常: {e}", file=sys.stderr)
        return None

def main():
    link = os.environ.get('VLESS', '').strip()
    if not link:
        print("未设置 VLESS 环境变量", file=sys.stderr)
        sys.exit(1)

    # 先尝试 sing-box convert（如果存在）
    try:
        proc = subprocess.run(
            ['sing-box', 'convert', 'link'],
            input=link.encode(),
            capture_output=True,
            timeout=10
        )
        if proc.returncode == 0:
            outbound = json.loads(proc.stdout)
            if outbound:
                json.dump(outbound, sys.stdout, indent=2)
                return
        else:
            # 打印 stderr 以便调试
            print(f"sing-box convert stderr: {proc.stderr.decode()}", file=sys.stderr)
    except Exception as e:
        print(f"sing-box convert 异常: {e}", file=sys.stderr)

    # 回退到手动 vless 解析
    outbound = parse_vless(link)
    if outbound:
        json.dump(outbound, sys.stdout, indent=2)
        return

    print("解析失败", file=sys.stderr)
    sys.exit(1)

if __name__ == '__main__':
    main()
