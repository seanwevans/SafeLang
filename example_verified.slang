#!/usr/bin/env SafeLang

! SafeLang: an example that survives falsification
!!!
Every emit variable is given a default before the guards run, so no input in
the consume domain can leave the body with an unassigned or out-of-domain
result. Run `safelang --falsify example_verified.slang` to see the compiler
fail to falsify it.
!!!

@init
function "limits_init" {
    @space 64B
    @time  1000ns

    consume { nil }
    emit { nil }
}

function "clamp_unit" {
    @space 32B
    @time  500ns

    consume {
        f32(x) # [0, 3/2]
    }

    cl_x = x
    x > 1 ? cl_x = 1

    emit {
        f32(cl_x) # [0, 1]
    }
}

function "scale_half" {
    @space 32B
    @time  500ns

    consume {
        f32(ratio) # [0, 1]
    }

    scaled = ratio * 50

    emit {
        f32(scaled) # [0, 50]
    }
}
