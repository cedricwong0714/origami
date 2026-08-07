# ORIGAMI local sandbox

One-command local website for testing ORIGAMI (Streamlit UI + static demos).

## Quick start (Windows)

From the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_sandbox.ps1
```

Or double-click `scripts\run_sandbox.bat`.

First run creates `.venv`, installs `.[ui,dev]`, then opens:

| Surface | URL |
|---------|-----|
| Streamlit (Explore / Design / Optimize / Learn) | http://localhost:8501 |
| Static Pages landing | http://localhost:8080/ |
| CTPR scaffold optimizer HTML | http://localhost:8080/ctpr_scaffold_optimizer.html |

Stop with **Ctrl+C**.

## Options

```powershell
# Custom ports
.\scripts\run_sandbox.ps1 -Port 8502 -StaticPort 8081

# Skip reinstall (faster subsequent starts)
.\scripts\run_sandbox.ps1 -SkipInstall

# Streamlit only (no static web/)
.\scripts\run_sandbox.ps1 -NoStatic
```

## Manual alternative

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[ui,dev]"
streamlit run app.py
```

## What you can test

1. **Explore** — evidence retrieval / honest refusal  
2. **Design** — CTPR geometry, mechanism profiles (incl. trans-activation), passport  
3. **Optimize** — CTPR spacing ranking → handoff to Design  
4. **Learn** — load synthetic CSV package, compare ODE vs data  
5. **CLI** (separate terminal): `origami freeze`, `origami optimize`, `origami validate-learn`

Synthetic Learn fixtures are **not** Tier-1 lab data.
