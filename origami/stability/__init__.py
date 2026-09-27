"""Literature thermal-table loading.

Observations are read from caller-supplied JSON. This package does not
embed melting temperatures or other biological constants.
"""

from origami.stability.series import (
    PHILLIPS_2012_CTPRA_DSC,
    load_named_series,
    literature_table_path,
)
from origami.stability.table import ThermalObservation, load_thermal_table

__all__ = [
    "PHILLIPS_2012_CTPRA_DSC",
    "ThermalObservation",
    "literature_table_path",
    "load_named_series",
    "load_thermal_table",
]
