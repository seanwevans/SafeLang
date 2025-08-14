#ifndef SAFELANG_RUNTIME_H
#define SAFELANG_RUNTIME_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Result of a saturating arithmetic operation. */
typedef struct {
    int64_t value;     /* clamped result */
    bool saturated;    /* whether saturation occurred */
} sl_result_t;

/** Compute representable bounds for the specified bit width. */
void sl_bounds(int bits, bool signed_arith, int64_t *min_out, int64_t *max_out);

/** Clamp the given value to the representable range. */
sl_result_t sl_clamp(int64_t value, int bits, bool signed_arith);

/** Saturating addition. Aborts if unsigned and either operand is negative. */
sl_result_t sl_sat_add(int64_t a, int64_t b, int bits, bool signed_arith);

/** Saturating subtraction. Aborts if unsigned and either operand is negative. */
sl_result_t sl_sat_sub(int64_t a, int64_t b, int bits, bool signed_arith);

/** Saturating multiplication. Aborts if unsigned and either operand is negative. */
sl_result_t sl_sat_mul(int64_t a, int64_t b, int bits, bool signed_arith);

/** Saturating division. Aborts on division by zero or if unsigned with negative operands. */
sl_result_t sl_sat_div(int64_t a, int64_t b, int bits, bool signed_arith);

/** Saturating modulo. Aborts on division by zero or if unsigned with negative operands. */
sl_result_t sl_sat_mod(int64_t a, int64_t b, int bits, bool signed_arith);

#ifdef __cplusplus
}
#endif

#endif /* SAFELANG_RUNTIME_H */
