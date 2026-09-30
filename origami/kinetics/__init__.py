"""Stage-1 scaffold kinetics (recruitment + locking).

Literature Spy k_on emulates a fusion path. Lab k_rev/k_bond stay vacant.
"""

from origami.kinetics.schema import kinetics_schema
from origami.kinetics.simulate import simulate_kinetics

__all__ = ["kinetics_schema", "simulate_kinetics"]
