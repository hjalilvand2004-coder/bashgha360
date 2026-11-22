#!/usr/bin/env python3
"""گارد PNT-02 — ممنوعیت اجرای داینامیک در service/router ماژول‌ها.

سخت‌گیرانه ممنوع:  eval( ، exec( ، __import__ با نام غیرلیترال یا خارج از
فهرست مجاز کتابخانهٔ استاندارد (uuid/datetime/json) — هر چیز دیگری ناموفق.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TARGETS = ["app/modules/*/" + n for n in ("service.py", "router.py")]

# بررسی با AST — فراخوانی واقعی eval/exec را می‌گیرد؛ متن کامنت/داک‌استرینگ نادیده
ALLOWED_IMPORTS = {"uuid", "datetime", "json"}

FORBIDDEN_CALLS = {"eval", "exec"}


def check_source(path: Path) -> list[str]:
    issues: list[str] = []
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        issues.append(f"{path}: سینتکس ناتمام ({e})")
        return issues
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                issues.append(f"{path}:{node.lineno}: فراخوانی ممنوع {node.func.id}()")
            elif node.func.id == "__import__":
                if not node.args or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
                    issues.append(f"{path}:{node.lineno}: __import__ با نام غیرلیترال ممنوع است")
                elif node.args[0].value not in ALLOWED_IMPORTS:
                    issues.append(f"{path}:{node.lineno}: __import__('{node.args[0].value}') خارج از فهرست مجاز")
    return issues


def main() -> int:
    files: list[Path] = []
    for pattern in TARGETS:
        files.extend((REPO / "backend").glob(pattern))
    if not files:
        print("هیچ فایلی برای بررسی یافت نشد", file=sys.stderr)
        return 1
    all_issues: list[str] = []
    for f in sorted(files):
        all_issues.extend(check_source(f))
    for issue in all_issues:
        print("PNT-02:", issue)
    if all_issues:
        print(f"\n{len(all_issues)} تخلف — commit رد شد", file=sys.stderr)
        return 1
    print(f"PNT-02 OK — {len(files)} فایل بررسی شد؛ بدون eval/exec/__import__ غیرمجاز")
    return 0


if __name__ == "__main__":
    sys.exit(main())
