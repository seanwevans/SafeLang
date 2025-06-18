# SafeLang Compiler Agents

The SafeLang compiler is structured as an **adversarial verification system**, composed of modular agents that collectively try to break the user’s code. These agents simulate, symbolically execute, and reason about the safety of a given program, rejecting anything that fails to meet rigorous proof-of-safety standards.

---

## 🎯 Agent Philosophy

> Every line of code is guilty until proven safe.

Each agent represents a specialized verifier or attack vector against your assumptions. The collective goal is to simulate real-world failures, edge conditions, hardware faults, and logic gaps before your system ever leaves the ground.

---

## 🔍 Core Compiler Agents

### 1. **Scope Shrinker**

* Enforces minimal lifetime and smallest scope declarations
* Flags excessive or function-level variable declarations

### 2. **Loop Bound Verifier**

* Requires statically provable numeric bounds on all loops
* Rejects data-dependent or infinite constructs

### 3. **Arithmetic Saturator**

* Translates all arithmetic to widened-upcast forms
* Clamps results to type bounds
* Flags frequent clamping for review

### 4. **Interface Contract Enforcer**

* Ensures every function declares `consume` and `emit` domains
* Rejects functions missing input or output constraints

### 5. **Pointer Depth Checker**

* Disallows triple-indirection
* Verifies pointer integrity against scope, aliasing, and type rules

### 6. **Memory Discipline Agent**

* Blocks dynamic allocation outside `@init`
* Verifies static stack and preallocated buffers

### 7. **Function Contract Checker**

* Verifies domain constraints from `consume` and `emit` blocks
* Ensures all return values are consumed or explicitly discarded with `@discard` tag

### 8. **Time/Space Budget Analyzer**

* Verifies declared `@time` and `@space` budgets
* Performs static cost modeling and simulation
* Flags any call paths that may exceed bounds

### 9. **Symbolic Adversary**

* Symbolically executes all control paths to search for logical contradictions
* Attempts to generate falsifying counterexamples
* Uses SMT-style reasoning to explore edge conditions

### 10. **Compile-Time Intrinsic Rewriter**

* Rewrites `+`, `-`, `*`, `/`, `%` to saturated forms using widened ops
* Maps to hardware instructions if available

---

## 🧪 Optional Agents (Configurable)

### - **Saturation Auditor**

Reports saturation hotspots to aid in refactoring or confirming expected clamping

### - **Interrupt Safety Checker**

Validates ISR-safe memory, atomic use, and scheduling points

### - **Watchdog Synthesizer**

Generates hardware watchdog fallback logic if time budgets are overrun

### - **Trace Generator**

Captures falsification traces for external replay/fuzz testing

---

## 🧠 Outcome

If your code survives all agents without falsification or violation, it is deemed **conditionally safe** under the current spec.

SafeLang doesn’t promise your code is perfect.

It promises your code survived a fight against everything the system could throw at it.

---

For language philosophy and core syntax, see [README.md](README.md).
