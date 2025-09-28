#include "safelang_runtime.h"
#include <stdlib.h> /* for abort */

static void check_bits(int bits) {
    if (bits <= 0 || bits > 63) {
        abort();
    }
}

void sl_bounds(int bits, bool signed_arith, int64_t *min_out, int64_t *max_out) {
    check_bits(bits);
    if (signed_arith) {
        uint64_t magnitude = UINT64_C(1) << (bits - 1);
        int64_t max_val = (int64_t)(magnitude - 1);
        int64_t min_val = -(int64_t)magnitude;
        if (min_out) *min_out = min_val;
        if (max_out) *max_out = max_val;
    } else {
        uint64_t magnitude = UINT64_C(1) << bits;
        int64_t max_val = (int64_t)(magnitude - 1);
        int64_t min_val = 0;
        if (min_out) *min_out = min_val;
        if (max_out) *max_out = max_val;
    }
}

static sl_result_t clamp_internal(int64_t value, int64_t min_val, int64_t max_val) {
    sl_result_t result;
    if (value > max_val) {
        result.value = max_val;
        result.saturated = true;
    } else if (value < min_val) {
        result.value = min_val;
        result.saturated = true;
    } else {
        result.value = value;
        result.saturated = false;
    }
    return result;
}

static sl_result_t clamp_from_wide(__int128 wide_value, int64_t min_val, int64_t max_val) {
    sl_result_t result;
    if (wide_value > (__int128)max_val) {
        result.value = max_val;
        result.saturated = true;
    } else if (wide_value < (__int128)min_val) {
        result.value = min_val;
        result.saturated = true;
    } else {
        result.value = (int64_t)wide_value;
        result.saturated = false;
    }
    return result;
}

sl_result_t sl_clamp(int64_t value, int bits, bool signed_arith) {
    int64_t min_v, max_v;
    sl_bounds(bits, signed_arith, &min_v, &max_v);
    return clamp_internal(value, min_v, max_v);
}

sl_result_t sl_sat_add(int64_t a, int64_t b, int bits, bool signed_arith) {
    if (!signed_arith && (a < 0 || b < 0)) {
        abort();
    }
    int64_t min_v, max_v;
    sl_bounds(bits, signed_arith, &min_v, &max_v);
    __int128 total = (__int128)a + (__int128)b;
    return clamp_from_wide(total, min_v, max_v);
}

sl_result_t sl_sat_sub(int64_t a, int64_t b, int bits, bool signed_arith) {
    if (!signed_arith && (a < 0 || b < 0)) {
        abort();
    }
    int64_t min_v, max_v;
    sl_bounds(bits, signed_arith, &min_v, &max_v);
    __int128 total = (__int128)a - (__int128)b;
    return clamp_from_wide(total, min_v, max_v);
}

sl_result_t sl_sat_mul(int64_t a, int64_t b, int bits, bool signed_arith) {
    if (!signed_arith && (a < 0 || b < 0)) {
        abort();
    }
    int64_t min_v, max_v;
    sl_bounds(bits, signed_arith, &min_v, &max_v);
    __int128 total = (__int128)a * (__int128)b;
    return clamp_from_wide(total, min_v, max_v);
}

sl_result_t sl_sat_div(int64_t a, int64_t b, int bits, bool signed_arith) {
    if (!signed_arith && (a < 0 || b < 0)) {
        abort();
    }
    if (b == 0) {
        abort();
    }
    int64_t total = a / b;
    int64_t min_v, max_v;
    sl_bounds(bits, signed_arith, &min_v, &max_v);
    return clamp_internal(total, min_v, max_v);
}

sl_result_t sl_sat_mod(int64_t a, int64_t b, int bits, bool signed_arith) {
    if (!signed_arith && (a < 0 || b < 0)) {
        abort();
    }
    if (b == 0) {
        abort();
    }
    int64_t total = a % b;
    int64_t min_v, max_v;
    sl_bounds(bits, signed_arith, &min_v, &max_v);
    return clamp_internal(total, min_v, max_v);
}
