# SafeLang

![Coverage](coverage.svg)

SafeLang is a programming language designed for **hard real-time, safety-critical embedded systems**, inspired by NASA's 10 rules for developing safety-critical code. It aims to produce software that is provably safe, resilient to overflow and misuse, and adversarially verified.

## Philosophy

> "The program is assumed correct. The compiler's job is to prove that false."

The SafeLang compiler is not your assistant. It is your adversary. It attempts to falsify the program by discovering any possible scenario—no matter how edge-case—that could cause failure, overflow, undefined behavior, or constraint violation. Code that compiles in SafeLang has *survived a hostile proof-of-safety*.

## Design Principles

### Control Flow

* Only simple, bounded control flow constructs allowed: `if`, `match`, `loop(start..end)`
* No recursion, no `goto`, no exceptions

### Loops

* All loops must have statically provable upper bounds

### Memory Management

* No dynamic allocation after initialization
* Exactly one `@init` function performs setup-time allocation and must run before other code

### Function Structure

* Max 128 lines per function (one line per statement or declaration)
* Each function must:

  * Declare explicit **time** and **space** budgets using `@time` and `@space`
  * Specify input and output domains via `consume` and `emit` blocks

```c
function "adjust_thrust" {
    @space 16B
    @time  100ns

    consume {
        f32(input) # [0, 1]
    }

    result = input * 100

    emit {
        f32(result) # [0, 100]
    }
}
```

### Scope Discipline

* All variables must be declared in the narrowest possible scope

### Function Contracts

* All functions must have their return values checked by the caller
* Input validation is expressed through `consume` domain constraints

### Preprocessor Constraints

* Only `#include` and simple `#define` of constants allowed
* No macros with logic or conditional compilation

### Pointer Rules

* Max 2 levels of indirection allowed: `T`, `T*`, `T**`
* Triple-indirection (`T***`) and beyond is disallowed

### Saturating Arithmetic

* All arithmetic operations are saturating by default
* Arithmetic is performed using a **widened type**, then clamped to the original type's bounds
* The Python demo runtime returns the clamped value along with a boolean flag
  indicating whether saturation occurred. No exception is raised on overflow.

The runtime exposes helpers `sat_add`, `sat_sub`, `sat_mul`, `sat_div`, and
`sat_mod` implementing these semantics.

```c
int32 sat_add(int32 a, int32 b)
    int64 sum = (int64)a + (int64)b
    if sum > INT32_MAX
        return INT32_MAX
    else if sum < INT32_MIN
        return INT32_MIN
    else
        return (int32)sum
```

### Compilation Discipline

* All errors are critical
* All warnings are errors, which are critical
* All info are warnings, which are errors, which are critical
* Compiler attempts adversarial simulation of symbolic execution paths
* Compilation only succeeds if the compiler **fails to falsify** the program under any circumstances

## Runtime Behavior

* Saturating arithmetic is deterministic and portable
* Overflow never wraps; instead the runtime returns the clamped value and
  reports saturation
* All failures (e.g., time/space overrun, assertion fail) result in predictable halt or fallback


## CLI Usage

Install the package to expose the ``safelang`` command line tool and run the verifier.

1. Install the project in editable mode:

   ```bash
   python -m pip install -e .
   ```

2. Execute the verifier on a SafeLang source file:

   ```bash
   safelang example.slang
   ```

   Example output:

   ```
   Parsed 2 functions successfully.
   ```

   If a function is missing `@space`, `@time`, `consume`, or `emit` blocks, or exceeds the 128 line limit, the CLI prints `ERROR:` messages and exits with a non‑zero status.

3. Alternatively, run the demonstration script which also showcases saturating arithmetic:

   ```bash
   python demo.py
   ```

   Example output:

   ```
   Parsed functions:
   - clamp_params_init (space=512B, time=10_000ns)
   - clamp_params (space=128B, time=1000ns)
   No contract errors found
   sat_add result=2147483647 saturated=True
   ```

## Running Tests

Install pytest and execute the suite:

```bash
python -m pip install pytest
pytest
```


## License

This project is licensed under the [MIT License](LICENSE).

---

For information on the compiler internals and verification agents, see [AGENTS.md](AGENTS.md).


