#!/usr/bin/env python3
"""本地排盘服务：默认仅监听 127.0.0.1，数据全部保存在本机 SQLite。

用法：
    python3 server.py [--port 8765] [--host 127.0.0.1]
"""
import argparse
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db
import chart as chart_mod
import interpret as interpret_mod
import aiclient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "BaziLocal/1.0"

    # ---------- 基础工具 ----------
    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        # 同源限制，避免被其他站点调用
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json_body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n <= 0:
            return {}
        raw = self.rfile.read(n)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            raise ValueError("请求体不是合法 JSON")

    def log_message(self, fmt, *args):
        pass  # 静默，避免泄露出生信息到终端日志

    # ---------- 路由 ----------
    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/profiles":
                return self._send(200, {"ok": True, "profiles": db.list_profiles()})
            if path == "/api/settings":
                return self._send(200, {"ok": True, "ai": db.get_ai_config(mask=True)})
            if path.startswith("/api/profiles/"):
                pid = path.rsplit("/", 1)[-1]
                p = db.get_profile(pid)
                if not p:
                    return self._send(404, {"ok": False, "error": "档案不存在"})
                return self._send(200, {"ok": True, "profile": p})
            return self._serve_static(path)
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"ok": False, "error": str(e)})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self._json_body()
        except ValueError as e:
            return self._send(400, {"ok": False, "error": str(e)})

        try:
            if path == "/api/chart":
                return self._api_chart(body)
            if path == "/api/profiles":
                return self._api_save_profile(body)
            if path == "/api/settings":
                cfg = db.set_ai_config(body.get("ai") or {})
                return self._send(200, {"ok": True, "ai": cfg})
            if path == "/api/ai":
                return self._api_ai(body)
            return self._send(404, {"ok": False, "error": "未知接口"})
        except KeyError as e:
            self._send(400, {"ok": False, "error": f"缺少字段：{e}"})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"ok": False, "error": str(e)})

    def do_DELETE(self):
        path = urlparse(self.path).path
        try:
            if path.startswith("/api/profiles/"):
                pid = int(path.rsplit("/", 1)[-1])
                db.delete_profile(pid)
                return self._send(200, {"ok": True})
            return self._send(404, {"ok": False, "error": "未知接口"})
        except Exception as e:
            self._send(500, {"ok": False, "error": str(e)})

    # ---------- 业务 ----------
    def _api_chart(self, body):
        birth = body.get("birth") or body
        ch = chart_mod.build_chart(birth)
        res = interpret_mod.interpret(ch)
        return self._send(200, {"ok": True, "chart": ch, "interpretation": res})

    def _api_save_profile(self, body):
        birth = body.get("birth") or body
        ch = chart_mod.build_chart(birth)
        payload = dict(birth)
        payload["chart"] = ch
        pid = db.save_profile(payload)
        return self._send(200, {"ok": True, "id": pid})

    def _api_ai(self, body):
        cfg = db.get_ai_config(mask=False)
        if not cfg.get("enabled"):
            return self._send(400, {"ok": False, "error": "AI 解读未启用，请先在设置中开启。"})
        ch = body.get("chart")
        if not ch:
            return self._send(400, {"ok": False, "error": "缺少盘面数据"})
        res = body.get("interpretation") or interpret_mod.interpret(ch)
        question = (body.get("question") or "").strip()
        context = interpret_mod.to_plain_text(ch, res)
        user_content = ("以下是我的八字命盘与初步分析，请为我详细解读：\n\n" + context)
        if question:
            user_content += "\n\n我想重点了解：" + question
        try:
            text = aiclient.chat(cfg, user_content)
        except aiclient.AIError as e:
            return self._send(502, {"ok": False, "error": str(e)})
        return self._send(200, {"ok": True, "text": text})

    # ---------- 静态资源 ----------
    def _serve_static(self, path):
        if path in ("/", ""):
            path = "/index.html"
        rel = unquote(path).lstrip("/")
        full = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not full.startswith(WEB_DIR) or not os.path.isfile(full):
            return self._send(404, {"ok": False, "error": "文件不存在"},
                              "application/json; charset=utf-8")
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as f:
            data = f.read()
        self._send(200, data, CONTENT_TYPES.get(ext, "application/octet-stream"))


def main():
    ap = argparse.ArgumentParser(description="本地八字排盘服务")
    ap.add_argument("--host", default="127.0.0.1", help="监听地址，默认仅本机 127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    db.init_db()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    shown = "127.0.0.1" if args.host in ("127.0.0.1", "localhost") else args.host
    print(f"本地排盘服务已启动： http://{shown}:{args.port}")
    print(f"数据文件： {db.DB_PATH}")
    if args.host not in ("127.0.0.1", "localhost"):
        print("⚠ 已监听非本机地址，局域网内其他设备可访问，请注意隐私风险。")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
        httpd.shutdown()


if __name__ == "__main__":
    main()