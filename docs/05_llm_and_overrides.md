# 05 — LLM Layer & Override Mechanism

## Hard rule: the LLM is never in the control loop

The optimizer is the **single source of truth** for hardware actions. The LLM does
exactly two things, both outside the loop:

1. **Explain** the solved schedule (post-hoc narration).
2. **Parse** natural-language overrides into **structured, schema-validated**
   objects — which then compile to LP constraints. The LLM never emits setpoints.

This keeps control deterministic and safe while giving you explainability.

## Single interface, two backends

Define one interface; a config flag picks the backend:

```python
def explain(schedule, forecasts, duals) -> str
def parse_override(free_text) -> Override        # validated against schema
```

### Cloud LLM (API)
- Pro: best reasoning, best override parsing, no local compute.
- Con: needs internet, costs per call, sends home energy data out (privacy).
- Use for: override parsing and richer explanations.

### Local LLM (Ollama on the training machine or a capable HA host)
- Pro: private, free per call, offline-capable.
- Con: needs a decent machine (7–14B on GPU, slow on CPU); weaker parsing.
- Use for: routine explanations.

Both consume the **same structured optimizer output**. The training machine is the
natural host for a local model (it has the compute and isn't latency-critical).

## Grounding explanations in duals (shadow prices)

Feed the LP's **dual values** to the explanation LLM. Duals tell you *which
constraint was binding* — e.g. "the export cap limited things at 13:00" or "the
SoC ceiling blocked more charging at noon." This turns vague narration into
grounded, correct explanations: the duals are the optimizer's own reasoning made
numeric. Extend `SolveResult.duals` in `energy_mpc.py` to capture the relevant
constraint duals.

## Overrides = constraints, NOT code paths

The most important architectural decision here. Do **not** special-case each
override with `if`-statements. Every override compiles to a modification of the
LP — an added constraint, a changed bound, or an added cost/load term. This keeps
overrides **composable**, **safe** (still constraint-checked), and **explainable**
by the same duals machinery.

### Layered model

1. **Base layer** — the profit-optimizing LP.
2. **Override layer** — a list of structured `Override` objects, each modifying
   the problem.
3. **Resolution rule** — overrides are constraints; if two conflict, the solver
   returns **infeasible**, which is a warning trigger ("I can't both charge the
   car full by 7am and reserve 30 kWh for the outage").

### Override kinds (see `energy_mpc.py: Override`)

| Natural language | Compiles to |
|---|---|
| "Charge the car full by tomorrow 07:00" | `car_deadline`: `SoC_car(step) ≥ target_wh` (hard) or slack-penalized (soft) |
| "Reserve battery for an outage Friday 18:00" | `house_reserve`: `SoC_house(step) ≥ reserve_wh` |
| "Sauna 19:00–20:00 Saturday" | `extra_load`: inject `+power_w` into the load vector over the window *before* solving (cleaner than a constraint) |

`hard=True` adds a hard constraint; `hard=False` adds a slack variable with a
large finite penalty so it's prioritized but yields if physically impossible.

### The safe parse pattern

```
free text → LLM → structured Override (proposal)
          → validate against schema
          → compile to LP constraint / load injection
          → solve
```

The LLM proposes structured intent; the schema validates it; the optimizer remains
the single source of truth. The LLM never touches hardware directly.

## Build notes

- Define the `Override` JSON schema explicitly and validate every parsed object
  before it reaches `solve_mpc`. Reject anything that doesn't conform — never pass
  an unvalidated LLM output into the solver.
- Map natural-language times to horizon step indices using the loop's clock and
  `dt_h`; do this in the parser/compiler, not in the LLM.
- Keep an audit log of: free text → parsed override → solve result, for debugging
  and for the explanation layer.
