#include "safelang_runtime.h"

int main(void) {
    int64_t min_val = 0;
    int64_t max_val = 0;

    sl_bounds(63, true, &min_val, &max_val);
    if (min_val != -(int64_t)(UINT64_C(1) << 62)) {
        return 1;
    }
    if (max_val != (int64_t)((UINT64_C(1) << 62) - 1)) {
        return 1;
    }

    sl_bounds(63, false, &min_val, &max_val);
    if (min_val != 0) {
        return 1;
    }
    if (max_val != (int64_t)((UINT64_C(1) << 63) - 1)) {
        return 1;
    }

    return 0;
}
