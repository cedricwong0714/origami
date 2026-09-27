"""Configuration checks for ODE simulation runs (no biology invented)."""

from __future__ import annotations


def check_simulation(sim_config: dict) -> list[str]:
    """Return error strings for invalid simulation configuration.

    Errors when:
    - ``model_version`` is missing or empty
    - ``timestep`` is missing or ``<= 0``
    - units are missing (``units`` key absent/empty, or empty ``units`` mapping)
    - ``calibrated`` is True without a ``dataset_id``
    """
    errors: list[str] = []
    if not isinstance(sim_config, dict):
        return ["sim_config must be a dict"]

    model_version = sim_config.get("model_version")
    if model_version is None or str(model_version).strip() == "":
        errors.append("missing model_version")

    if "timestep" not in sim_config:
        errors.append("timestep<=0")
    else:
        try:
            timestep = float(sim_config["timestep"])
        except (TypeError, ValueError):
            errors.append("timestep<=0")
        else:
            if timestep <= 0:
                errors.append("timestep<=0")

    units = sim_config.get("units")
    missing_units = units is None or units == "" or units == {}
    if missing_units:
        errors.append("missing units")

    calibrated = sim_config.get("calibrated")
    if calibrated is True:
        dataset_id = sim_config.get("dataset_id")
        if dataset_id is None or str(dataset_id).strip() == "":
            errors.append("calibrated flag True without dataset_id")

    return errors
