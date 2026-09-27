"""Literature thermal-table loading.

Observations are read from caller-supplied JSON. This package does not
embed melting temperatures or other biological constants.
"""

from origami.stability.table import ThermalObservation, load_thermal_table

__all__ = ["ThermalObservation", "load_thermal_table"]
