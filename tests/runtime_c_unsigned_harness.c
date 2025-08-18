#include "safelang_runtime.h"

int main(void) {
#ifdef TEST_ADD
    sl_sat_add(-1, 1, 8, false);
#elif defined(TEST_SUB)
    sl_sat_sub(-1, 1, 8, false);
#elif defined(TEST_MUL)
    sl_sat_mul(-1, 1, 8, false);
#elif defined(TEST_DIV)
    sl_sat_div(-1, 1, 8, false);
#elif defined(TEST_MOD)
    sl_sat_mod(-1, 1, 8, false);
#else
#error "No test operation defined"
#endif
    return 0;
}
