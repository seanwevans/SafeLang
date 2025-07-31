// SafeLang JavaScript runtime helpers for saturating arithmetic.
//
// Each helper returns an object { value, saturated } describing the result of
// the operation and whether clamping occurred. All arithmetic is performed
// using JavaScript BigInts to avoid precision loss for 64-bit operations.

'use strict';

function bounds(bits, signed = true) {
  if (bits <= 0) {
    throw new Error('bits must be positive');
  }
  if (bits > 63) {
    throw new Error('bits must be 63 or less');
  }
  if (signed) {
    const max = (1n << BigInt(bits - 1)) - 1n;
    const min = -(1n << BigInt(bits - 1));
    return { min, max };
  }
  const max = (1n << BigInt(bits)) - 1n;
  return { min: 0n, max };
}

function clamp(value, bits, signed = true) {
  const { min, max } = bounds(bits, signed);
  let bigint = BigInt(value);
  if (bigint > max) {
    return { value: max, saturated: true };
  }
  if (bigint < min) {
    return { value: min, saturated: true };
  }
  return { value: bigint, saturated: false };
}

function satAdd(a, b, bits, signed = true) {
  const total = BigInt(a) + BigInt(b);
  return clamp(total, bits, signed);
}

function satSub(a, b, bits, signed = true) {
  const total = BigInt(a) - BigInt(b);
  return clamp(total, bits, signed);
}

function satMul(a, b, bits, signed = true) {
  const total = BigInt(a) * BigInt(b);
  return clamp(total, bits, signed);
}

function satDiv(a, b, bits, signed = true) {
  bounds(bits, signed); // validate bit width
  if (BigInt(b) === 0n) {
    throw new Error('division by zero');
  }
  const total = BigInt(a) / BigInt(b);
  return clamp(total, bits, signed);
}

function satMod(a, b, bits, signed = true) {
  bounds(bits, signed); // validate bit width
  if (BigInt(b) === 0n) {
    throw new Error('integer modulo by zero');
  }
  const total = BigInt(a) % BigInt(b);
  return clamp(total, bits, signed);
}

module.exports = {
  bounds,
  clamp,
  satAdd,
  satSub,
  satMul,
  satDiv,
  satMod,
};

