from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ClassExceptionMetrics:
    caaec: float  # average except handlers per method


def compute_caaec(py_texts: list[tuple[str, str]]) -> Dict[str, ClassExceptionMetrics]:
    out: Dict[str, ClassExceptionMetrics] = {}
    for filename, text in py_texts:
        try:
            tree = ast.parse(text)
        except Exception:
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if not methods:
                    out[node.name] = ClassExceptionMetrics(caaec=0.0)
                    continue
                total_handlers = 0
                for m in methods:
                    handlers = 0
                    for n in ast.walk(m):
                        if isinstance(n, ast.ExceptHandler):
                            handlers += 1
                    total_handlers += handlers
                out[node.name] = ClassExceptionMetrics(caaec=float(total_handlers / len(methods)))
    return out
