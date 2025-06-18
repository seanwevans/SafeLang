# SafeLang C Runtime

This directory provides a minimal C implementation of SafeLang's
saturating arithmetic helpers.  The routines mirror the behavior of the
Python runtime found in `safelang/runtime.py`.

The API exposes a `sl_result_t` structure which contains the clamped
result and a flag indicating whether saturation occurred.

```
sl_result_t sl_sat_add(int64_t a, int64_t b, int bits, bool signed);
```

All operations abort on invalid bit width or division by zero. The
functions support bit widths up to 63 bits.

Compile the runtime into a static library:

```
cc -c safelang_runtime.c -o safelang_runtime.o
ar rcs libsafelang.a safelang_runtime.o
```

You can then link `libsafelang.a` with generated C code from the
SafeLang compiler.
