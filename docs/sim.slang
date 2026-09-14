#!/usr/bin/env SafeLang

! The control frame that docs/index.html runs on wall time.
!!!
Every cycle count, WCET and budget the page draws for these functions is the
output of the real analyser, not a hand-written number:

    safelang --time-report docs/sim.slang

tests/test_sim_constants.py re-runs that analysis and fails if the page and
the compiler ever disagree.
!!!

@init
function "frame_init" {
    @space 512B
    @time  10_000ns

    consume { nil }

    memory buffer[64] : f32   ! the whole arena, reserved once
    buffer[0] = 0.0

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

function "adjust_thrust" {
    @space 16B
    @time  100ns

    consume {
        f32(input) # [0, 1]
    }

    result = input * 100

    emit {
        f32(result) # [0, 100]
    }
}

function "mix_channels" {
    @space 64B
    @time  500ns

    consume {
        f32(gain) # [0, 1]
    }

    acc = 0
    loop(i = 0..7)
        acc = acc + buffer[i]

    emit {
        f32(acc) # [0, 64]
    }
}
