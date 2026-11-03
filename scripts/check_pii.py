#!/usr/bin/env python3
"""Quét src/ và public/ tìm email / số điện thoại. Thoát mã 1 nếu phát hiện (dùng trước khi deploy).

Địa chỉ liên hệ chính thức của dự án được phép: thêm vào ALLOW.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOW = {"tholaai.project@gmail.com"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)(?:\+?84|0)[\s.]?\d{2,3}[\s.]?\d{3}[\s.]?\d{3,4}(?!\d)")
TEXT = {".md", ".mdx", ".json", ".astro", ".ts", ".js", ".css", ".html", ".yml", ".yaml", ".txt"}

bad = []
for base in ("src", "public"):
    for p in (ROOT / base).rglob("*"):
        if p.suffix.lower() not in TEXT or not p.is_file():
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        for m in EMAIL.findall(s):
            if m.lower() not in ALLOW:
                bad.append((p, m))
        for m in PHONE.findall(s):
            bad.append((p, m))
for p, m in bad:
    print(f"PII? {p.relative_to(ROOT)}: {m}")
print("OK: không phát hiện PII" if not bad else f"{len(bad)} mục cần kiểm tra")
sys.exit(1 if bad else 0)

