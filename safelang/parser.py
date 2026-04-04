"""Very minimal SafeLang parser for demonstration purposes."""

import re
from bisect import bisect_right
from dataclasses import dataclass, field
from typing import List

_PARAM_RE = re.compile(r"(\w+)\(([^)]+)\)")
_DOMAIN_VALUE_RE = re.compile(
    r"""
    [+-]?(?:inf|pi|e)|
    [+-]?(?:\d+(?:_\d+)*(?:\.\d+(?:_\d+)*)?|\.\d+(?:_\d+)*)|
    [+-]?\d+(?:_\d+)*/\d+(?:_\d+)*|
    [A-Za-z_]\w*
    """,
    re.VERBOSE,
)
_DOMAIN_RE = re.compile(
    rf"^\s*([\[(])\s*({_DOMAIN_VALUE_RE.pattern})\s*,\s*({_DOMAIN_VALUE_RE.pattern})\s*([\])])\s*$",
    re.VERBOSE,
)


@dataclass
class FunctionDef:
    """Container for a parsed function's metadata and contracts."""

    name: str
    space: str
    time: str
    body: str = ""
    consume: List[str] = field(default_factory=list)
    emit: List[str] = field(default_factory=list)
    is_init: bool = False
    lines: int = 0


def _sanitize(text: str) -> str:
    """Return ``text`` with comments and strings replaced by whitespace."""

    result: List[str] = []
    i = 0
    length = len(text)
    in_string = None
    in_block_comment = False
    string_start = None
    block_start = None

    while i < length:
        ch = text[i]
        if in_block_comment:
            if text.startswith("/*", i):
                raise ValueError("Nested block comments are not supported")
            if ch == "*" and i + 1 < length and text[i + 1] == "/":
                result.append("  ")
                i += 2
                in_block_comment = False
            else:
                result.append("\n" if ch == "\n" else " ")
                i += 1
            continue

        if in_string:
            result.append("\n" if ch == "\n" else " ")
            if ch == in_string:
                # Count preceding backslashes to see if this quote is escaped.
                bs_count = 0
                j = i - 1
                while j >= 0 and text[j] == "\\":
                    bs_count += 1
                    j -= 1
                # Only terminate the string if the number of backslashes is even
                # (i.e. the quote is not escaped).
                if bs_count % 2 == 0:
                    in_string = None
            i += 1
            continue

        if text.startswith("/*", i):
            in_block_comment = True
            block_start = i
            result.append("  ")
            i += 2
            continue

        if text.startswith("//", i):
            while i < length and text[i] != "\n":
                result.append(" ")
                i += 1
            continue

        if (ch == "#" or ch == "!") and (i == 0 or text[i - 1].isspace()):
            while i < length and text[i] != "\n":
                result.append(" ")
                i += 1
            continue

        if ch in {'"', "'"}:
            in_string = ch
            string_start = i
            result.append(" ")
            i += 1
            continue

        result.append(ch)
        i += 1

    if in_block_comment:
        line = text.count("\n", 0, block_start) + 1
        raise ValueError(f"Unterminated block comment starting at line {line}")
    if in_string:
        line = text.count("\n", 0, string_start) + 1
        raise ValueError(f"Unterminated string starting at line {line}")

    return "".join(result)


def _find_matching_brace(text: str, open_pos: int) -> int:
    depth = 1
    i = open_pos + 1
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
            if depth < 0:
                line = text[:i].count("\n") + 1
                raise ValueError(f"Unmatched closing brace at line {line}")
        i += 1

    line = text[:open_pos].count("\n") + 1
    raise ValueError(f"Unterminated function block starting at line {line}")


def parse_functions(text: str) -> List[FunctionDef]:
    """Parse function blocks from source text using a simple tokenizer."""

    funcs: List[FunctionDef] = []
    sanitized = _sanitize(text)

    orig_lines = text.splitlines()
    san_lines = sanitized.splitlines()
    offsets = []
    pos = 0
    for ln in orig_lines:
        offsets.append(pos)
        pos += len(ln) + 1

    newline_positions = [idx for idx, ch in enumerate(sanitized) if ch == "\n"]

    i = 0
    while i < len(san_lines):
        line_san = san_lines[i].strip()
        line_orig = orig_lines[i].strip()
        flagged_init = False
        if line_san.startswith("@init"):
            flagged_init = True
            i += 1
            # Skip any blank or comment-only lines between @init and the function
            while i < len(san_lines) and san_lines[i].strip() == "":
                i += 1
            if i >= len(san_lines):
                raise ValueError("@init must be followed by a function definition")
            line_san = san_lines[i].strip()
            line_orig = orig_lines[i].strip()
            if not line_san.startswith("function "):
                raise ValueError("@init must be followed by a function definition")

        if line_san.startswith("function "):
            name_match = re.match(r"function\s+\"([^\"]+)\"", line_orig)
            if not name_match:
                raise ValueError(
                    f"Malformed function declaration at line {i + 1}: {line_orig}"
                )
            name = name_match.group(1)

            start_pos = offsets[i]
            next_open = sanitized.find("{", start_pos)
            next_close = sanitized.find("}", start_pos)
            if next_close != -1 and (next_open == -1 or next_close < next_open):
                error_line = sanitized.count("\n", 0, next_close) + 1
                raise ValueError(f"Unmatched closing brace at line {error_line}")
            if next_open == -1:
                raise ValueError(
                    f"Unterminated function block starting at line {i + 1}"
                )

            end_pos = _find_matching_brace(sanitized, next_open)
            body = text[next_open + 1 : end_pos]
            line_count = body.count("\n") + 1 if body else 0

            body_sanitized = sanitized[next_open + 1 : end_pos]

            space_match = re.search(r"@space\s+(\S+)", body_sanitized)
            time_match = re.search(r"@time\s+(\S+)", body_sanitized)

            space_value = (
                body[space_match.start(1) : space_match.end(1)] if space_match else ""
            )
            time_value = (
                body[time_match.start(1) : time_match.end(1)] if time_match else ""
            )

            def extract_contract(keyword: str) -> List[str]:
                match = re.search(rf"\b{keyword}\b", body_sanitized)
                if not match:
                    return []

                idx = match.end()
                while idx < len(body_sanitized) and body_sanitized[idx].isspace():
                    idx += 1

                if idx >= len(body_sanitized) or body_sanitized[idx] != "{":
                    raise ValueError(f"{keyword} block missing opening brace")

                brace_start = idx
                depth = 1
                idx += 1
                while idx < len(body_sanitized) and depth:
                    ch = body_sanitized[idx]
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            brace_end = idx
                            break
                    idx += 1
                else:
                    raise ValueError(f"Unterminated {keyword} block")

                block_text = body[brace_start + 1 : brace_end]
                lines = block_text.strip().splitlines()
                return [ln.strip() for ln in lines if ln.strip()]

            consume_entries = extract_contract("consume")
            emit_entries = extract_contract("emit")

            funcs.append(
                FunctionDef(
                    name=name,
                    space=space_value,
                    time=time_value,
                    body=body,
                    consume=consume_entries,
                    emit=emit_entries,
                    is_init=flagged_init,
                    lines=line_count,
                )
            )

            i = bisect_right(newline_positions, end_pos) + 1
            continue

        i += 1

    return funcs


