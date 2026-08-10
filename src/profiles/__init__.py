"""Mechanism profiles — one package per proximity-dependent function."""

from src.core.schema import MechanismType
from src.profiles.base import MechanismProfile, ProfilePrediction
from src.profiles.covalent_capture import CovalentCaptureProfile
from src.profiles.redox_transfer import RedoxTransferProfile
from src.profiles.target_complementation import TargetComplementationProfile
from src.profiles.trans_activation import TransActivationProfile
from src.profiles.protease_cleavage import ProteaseCleavageProfile
from src.profiles.trehalose_synthesis import TrehaloseSynthesisProfile

PROFILE_REGISTRY: dict[MechanismType, MechanismProfile] = {
    MechanismType.INTERMEDIATE_TRANSFER: TrehaloseSynthesisProfile(),
    MechanismType.TARGET_COMPLEMENTATION: TargetComplementationProfile(),
    MechanismType.REDOX_TRANSFER: RedoxTransferProfile(),
    MechanismType.COVALENT_CAPTURE: CovalentCaptureProfile(),
    MechanismType.TRANS_ACTIVATION: TransActivationProfile(),
    MechanismType.PROTEASE_CLEAVAGE: ProteaseCleavageProfile(),
}


def get_profile(mechanism_type: MechanismType) -> MechanismProfile:
    try:
        return PROFILE_REGISTRY[mechanism_type]
    except KeyError as exc:
        raise ValueError(f"No mechanism profile registered for {mechanism_type}") from exc


__all__ = [
    "MechanismProfile",
    "ProfilePrediction",
    "TrehaloseSynthesisProfile",
    "TargetComplementationProfile",
    "RedoxTransferProfile",
    "CovalentCaptureProfile",
    "TransActivationProfile",
    "ProteaseCleavageProfile",
    "PROFILE_REGISTRY",
    "get_profile",
]
