"""Sequence feature extraction: ESM-2 preferred, one-hot / composition fallback.

SEQUENCE_ENCODING: esm2 preferred; onehot/composition as fallback.
ESM-2 needs torch + transformers, which are NOT project dependencies. If they
are missing, ``encode_sequence`` warns and returns the one-hot fallback; the
method actually used is always returned so it can be recorded.
"""

from __future__ import annotations

import warnings

import numpy as np

AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
ESM2_MODEL = "facebook/esm2_t6_8M_UR50D"
ONEHOT_MAX_LEN = 64


def _clean(seq: str) -> str:
    s = seq.strip().upper()
    bad = set(s) - set(AMINO_ACIDS)
    if bad or not s:
        raise ValueError(f"Invalid protein sequence; bad residues: {sorted(bad)}")
    return s


def composition_features(seq: str) -> np.ndarray:
    """Fraction of each of the 20 amino acids (length 20)."""
    s = _clean(seq)
    return np.array([s.count(a) / len(s) for a in AMINO_ACIDS])


def onehot_encoding(seq: str, max_len: int = ONEHOT_MAX_LEN) -> np.ndarray:
    """Mean-pooled one-hot over positions after truncation to ``max_len``.

    Pooling discards order; it is a composition of the truncated prefix.
    Length of the full sequence is appended so size is not lost.
    """
    s = _clean(seq)[:max_len]
    M = np.zeros((len(s), 20))
    for i, a in enumerate(s):
        M[i, AMINO_ACIDS.index(a)] = 1.0
    return np.append(M.mean(axis=0), len(seq.strip()) / 1000.0)


def esm2_embedding(seq: str) -> np.ndarray:
    """Mean-pooled last hidden state of ESM-2 (320-d for the 8M model)."""
    import torch  # noqa: PLC0415
    from transformers import AutoModel, AutoTokenizer  # noqa: PLC0415

    s = _clean(seq)
    tok = AutoTokenizer.from_pretrained(ESM2_MODEL)
    model = AutoModel.from_pretrained(ESM2_MODEL).eval()
    with torch.no_grad():
        out = model(**tok(s, return_tensors="pt"))
    return out.last_hidden_state[0, 1:-1].mean(dim=0).numpy()


def encode_sequence(seq: str, method: str = "esm2") -> tuple[np.ndarray, str]:
    """Return (features, method_actually_used)."""
    if method == "esm2":
        try:
            return esm2_embedding(seq), "esm2"
        except ImportError:
            warnings.warn(
                "ESM-2 unavailable (torch/transformers not installed); "
                "falling back to one-hot. Record method_used with the data.",
                UserWarning,
                stacklevel=2,
            )
            return onehot_encoding(seq), "onehot"
    if method == "onehot":
        return onehot_encoding(seq), "onehot"
    if method == "composition":
        return composition_features(seq), "composition"
    raise ValueError(f"Unknown method '{method}'")
