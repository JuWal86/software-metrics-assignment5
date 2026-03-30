from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Dict, Set, Tuple, List


@dataclass
class ClassOOMetrics:
    wmc: float
    dit: int
    noc: int
    cbo: int
    lcom: float


def _method_complexity(func: ast.FunctionDef) -> int:
    # simple cyclomatic approximation: count decision nodes + 1
    nodes = (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.ExceptHandler, ast.With, ast.Try, ast.Match)
    c = 1
    for n in ast.walk(func):
        if isinstance(n, nodes):
            c += 1
    return c


def compute_oo_metrics(py_texts: list[tuple[str, str]]) -> Dict[str, ClassOOMetrics]:
    """
    py_texts: list of (filename, text)
    returns: per-class OO metrics (approx for Python)
    """
    class_bases: Dict[str, List[str]] = {}
    children: Dict[str, Set[str]] = {}
    class_methods: Dict[str, List[ast.FunctionDef]] = {}
    class_imports: Dict[str, Set[str]] = {}
    class_attrs_by_method: Dict[Tuple[str, str], Set[str]] = {}

    for filename, text in py_texts:
        try:
            tree = ast.parse(text)
        except Exception:
            continue

        imports_in_file: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports_in_file.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports_in_file.add(node.module.split(".")[0])

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                cname = node.name
                bases = []
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        bases.append(b.id)
                    elif isinstance(b, ast.Attribute):
                        bases.append(b.attr)
                class_bases[cname] = bases
                children.setdefault(cname, set())
                class_imports.setdefault(cname, set()).update(imports_in_file)

                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                class_methods[cname] = methods

                for m in methods:
                    attrs = set()
                    for n in ast.walk(m):
                        # self.x attribute usage
                        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "self":
                            attrs.add(n.attr)
                    class_attrs_by_method[(cname, m.name)] = attrs

    # build child map
    for cls, bases in class_bases.items():
        for b in bases:
            children.setdefault(b, set()).add(cls)

    def dit_for(cls: str) -> int:
        # naive: longest base chain using known classes
        seen = set()
        depth = 0
        cur = cls
        while True:
            if cur in seen:
                break
            seen.add(cur)
            bases = class_bases.get(cur, [])
            # only follow first known base for simplicity
            next_base = None
            for b in bases:
                if b in class_bases:
                    next_base = b
                    break
            if not next_base:
                break
            depth += 1
            cur = next_base
        return depth

    out: Dict[str, ClassOOMetrics] = {}
    for cls, methods in class_methods.items():
        # WMC: sum of method complexities
        wmc = 0
        for m in methods:
            wmc += _method_complexity(m)

        # DIT/NOC
        dit = dit_for(cls)
        noc = len(children.get(cls, set()))

        # CBO approximation: unique imports referenced
        cbo = len(class_imports.get(cls, set()))

        # LCOM approximation: (non-sharing pairs - sharing pairs) normalized
        mnames = [m.name for m in methods]
        pairs = 0
        sharing = 0
        for i in range(len(mnames)):
            for j in range(i + 1, len(mnames)):
                pairs += 1
                a = class_attrs_by_method.get((cls, mnames[i]), set())
                b = class_attrs_by_method.get((cls, mnames[j]), set())
                if a.intersection(b):
                    sharing += 1
        if pairs == 0:
            lcom = 0.0
        else:
            non_sharing = pairs - sharing
            lcom = max(0.0, (non_sharing - sharing) / pairs)

        out[cls] = ClassOOMetrics(wmc=float(wmc), dit=int(dit), noc=int(noc), cbo=int(cbo), lcom=float(lcom))

    return out
