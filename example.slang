#!/usr/bin/env SafeLang

! SafeLang: Clamping Example with Initialization
!!!
This example demonstrates:
- Use of @init to preallocate static memory
- Domain-bound parameter clamping
- Compile-time verification of input ranges
!!!

@init
function "clamp_params_init" {
    @space 512B
    @time  10_000ns

    consume { nil }
    
    memory buffer[64] : f32   ! preallocated static memory for later use
    buffer[0] = 42.0          ! initialization logic is allowed here

    emit { nil }
}

function "clamp_params" {
    @space 128B
    @time  1000ns

    consume {
        f32(x) # [0, 3/2]       ! 0 ≤ x ≤ 1.5
        f32(y) # [-3, 4.29382)  ! -3 ≤ y < 4.29382
        f32(z) # [-inf, pi]     ! -∞ ≤ z ≤ π
    }

    x < 0.1 ? cl_x = 0
    x > 1   ? cl_x = 1

    y < -1  ? cl_y = -1
    y > 3.1 ? cl_y = 3

    z < -1.1 ? cl_z = -1.1
    z > pi   ? cl_z = 2

    emit {
        f32(cl_x) # [0, 1]
        f32(cl_y) # [-3, 3]
        f32(cl_z) # [-1.1, 2]
    }
}

! System startup
clamp_params_init()

! Valid and invalid uses
clamp_params(2, 5, 5)               ! compile-time error: input domains violated
clamp_params(0.00385, 3.2, 1.5)     ! OK: emits clamped values 0, 3, 1.5
