#!/usr/bin/env python3
"""Test manifest and proxy endpoints."""
import paramiko
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HOST = "192.144.12.68"
PORT = 22
USERNAME = "aruser"
PASSWORD = "vPB4b!vLk5"


def run(connection, command, timeout=30):
    chan = connection.get_transport().open_session()
    chan.settimeout(30)
    chan.exec_command(command)
    out = chan.recv(1_000_000).decode("utf-8", errors="replace")
    err = chan.recv_stderr(1_000_000). decode("utf-8", errors="replace")
    rc = chan.recv_exit_status()
    return rc, out, err


connection = paramiko.SSHClient()
connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
connection.connect(hostname=HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=20)

def step(name, command, timeout=30):
    print(f"\n=== {name} ===")
    rc, out, err = run(connection, command, timeout=timeout)
    print(f"rc={rc}")
    print(out[:3000])
    if err:
        print("ERR:", err[:500])
    return rc

# Test manifest for AR content 45
step("MANIFEST_45", "curl -s http://127.0.0.1:8000/api/viewer/ar/c0f8bb04-f4e1-4e6e-838d-6b97deff244d/manifest")

# Test proxy endpoint directly for marker
step("PROXY_MARKER", "curl -s -o /dev/null -w '%{http_code}' 'http://127.0.0.1:8000/api/storage/yd-file?path=promo/ORD-20260604-1818/photo.jpg&company_id=4'")

# Test proxy endpoint directly for video
step("PROXY_VIDEO", "curl -s -o /dev/null -w '%{http_code}' 'http://127.0.0.1:8000/api/storage/yd-file?path=promo/ORD-20260604-1818/videos/video_55.mp4&company_id=4'")

connection.close()
