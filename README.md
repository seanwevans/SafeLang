# SafeLang

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
* A mandatory `@init` function performs setup-time allocation and must run before other code

### Function Structure

* Max 50 lines per function (one line per statement or declaration)
* Each function must:

  * Declare explicit **time** and **space** budgets using `@time` and `@space`
  * Specify input and output domains via `consume` and `emit` blocks

```c
function "adjust_thrust" {
    @space 256B
    @time  1000ns

    consume {
        f32(input) # [0, 1]
    }

    result = input * 100.0

    emit {
        f32(result) # [0, 100]
    }
}
```

### Scope Discipline

* All variables must be declared in the narrowest possible scope

### Function Contracts

* All non-void functions must have their return values checked by the caller
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

* All warnings are errors
* Compiler attempts adversarial simulation of symbolic execution paths
* Compilation only succeeds if the compiler **fails to falsify** the program under any circumstances

## Runtime Behavior

* Saturating arithmetic is deterministic and portable
* Overflow never wraps or traps
* All failures (e.g., time/space overrun, assertion fail) result in predictable halt or fallback

## Target Applications

* Avionics
* Spacecraft control systems
* Nuclear reactor monitors
* Autonomous vehicle core logic

---

For information on the compiler internals and verification agents, see [AGENTS.md](AGENTS.md).
