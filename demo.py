"""Demonstration of the SafeLang parser and saturating math."""

from safelang import (
    parse_functions,
    verify_contracts,
    sat_add,
)


def main() -> None:
    with open("example.slang") as f:
        text = f.read()

    funcs = parse_functions(text)
    errors = verify_contracts(funcs)

    print("Parsed functions:")
    for fn in funcs:
        print(f"- {fn.name} (space={fn.space}, time={fn.time})")

    if errors:
        print("Errors:\n" + "\n".join(errors))
    else:
        print("No contract errors found")

    value, saturated = sat_add(2147483640, 100, 32, signed=True)
    print(f"sat_add result={value} saturated={saturated}")


if __name__ == "__main__":
    main()
