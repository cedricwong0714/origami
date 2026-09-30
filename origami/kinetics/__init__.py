"""Stage-1 scaffold kinetics (recruitment + locking).

Lab-measured SpyTag rates stay vacant until stage-1 ingestion.
Literature Kd drives steady-state recruitment only.
"""

from origami.kinetics.schema import kinetics_schema
from origami.kinetics.simulate import simulate_kinetics

__all__ = ["kinetics_schema", "simulate_kinetics"]
