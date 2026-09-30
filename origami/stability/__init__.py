"""Literature thermal-table loading.

Observations are read from caller-supplied JSON. This package does not
embed melting temperatures or other biological constants.
"""

from origami.stability.series import (
    CORTAJARENA_2011_CTPRA_DSC,
    PHILLIPS_2012_CTPRA_DSC,
    CitedDeltaGRank,
    companion_delta_g_rows,
    delta_g_at_n,
    literature_table_path,
    load_named_series,
    rank_companion_delta_g,
)
from origami.stability.table import ThermalObservation, load_thermal_table

__all__ = [
    "CORTAJARENA_2011_CTPRA_DSC",
    "PHILLIPS_2012_CTPRA_DSC",
    "CitedDeltaGRank",
    "ThermalObservation",
    "companion_delta_g_rows",
    "delta_g_at_n",
    "literature_table_path",
    "load_named_series",
    "load_thermal_table",
    "rank_companion_delta_g",
]
