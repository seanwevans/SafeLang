"""Very minimal SafeLang parser for demonstration purposes."""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class FunctionDef:
    name: str
    space: str
    time: str
    consume: List[str] = field(default_factory=list)
    emit: List[str] = field(default_factory=list)


def parse_functions(text: str) -> List[FunctionDef]:
    """Parse function blocks from source text."""

    funcs: List[FunctionDef] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("function ") or line.startswith("@init"):
            if line.startswith("@init"):
                i += 1
                line = lines[i].strip()

            name_match = re.match(r"function\s+\"([^\"]+)\"", line)
            if not name_match:
                i += 1
                continue
            name = name_match.group(1)

            brace_depth = 0
            body_lines = []
            if "{" in line:
                brace_depth += 1
                body_lines.append(line.split("{", 1)[1])
            i += 1
            while i < len(lines) and brace_depth > 0:
                l = lines[i]
                brace_depth += l.count("{")
                brace_depth -= l.count("}")
                body_lines.append(l)
                i += 1

            body = "\n".join(body_lines)
            space_match = re.search(r"@space\s+([0-9]+B)", body)
            time_match = re.search(r"@time\s+([0-9_]+ns)", body)
            consume_block = re.search(r"consume\s*{([^}]*)}", body, re.S)
            emit_block = re.search(r"emit\s*{([^}]*)}", body, re.S)
            funcs.append(
                FunctionDef(
                    name=name,
                    space=space_match.group(1) if space_match else "",
                    time=time_match.group(1) if time_match else "",
                    consume=[
                        line.strip()
                        for line in (
                            consume_block.group(1).strip().splitlines()
                            if consume_block
                            else []
                        )
                        if line.strip()
                    ],
                    emit=[
                        line.strip()
                        for line in (
                            emit_block.group(1).strip().splitlines()
                            if emit_block
                            else []
                        )
                        if line.strip()
                    ],
                )
            )
        else:
            i += 1
    return funcs


def verify_contracts(funcs: List[FunctionDef]) -> List[str]:
    errors = []
    for fn in funcs:
        if not fn.space:
            errors.append(f"Function {fn.name} missing @space")
        if not fn.time:
            errors.append(f"Function {fn.name} missing @time")
        if not fn.consume:
            errors.append(f"Function {fn.name} missing consume block")
        if not fn.emit:
            errors.append(f"Function {fn.name} missing emit block")
    return errors


__all__ = ["FunctionDef", "parse_functions", "verify_contracts"]
