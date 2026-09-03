# SafeLang Specification

This document outlines the formal specification of SafeLang's type system, syntax rules, and structural grammar. It serves as the reference implementation target for compiler developers.

---

## 🎯 Core Goals

* Strong typing with zero implicit conversions
* Predictable memory and control flow
* Bounded runtime and memory usage
* Fully statically verifiable constraints

---

## 🎛 Type System

### Primitive Types

| Type      | Description     | Range              |
| --------- | --------------- | ------------------ |
| `int8`    | signed 8-bit    | \[-128, 127]       |
| `uint8`   | unsigned 8-bit  | \[0, 255]          |
| `int16`   | signed 16-bit   | \[-32,768, 32,767] |
| `uint16`  | unsigned 16-bit | \[0, 65,535]       |
| `int32`   | signed 32-bit   | \[-2^31, 2^31-1]   |
| `uint32`  | unsigned 32-bit | \[0, 2^32-1]       |
| `int64`   | signed 64-bit   | \[-2^63, 2^63-1]   |
| `uint64`  | unsigned 64-bit | \[0, 2^64-1]       |
| `bool`    | Boolean         | `true`, `false`    |
| `float32` | 32-bit float    | IEEE-754           |
| `float64` | 64-bit float    | IEEE-754           |

All arithmetic on integer types is **saturating** and implemented via **upcast + clamp**.
If clamping would occur at runtime, the runtime returns the clamped value and
indicates that saturation occurred.

### Compound Types

* `T*`: pointer to T
* `T**`: pointer to pointer to T
* Pointers beyond 2 levels (`T***`) are disallowed

### Arrays

* `T[N]`: fixed-size array
* Array size `N` must be compile-time constant

### Structs

```c
struct Vec3
    float32 x
    float32 y
    float32 z
```

---

## 🔣 Syntax Overview

### Function

```c
@init
function "name" {
    @space 512B
    @time  1000ns

    consume {
        f32(arg1) # [0, 1]
        f32(arg2) # [-1, 1]
    }

    // body

    emit {
        f32(result) # [0, 1]
    }
}
```

### Loop

```c
loop(i = 0..9)
    // body
```

### If/Else

```c
if cond
    ...
else
    ...
```

### Match

```c
match value
    case A => ...
    case B => ...
```

### Constants

```c
const PI = 3.1415
```

### Modules & Imports

```c
import "hardware"
```

---

## 🚫 Disallowed Constructs

* Dynamic memory (except in `@init`)
* Recursion
* Macros beyond `#define CONSTANT`
* `goto`, `break`, `continue`, unlabeled jumps
* Function pointers

---

## 🧪 Runtime Model

* All arithmetic uses **saturating upcast logic**
* Every function's time/space contract must be statically analyzable
* Violations trigger compile-time rejection or runtime trap (if enabled)

### Timing analysis

A function's worst-case execution time is the sum of the cycle costs of the
operations it performs, evaluated against a target clock (100 MHz by default):

| Operation | Cycles |
| --------- | ------ |
| move / assignment | 1 |
| add, subtract | 1 |
| multiply | 3 |
| divide, modulo | 20 |
| comparison | 1 |
| taken branch | 2 |
| array index | 1 |
| function call | 5 |
| return | 1 |

Control flow is costed for its worst case: a `loop(i = a..b)` contributes its
full static trip count, an `if`/`else` contributes its more expensive arm, and a
`match` tests every arm before taking the priciest one. A `memory` declaration
reserves space at `@init` time and costs nothing at runtime.

A construct with no statically provable worst case — most importantly a loop
whose bounds are not compile-time constants — is a compile-time error. The
analysis never substitutes an estimate for a bound it cannot prove.

---

## 📌 Attributes

* `@time Nns`  — per-function time budget, checked against a static worst-case
  execution time estimate (see *Timing analysis* above)
* `@space NB`  — total stack and local memory, emitted as the stack reservation
* `@init` — exactly one function marked with this attribute performs required setup-time allocation

---

See `README.md` for philosophy and `AGENTS.md` for compiler verification logic.
