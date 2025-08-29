"""Simple SafeLang code generators."""

from __future__ import annotations
from typing import List
import re

from .parser import FunctionDef

# C and Rust type maps

_C_TYPE_MAP = {
    "f32": "float",
    "f64": "double",
    "int8": "int8_t",
    "uint8": "uint8_t",
    "int16": "int16_t",
    "uint16": "uint16_t",
    "int32": "int32_t",
    "uint32": "uint32_t",
    "int64": "int64_t",
    "uint64": "uint64_t",
}

_RUST_TYPE_MAP = {
    "f32": "f32",
    "f64": "f64",
    "int8": "i8",
    "uint8": "u8",
    "int16": "i16",
    "uint16": "u16",
    "int32": "i32",
    "uint32": "u32",
    "int64": "i64",
    "uint64": "u64",
}

_PARAM_RE = re.compile(r"(\w+)\(([^)]+)\)")


def _parse_params(lines: List[str], type_map: dict, style: str) -> List[str]:
    """Parse parameters from ``consume`` block lines."""
    params: List[str] = []
    seen = set()
    for ln in lines:
        stripped = ln.split("#", 1)[0].split("!", 1)[0].strip()
        if stripped == "nil":
            continue
        match = _PARAM_RE.fullmatch(stripped)
        if not match:
            raise ValueError(f"Malformed parameter: {ln}")
        typ, name = match.group(1), match.group(2)
        if name in seen:
            raise ValueError(f"Duplicate parameter name: {name}")
        mapped = type_map.get(typ)
        if mapped is None:
            raise ValueError(f"Unknown type: {typ}")
        if style == "c":
            params.append(f"{mapped} {name}")
        else:  # rust
            params.append(f"{name}: {mapped}")
        seen.add(name)
    return params


def _parse_space(space: str) -> int:
    """Parse a memory size string into bytes.

    Recognizes suffixes like ``B``, ``KB``, ``MB`` and converts the numeric
    portion (allowing underscores for readability) into its byte equivalent.

    Parameters
    ----------
    space: str
        A string representing the memory size (e.g. ``"4KB"``).

    Returns
    -------
    int
        The size in bytes.

    Raises
    ------
    ValueError
        If the format is not recognized.
    """

    space = space.strip().upper()
    match = re.fullmatch(r"([0-9_]+)([KMGT]?B)", space)
    if not match:
        raise ValueError(f"Unrecognized space format: {space}")

    number = int(match.group(1).replace("_", ""))
    suffix = match.group(2)
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
    }

    try:
        return number * multipliers[suffix]
    except KeyError as exc:
        raise ValueError(f"Unrecognized space format: {space}") from exc


_PARAM_REGS = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]


def _mov_to_rax(token: str, var_regs: dict) -> str:
    src = var_regs.get(token, token)
    return f"mov rax, {src}"


_TOKEN_RE = re.compile(r"\w+|[-+*/]")


def _tokenize(expr: str) -> List[str]:
    return _TOKEN_RE.findall(expr)


def _compile_expr(expr: str, var_regs: dict) -> List[str]:
    tokens = _tokenize(expr)
    if not tokens:
        return []
    if len(tokens) == 1:
        return [_mov_to_rax(tokens[0], var_regs)]
    if len(tokens) == 2 and tokens[0] == "-":
        rhs_val = var_regs.get(tokens[1], tokens[1])
        return ["mov rax, 0", f"sub rax, {rhs_val}"]
    if len(tokens) == 3:
        lhs, op, rhs = tokens
        code = [_mov_to_rax(lhs, var_regs)]
        rhs_val = var_regs.get(rhs, rhs)
        if op == "+":
            code.append(f"add rax, {rhs_val}")
        elif op == "-":
            code.append(f"sub rax, {rhs_val}")
        elif op == "*":
            code.append(f"imul rax, {rhs_val}")
        elif op == "/":
            code.append("cqo")
            code.append(f"idiv {rhs_val}")
        else:
            code.append(f"; unsupported op {op}")
        return code
    return [f"; unsupported expr {expr}"]


def _compile_stmt(stmt: str, var_regs: dict) -> List[str]:
    stmt = stmt.strip().rstrip(";")
    if stmt.startswith("return"):
        expr = stmt[len("return") :].strip()
        return _compile_expr(expr, var_regs)
    return [f"; unsupported: {stmt}"]


def _extract_body(body: str) -> List[str]:
    result: List[str] = []
    in_block = False
    for ln in body.splitlines():
        stripped = ln.strip()
        if not stripped:
            continue
        if in_block:
            if stripped.endswith("}"):
                in_block = False
            continue
        if stripped.startswith("@"):  # annotations like @space/@time
            continue
        if stripped.startswith("consume") or stripped.startswith("emit"):
            if not stripped.endswith("}"):
                in_block = True
            continue
        if stripped.startswith("memory") or stripped.startswith("!"):
            continue
        result.append(stripped)
    return result


def compile_to_nasm(funcs: List[FunctionDef]) -> str:
    """Return NASM x86_64 assembly for ``funcs``.

    Supports a very small subset of SafeLang consisting of basic arithmetic
    expressions and ``return`` statements.
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

        var_regs = {}
        for idx, ln in enumerate(fn.consume):
            match = _PARAM_RE.search(ln)
            if not match:
                continue
            if idx >= len(_PARAM_REGS):
                raise ValueError(f"{fn.name}: too many parameters")
            var_regs[match.group(2)] = _PARAM_REGS[idx]

        for stmt in _extract_body(fn.body):
            for ins in _compile_stmt(stmt, var_regs):
                lines.append(f"    {ins}")

        if space:
            lines.append(f"    add rsp, {space}")
        lines.append("    pop rbp")
        lines.append("    ret")

    return "\n".join(lines)


def generate_c(funcs: List[FunctionDef]) -> str:
    """Generate a very small C translation of ``funcs``."""
    lines = ["// Generated by SafeLang", "#include <stdint.h>", ""]
    for fn in funcs:
        try:
            params = _parse_params(fn.consume, _C_TYPE_MAP, "c")
        except ValueError as exc:
            raise ValueError(f"{fn.name}: {exc}") from exc
        lines.append(f"/* {fn.name}: @space {fn.space} @time {fn.time} */")
        lines.append(f"void {fn.name}({', '.join(params)}) {{")
        for b in _extract_body(fn.body):
            lines.append(f"    {b}")
        lines.append("}")

        lines.append("")
    return "\n".join(lines)


def generate_rust(funcs: List[FunctionDef]) -> str:
    """Generate a very small Rust translation of ``funcs``."""
    lines = ["// Generated by SafeLang", ""]
    for fn in funcs:
        try:
            params = _parse_params(fn.consume, _RUST_TYPE_MAP, "rust")
        except ValueError as exc:
            raise ValueError(f"{fn.name}: {exc}") from exc
        lines.append(f"// {fn.name}: @space {fn.space} @time {fn.time}")
        lines.append(f"pub fn {fn.name}({', '.join(params)}) {{")
        for b in _extract_body(fn.body):
            lines.append(f"    {b}")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


__all__ = ["generate_c", "generate_rust", "compile_to_nasm"]