def _validate_numeric_attr(
    value: str,
    pattern: str,
    errors: List[str],
    missing_msg: str,
    invalid_msg: str,
    non_positive_msg: str,
) -> None:
    """Validate a numeric attribute against a regex pattern.

    ``value`` is checked to ensure it matches ``pattern`` and represents a
    positive integer.  Any failures are appended to ``errors`` using the
    provided messages.
    """

    if not value:
        errors.append(missing_msg)
        return

    if not re.fullmatch(pattern, value):
        errors.append(invalid_msg)
        return

    try:
        numeric = int(re.sub(r"[^0-9]", "", value))
    except ValueError:
        errors.append(invalid_msg)
        return

    if numeric <= 0:
        errors.append(non_positive_msg)


def verify_contracts(funcs: List[FunctionDef]) -> List[str]:
    """Check each parsed function for required annotations and limits."""
    errors = []
    init_count = 0
    seen_names = set()
    for fn in funcs:
        if fn.name in seen_names:
            errors.append(f"Duplicate function name {fn.name}")
        else:
            seen_names.add(fn.name)

        if fn.is_init:
            init_count += 1

        _validate_numeric_attr(
            fn.space.upper(),
            r"[0-9_]+[KMGT]?B",
            errors,
            f"Function {fn.name} missing @space",
            f"Function {fn.name} invalid @space value",
            f"Function {fn.name} has non-positive @space",
        )

        _validate_numeric_attr(
            fn.time.lower(),
            r"[0-9_]+ns",
            errors,
            f"Function {fn.name} missing @time",
            f"Function {fn.name} invalid @time value",
            f"Function {fn.name} has non-positive @time",
        )

        if not fn.consume:
            errors.append(f"Function {fn.name} missing consume block")
        else:
            for entry in fn.consume:
                signature, domain_expr = _split_contract_entry(entry)
                if signature == "nil":
                    continue
                if not _PARAM_RE.fullmatch(signature):
                    errors.append(
                        f"Function {fn.name} malformed consume entry: {entry.strip()}"
                    )
                    continue
                if domain_expr is None:
                    errors.append(
                        f"Function {fn.name} consume entry missing domain: {entry.strip()}"
                    )
                    continue
                if not _is_valid_domain_expr(domain_expr):
                    errors.append(
                        f"Function {fn.name} invalid consume domain in entry: {entry.strip()}"
                    )
        if not fn.emit:
            errors.append(f"Function {fn.name} missing emit block")
        else:
            for entry in fn.emit:
                signature, domain_expr = _split_contract_entry(entry)
                if signature == "nil":
                    continue
                if not _PARAM_RE.fullmatch(signature):
                    errors.append(
                        f"Function {fn.name} malformed emit entry: {entry.strip()}"
                    )
                    continue
                if domain_expr is None:
                    errors.append(
                        f"Function {fn.name} emit entry missing domain: {entry.strip()}"
                    )
                    continue
                if not _is_valid_domain_expr(domain_expr):
                    errors.append(
                        f"Function {fn.name} invalid emit domain in entry: {entry.strip()}"
                    )
        if fn.lines > 128:
            errors.append(f"Function {fn.name} exceeds 128 line limit")

    if init_count == 0:
        errors.append("No @init function defined")
    elif init_count > 1:
        errors.append("Multiple @init functions defined")

    return errors


def _split_contract_entry(entry: str) -> tuple[str, str | None]:
    """Split a contract line into a signature and optional domain fragment."""

    signature_fragment, domain_fragment = entry, None
    if "#" in entry:
        signature_fragment, domain_fragment = entry.split("#", 1)

    signature = signature_fragment.split("!", 1)[0].strip()
    if domain_fragment is None:
        return signature, None

    domain = domain_fragment.split("!", 1)[0].strip()
    return signature, domain or None


def _is_valid_domain_expr(domain_expr: str) -> bool:
    """Validate SafeLang domain interval fragments."""

    return bool(_DOMAIN_RE.fullmatch(domain_expr))


__all__ = ["FunctionDef", "parse_functions", "verify_contracts"]
