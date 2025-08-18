import time
from safelang.parser import parse_functions


def test_parse_large_source_performance():
    """Parse a large synthetic source and ensure it finishes quickly."""
    func_template = (
        'function "f{0}" {{\n'
        "  @space 1B\n"
        "  @time 1ns\n"
        "  consume {{}}\n"
        "  emit {{}}\n"
        "}}\n"
    )
    count = 1000
    source = "@init\n" + "\n".join(func_template.format(i) for i in range(count))

    start = time.perf_counter()
    funcs = parse_functions(source)
    duration = time.perf_counter() - start

    assert len(funcs) == count
    assert duration < 1.0, f"Parsing took too long: {duration:.3f}s"
