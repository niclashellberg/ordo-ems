# 02 — Control Core (the MPC / LP formulation)

Implemented and validated in `energy_mpc.py` (CVXPY + HiGHS). This doc is the
spec behind that file. Read both together.

## State

Two energy states, both in Wh:

```
SoC_house(k+1) = SoC_house(k) + η_c · P_hc(k) · Δt − (1/η_d) · P_hd(k) · Δt
SoC_car(k+1)   = SoC_car(k)   + η_car · P_car(k) · Δt        (when car available)
```

- `P_hc` house charge power, `P_hd` house discharge power (split, both ≥ 0).
- Splitting into separate charge/discharge variables keeps the model **linear**.
  Round-trip efficiency loss means the optimum never charges and discharges
  simultaneously — so **no integer variable is needed** for that.

## Decision variables (per timestep k)

`P_hc, P_hd, P_car, P_import, P_export` — all in W, all ≥ 0.
Plus `SoC_house, SoC_car` trajectories.

## Meter balance (the heart of it)

```
P_load(k) + P_hc(k) + P_car(k) + P_export(k)
   = P_solar(k) + P_hd(k) + P_import(k)
```

Because car-charging-from-house-battery is **allowed**, `P_hd` can supply `P_car`
through this balance with no extra constraint.

## Pricing — ASYMMETRIC, get this exactly right

VAT and the grid (net-owner) fee apply to **import only**:

```
price_buy(k)  = spot(k) · (1 + VAT) + grid_fee     ← what you pay to import
price_sell(k) = spot(k)                            ← what you're paid to export
```

So `price_buy > price_sell` always. This spread creates a **no-arbitrage
dead-band**: round-tripping through the grid only pays when the future-buy vs
now-sell gap exceeds the spread *and* the round-trip efficiency loss.

**Do not collapse buy and sell into one price** — that produces a controller that
over-cycles the battery for no profit and wears it out. The LP handles the
dead-band automatically given both vectors.

Consequence (falls out for free, don't hand-code it): since export pays the lower
raw spot, the optimizer prefers **self-consumption** — using battery/solar for the
house and car before exporting — whenever `avoided_buy > sell`.

## Objective

```
min  Σ [ price_buy(k)·P_import(k) − price_sell(k)·P_export(k) ] · Δt
     − terminal_value · SoC_house(N)
```

Negative total = net profit over the horizon.

`terminal_value` defaults to the **mean forward buy price** (a cost-to-go proxy):
the leftover battery energy is worth roughly what it would cost to import it.

## Constraints from config

```
0 ≤ P_hc ≤ 10000           # house charge max (W)
0 ≤ P_hd ≤ 10000           # house discharge max (W)
0 ≤ P_car ≤ 2990           # 13 A × 230 V single-phase; 0 when car unavailable
0 ≤ P_export ≤ 12000       # export cap (W)
0 ≤ SoC_house ≤ 50000      # capacity (Wh)  [add a min reserve > 0 in production]
0 ≤ SoC_car ≤ E_car_max
SoC_car(deadline) ≥ car_target     # the deferrable-load deadline (an override)
```

## The time-varying Nord Pool horizon — the tricky bit

Price visibility is the constraint that shapes the controller:

- At **12:59** you see ~**11h** ahead.
- At **13:01** you see ~**35h** ahead (next-day prices publish at 13:00).

So in the window roughly **00:00–13:00**, part of any fixed 24h horizon has **no
real price data**. Naive handling either crashes, assumes zero price (and dumps
the battery), or holds a stale plan.

Correct handling:

1. Use **actual** Nord Pool prices for the known window (`n_real_prices` steps).
2. Fill the unknown tail with a **price forecast** (see `03_forecasting.md`).
3. Add the **terminal value** term so the battery isn't emptied right before the
   data runs out.
4. **Event-trigger a re-solve at 13:01** — `n_real_prices` jumps ~11 → ~35 and the
   plan can change drastically. This is a hard trigger, separate from the periodic
   re-solve.

In `energy_mpc.py`, `HorizonInputs.spot` is "real prices + forecast tail" and
`n_real_prices` marks the boundary.

## When you'd need MILP (and how to avoid it)

Stay an LP unless a requirement forces integers. Things that *would* force MILP:

- **No simultaneous grid-import + battery-discharge** — IF the hybrid inverter
  physically can't do both. This needs a binary mutual-exclusion variable.
  **Confirm the inverter capability with the user** before adding this.
- **Per-cycle battery degradation as a fixed cost** — defer.
- **Minimum car charge-session duration / minimum on-time** — defer.

LPs solve in milliseconds on a Pi; MILPs can be orders of magnitude slower. Only
pay that cost when a real requirement demands it.

## Production hardening checklist

- [ ] Add a **minimum SoC reserve** (`SoC_house ≥ reserve`) — health + buffer.
- [ ] Measure real **efficiencies**; replace the 0.95 defaults.
- [ ] Confirm **inverter simultaneous import/discharge** capability (MILP or not).
- [ ] Surface **infeasibility** (`feasible == False`) as a warning (conflicting
      overrides). See `05_llm_and_overrides.md`.
- [ ] Pre-check **car deadline reachability** at `P_car_max` given availability.

## Outputs the loop actuates

Only the **first timestep** of each solve is sent to hardware:
`P_hc[0]`, `P_hd[0]`, `P_car[0]` → inverter / car charger. Everything else is
discarded and recomputed next cycle (receding horizon).
