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
@time_limit(ns = 1000)
@space_limit(bytes = 512)
function name(type arg1, type arg2) returns type
    assert(arg1 constraint)
    // body
    assert(return_value constraint)
    return return_value
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

---

## 📌 Attributes

* `@time_limit(ns = N)` — compile-time budget enforcement
* `@space_limit(bytes = B)` — total stack and local memory
* `@discard` — explicitly ignore return value
* `@init` — setup phase permitting limited dynamic alloc

---

See `README.md` for philosophy and `AGENTS.md` for compiler verification logic.
