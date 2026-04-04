#include "safelang_runtime.h"

#include <limits.h>
#include <stdint.h>

int main(void) {
    const int bits = 63;
    const int64_t max63 = (int64_t)((1ULL << 63) - 1);

    sl_result_t add_res = sl_sat_add(max63, max63, bits, false);
    if (add_res.value != max63 || !add_res.saturated) {
        return 1;
    }

    const int64_t big = (int64_t)(1ULL << 40);
    const int64_t other = (int64_t)(1ULL << 30);
    sl_result_t mul_res = sl_sat_mul(big, other, bits, false);
    if (mul_res.value != max63 || !mul_res.saturated) {
        return 2;
    }

    const int signed_bits = 8;
    const int64_t signed_max = 127;

    sl_result_t div_res = sl_sat_div(INT64_MIN, -1, signed_bits, true);
    if (div_res.value != signed_max || !div_res.saturated) {
        return 3;
    }

    sl_result_t mod_res = sl_sat_mod(INT64_MIN, -1, signed_bits, true);
    if (mod_res.value != 0 || mod_res.saturated) {
        return 4;
    }

    return 0;
}
