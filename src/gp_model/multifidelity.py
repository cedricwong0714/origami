"""Two-fidelity (dry=0, wet=1) Gaussian process with a Matern-5/2 ARD kernel.

Equations (approved by the team, 2026-10-02):

    K((x,f),(x',f')) = B[f,f'] * k(x,x') + delta_{ff'} * noise_f^2
    B = [[s_dry^2,            rho*s_dry*s_wet],
         [rho*s_dry*s_wet,    s_wet^2        ]]
    k(x,x') = (1 + sqrt5*d + 5*d^2/3) * exp(-sqrt5*d),
    d = sqrt(sum_j ((x_j - x'_j)/l_j)^2)

``k`` has unit amplitude; the amplitude lives in B. One model is fitted per
wet output (luminescence, locking, expression, solubility, purity); this is
the "separate GPs per output" option, not a multi-task covariance.

Hyperparameter bounds are PRIOR CHOICES with no empirical source:
sigma in (0.1, 10), rho in (0.3, 0.95), length scales in (0.01, 10) on
normalised features, wet noise in (0.05, 2.0).
sigma_noise_dry is a fixed PRIOR CHOICE (0.1, standardised units): dry data
have no replicates, so it is not learned.
Wet noise is learned unless per-point wet noise is supplied (e.g. from CVs).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize

SIGMA_BOUNDS = (0.1, 10.0)  # prior choice
RHO_BOUNDS = (0.3, 0.95)  # prior choice
ELL_BOUNDS = (0.01, 10.0)  # prior choice, normalised features
WET_NOISE_BOUNDS = (0.05, 2.0)  # prior choice, standardised units
SIGMA_NOISE_DRY = 0.1  # fixed prior choice (no replicates to estimate)
MIN_WET_POINTS_WARN = 3
_JITTER = 1e-8


def matern52_ard(A: np.ndarray, B: np.ndarray, ell: np.ndarray) -> np.ndarray:
    """Unit-amplitude Matern-5/2 kernel with per-feature length scales."""
    A = np.atleast_2d(A) / ell
    B = np.atleast_2d(B) / ell
    d2 = (
        np.sum(A**2, axis=1)[:, None]
        + np.sum(B**2, axis=1)[None, :]
        - 2.0 * A @ B.T
    )
    d = np.sqrt(np.maximum(d2, 0.0))
    s5d = np.sqrt(5.0) * d
    return (1.0 + s5d + 5.0 * d2 / 3.0) * np.exp(-s5d)


def coregionalization(sigma_dry: float, sigma_wet: float, rho: float) -> np.ndarray:
    """The 2x2 matrix B."""
    c = rho * sigma_dry * sigma_wet
    return np.array([[sigma_dry**2, c], [c, sigma_wet**2]])


@dataclass
class Prediction:
    mean: np.ndarray
    std: np.ndarray
    fidelity: int
    includes_observation_noise: bool


class MultiFidelityGP:
    """Fit/predict for one output. Features should be normalised."""

    def __init__(self, n_restarts: int = 5, seed: int = 0):
        self.n_restarts = n_restarts
        self.seed = seed
        self.fitted = False

    def _noise_diag(self, f: np.ndarray, wet_noise: float) -> np.ndarray:
        wet = self._wet_noise_points
        n = np.where(f == 0, SIGMA_NOISE_DRY, wet_noise) ** 2
        if wet is not None:
            n = np.where(f == 0, SIGMA_NOISE_DRY**2, wet**2)
        return n

    def _K(self, theta: np.ndarray, X: np.ndarray, f: np.ndarray) -> np.ndarray:
        s_dry, s_wet, rho, wet_noise = theta[0], theta[1], theta[2], theta[3]
        ell = theta[4:]
        Bm = coregionalization(s_dry, s_wet, rho)
        K = Bm[np.ix_(f, f)] * matern52_ard(X, X, ell)
        return K + np.diag(self._noise_diag(f, wet_noise) + _JITTER)

    def _nlml(self, theta: np.ndarray) -> float:
        try:
            K = self._K(theta, self._X, self._f)
            c = cho_factor(K, lower=True)
        except np.linalg.LinAlgError:
            return 1e10
        alpha = cho_solve(c, self._y)
        return float(
            0.5 * self._y @ alpha
            + np.sum(np.log(np.diag(c[0])))
            + 0.5 * len(self._y) * np.log(2 * np.pi)
        )

    def fit(
        self,
        X: np.ndarray,
        fidelity: np.ndarray,
        y: np.ndarray,
        wet_noise_sd: np.ndarray | None = None,
    ) -> "MultiFidelityGP":
        """``wet_noise_sd`` (per point, in y units) overrides learned wet noise."""
        X = np.atleast_2d(np.asarray(X, dtype=float))
        f = np.asarray(fidelity, dtype=int)
        y = np.asarray(y, dtype=float)
        if not set(np.unique(f)) <= {0, 1}:
            raise ValueError("fidelity must be 0 (dry) or 1 (wet)")
        if len(X) != len(f) or len(X) != len(y):
            raise ValueError("X, fidelity and y must have equal length")
        if int(np.sum(f == 1)) < MIN_WET_POINTS_WARN:
            warnings.warn(
                f"Only {int(np.sum(f == 1))} wet points; wet-fidelity "
                "predictions are dominated by dry data and the prior.",
                UserWarning,
                stacklevel=2,
            )
        self._ymean = float(np.mean(y))
        self._ysd = float(np.std(y)) or 1.0
        self._y = (y - self._ymean) / self._ysd
        self._X, self._f = X, f
        self._wet_noise_points = (
            None if wet_noise_sd is None else np.asarray(wet_noise_sd, float) / self._ysd
        )
        D = X.shape[1]
        bounds = [SIGMA_BOUNDS, SIGMA_BOUNDS, RHO_BOUNDS, WET_NOISE_BOUNDS] + [
            ELL_BOUNDS
        ] * D
        lo = np.array([b[0] for b in bounds])
        hi = np.array([b[1] for b in bounds])
        rng = np.random.default_rng(self.seed)
        starts = [np.array([1.0, 1.0, 0.7, 0.3] + [1.0] * D)]
        for _ in range(self.n_restarts - 1):
            starts.append(np.exp(rng.uniform(np.log(lo), np.log(hi))))
        best = None
        for s in starts:
            r = minimize(self._nlml, np.clip(s, lo, hi), method="L-BFGS-B", bounds=bounds)
            if best is None or r.fun < best.fun:
                best = r
        self.theta = best.x
        self.nlml = float(best.fun)
        K = self._K(self.theta, X, f)
        self._chol = cho_factor(K, lower=True)
        self._alpha = cho_solve(self._chol, self._y)
        self.fitted = True
        return self

    @property
    def hyperparameters(self) -> dict:
        t = self.theta
        return {
            "sigma_dry": t[0],
            "sigma_wet": t[1],
            "rho": t[2],
            "sigma_noise_wet": t[3],
            "sigma_noise_dry_fixed": SIGMA_NOISE_DRY,
            "length_scales": list(t[4:]),
            "status": "prior_choice_bounds",
        }

    def predict(
        self, Xs: np.ndarray, fidelity: int = 1, include_noise: bool = False
    ) -> Prediction:
        """Posterior mean/std at the requested fidelity, in original y units."""
        if not self.fitted:
            raise RuntimeError("fit() first")
        Xs = np.atleast_2d(np.asarray(Xs, dtype=float))
        t = self.theta
        Bm = coregionalization(t[0], t[1], t[2])
        ell = t[4:]
        fs = np.full(len(Xs), int(fidelity))
        Ks = Bm[np.ix_(fs, self._f)] * matern52_ard(Xs, self._X, ell)
        mean = Ks @ self._alpha
        v = cho_solve(self._chol, Ks.T)
        var = Bm[fidelity, fidelity] - np.sum(Ks * v.T, axis=1)
        if include_noise:
            var = var + (t[3] if fidelity == 1 else SIGMA_NOISE_DRY) ** 2
        std = np.sqrt(np.maximum(var, 0.0))
        return Prediction(
            mean=mean * self._ysd + self._ymean,
            std=std * self._ysd,
            fidelity=int(fidelity),
            includes_observation_noise=include_noise,
        )
