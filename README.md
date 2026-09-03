# SafeLang
<img width="256" alt="what? you don't use the back of your clipboard?" src="https://github.com/user-attachments/assets/34594266-6058-4662-84d4-bc13be6f0243" />

![Coverage](coverage.svg)
[![CI](https://github.com/seanwevans/SafeLang/actions/workflows/ci.yml/badge.svg)](https://github.com/seanwevans/SafeLang/actions/workflows/ci.yml)

SafeLang is a programming language designed for **hard real-time, safety-critical embedded systems**, inspired by NASA's 10 rules for developing safety-critical code. It aims to produce software that is provably safe, resilient to overflow and misuse, and adversarially verified.

## Philosophy

> "The program is assumed correct. The compiler's job is to prove that false."

The SafeLang compiler is not your assistant. It is your adversary. It attempts to falsify the program by searching for an input—no matter how edge-case—that violates a declared contract. Code that survives has *survived a hostile proof-of-safety*.

That posture is implemented, not aspirational: `safelang --falsify` hands the
`consume`/`emit` domains and the function body to the Z3 SMT solver and asks it
for a counterexample. What the pass covers today, and where it stops, is spelled
out under [Falsification](#falsification) — read that section before treating a
clean run as a proof.

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

Both budgets are enforced, not decorative. `@space` becomes the stack
reservation in the generated NASM, and `@time` is checked against a static
worst-case execution time estimate — see [Time budgets](#time-budgets).

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
* A JavaScript runtime is available in `safelang/runtime.js` providing the same
  saturating helpers for Node.js environments.

The runtime exposes helpers `sat_add`, `sat_sub`, `sat_mul`, `sat_div`, and
`sat_mod` implementing these semantics.
A portable C implementation of these helpers is available under
`runtime-c/` for use with generated C code.

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
* Under `--falsify`, the compiler symbolically executes each function body and
  asks an SMT solver to break its `emit` contracts
* Compilation succeeds only if the solver **fails to falsify** every obligation
  it was able to model. A body containing a construct the solver cannot model is
  reported `INCONCLUSIVE` and fails — the pass never reports a proof over code it
  did not read.

## Falsification

`safelang --falsify FILE` runs the adversarial pass. For each function it treats
every `consume` domain as an assumption and every `emit` domain as a proof
obligation, symbolically executes the body, and asks
[Z3](https://github.com/Z3Prover/z3) for a witness that breaks an obligation.

Install the solver alongside the package:

```bash
pip install 'safelang-verifier[verify]'      # from PyPI
python -m pip install -e '.[verify]'         # from a checkout
```

Each function comes back with one of three verdicts:

| Verdict | Meaning |
| --- | --- |
| `OK` | The solver proved no input in the `consume` domains can break the `emit` domains. |
| `FALSIFIED` | The solver produced a concrete counterexample, printed as a witness. |
| `INCONCLUSIVE` | The body used a construct outside the modelled subset, so no verdict is claimed. |

`FALSIFIED` and `INCONCLUSIVE` both exit non-zero.

### A worked example

The bundled `example.slang` does not survive. Its clamps guard only the tails:

```c
x < 0.1 ? cl_x = 0
x > 1   ? cl_x = 1
```

Nothing assigns `cl_x` when `0.1 ≤ x ≤ 1`, and the solver says so:

```bash
$ safelang --falsify example.slang
OK: clamp_params_init survived falsification (no emit domain obligations to falsify)
FALSIFIED: clamp_params: cl_x: can leave the body unassigned [witness: x=0.1, y=0, z=0]
```

`example_verified.slang` closes the gap by assigning a default before the
guards run, and survives:

```bash
$ safelang --falsify example_verified.slang
OK: limits_init survived falsification (no emit domain obligations to falsify)
OK: clamp_unit survived falsification
OK: scale_half survived falsification
```

### What the pass checks

* Every `emit` variable is assigned on **every** path through the body
* Every `emit` variable stays inside its declared domain for **every** input
  permitted by the `consume` domains
* No division can be reached with a zero divisor

### What the pass does not check — yet

These are honest limits, not fine print. A clean run proves the three properties
above and nothing else:

* **Values are modelled as mathematical reals.** Floating-point rounding and
  integer saturation are not modelled, so a domain proven here is proven for
  exact arithmetic.
* **Only three statement forms are understood:** `name = expr`,
  `cond ? name = expr`, and `return expr`. Arrays, `memory` declarations,
  `loop`, `if`/`else`, `match`, and calls make a function `INCONCLUSIVE`.
* **Contracts are not composed across calls.** Each function is falsified in
  isolation; a caller passing out-of-domain arguments is not yet detected.
* **`@space` and `@time` budgets are not part of this pass.**

## Time budgets

Every function declares a `@time` budget, and the compiler checks it. It walks
the body, adds up a cycle cost for every operation, converts the total to
nanoseconds against a target clock, and rejects any function whose worst case
does not fit:

```bash
$ safelang --time-report example.slang
OK: clamp_params_init: 2 cycles = 20ns against a 10000ns budget
OK: clamp_params: 34 cycles = 340ns against a 1000ns budget
```

The check runs by default. `--clock-mhz` sets the target clock (100 MHz by
default, which makes one cycle exactly 10ns), and `--no-time-check` skips the
analysis.

### The cost model

The model approximates a simple in-order core with no cache, no pipeline
overlap and no speculation — the machine a hard-real-time budget is usually
written against:

| Operation | Cycles |
| --- | --- |
| move / assignment | 1 |
| add, subtract | 1 |
| multiply | 3 |
| divide, modulo | 20 |
| comparison | 1 |
| taken branch | 2 |
| array index | 1 |
| function call | 5 |
| return | 1 |

Control flow is costed conservatively. A `loop(i = a..b)` costs its full static
trip count, an `if`/`else` costs its more expensive arm, and a `match` pays to
test every arm and then take the priciest one.

### What it refuses to do

The estimator will not invent a number it cannot justify. A loop whose bounds
are not compile-time constants has no worst case, and is reported as an error
rather than being assigned a guess:

```
ERROR: Function scan has no bounded worst case: loop bound 'n' is not a
compile-time constant; SafeLang loops must have statically provable bounds
```

The estimate is a static upper bound on a simplified machine, not a measurement.
It catches a budget nobody could meet; it does not replace timing the code on
real silicon.

## Runtime Behavior

* Saturating arithmetic is deterministic and portable
* Overflow never wraps; instead the runtime returns the clamped value and
  reports saturation
* All failures (e.g., time/space overrun, assertion fail) result in predictable halt or fallback


## CLI Usage

Install the package to expose the ``safelang`` command line tool and run the verifier.

1. Install from PyPI:

   ```bash
   pip install safelang-verifier
   ```

   The distribution is named `safelang-verifier` because the bare `safelang`
   name on PyPI belongs to an unrelated placeholder package. The import package
   and the command are both still `safelang`.

   To work on SafeLang itself, install it from a checkout instead:

   ```bash
   python -m pip install -e '.[dev]'
   ```

2. Execute the verifier on a SafeLang source file:

   ```bash
   safelang example.slang
   ```

   Example output:

   ```
   Parsed 2 functions successfully.
   ```

   Every backend has the same pair of options: ``--emit-NAME`` writes the
   generated code to stdout, and ``--NAME-out PATH`` writes it to a file. The
   options are mutually exclusive -- one run produces one output.

   | Backend | To stdout | To a file |
   | --- | --- | --- |
   | C | `--emit-c` | `--c-out PATH` |
   | Rust | `--emit-rust` | `--rust-out PATH` |
   | NASM x86-64 | `--emit-nasm` | `--nasm-out PATH` |

   ```bash
   safelang --emit-c example.slang
   safelang --emit-rust example.slang
   safelang --emit-nasm example.slang
   safelang --nasm-out out.asm example.slang
   ```

   ``--nasm PATH`` is still accepted as a deprecated alias for ``--nasm-out``
   and prints a warning.

   To run the adversarial falsification pass, add ``--falsify`` (needs the
   ``verify`` extra installed):

   ```bash
   safelang --falsify example_verified.slang
   ```

   To see the worst-case execution time estimate for each function, use
   `--time-report`:

   ```bash
   safelang --time-report example.slang
   ```

   If a function is missing `@space`, `@time`, `consume`, or `emit` blocks, exceeds the 128 line limit, or cannot meet its declared `@time` budget, the CLI prints `ERROR:` messages and exits with a non‑zero status.

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

Install the development extra and execute the suite:

```bash
python -m pip install -e '.[dev]'
pytest
```

## Releasing

See [RELEASING.md](RELEASING.md).

