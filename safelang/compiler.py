"""Minimal NASM compiler for SafeLang functions."""

from typing import List
import re

from .parser import FunctionDef


def _parse_space(space: str) -> int:
    match = re.match(r"([0-9_]+)B", space)
    if not match:
        return 0
    return int(match.group(1).replace("_", ""))


def compile_to_nasm(funcs: List[FunctionDef]) -> str:
    """Return NASM x86_64 assembly for ``funcs``.

    This is a very small subset that only emits prologue/epilogue and reserves
    stack space based on ``@space`` attributes.
    """
    lines = ["; Auto-generated NASM for SafeLang"]
    for fn in funcs:
        lines.append(f"global {fn.name}")
    lines.append("")
    for fn in funcs:
        space = _parse_space(fn.space)
        lines.append(f"{fn.name}:")
        lines.append("    push rbp")
        lines.append("    mov rbp, rsp")
        if space:
            lines.append(f"    sub rsp, {space}")
        lines.append("    ; TODO: compile body")
        if space:
            lines.append(f"    add rsp, {space}")
        lines.append("    pop rbp")
        lines.append("    ret")
        lines.append("")
    return "\n".join(lines)


__all__ = ["compile_to_nasm"]

