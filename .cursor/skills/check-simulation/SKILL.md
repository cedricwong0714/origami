---
name: check-simulation
description: Checks ODE/simulation outputs for physical consistency (non-negative states, mass balance, solver flags). Use after running kinetic or dose-response simulations.
disable-model-invocation: true
---

# check-simulation

AI advises. The Python function enforces. Humans approve.

## Authority

Call `src/ode_model/check_simulation.py::check_simulation`. Physical invariants are enforced in Python.

## When

- After an ODE or kinetics run.
- Before using trajectories as evidence for a design.

## Do

1. Feed states, times, units, and model version into `check_simulation`.
2. Report solver warnings and failed invariants as returned.
3. Keep confidence tiers honest if the run is off calibration.

## Do not

- Smooth negative concentrations in the chat.
- Present a run as validated biology because the solver finished.

## Human

A human interprets failed invariants and decides whether the model or the design is at fault.
