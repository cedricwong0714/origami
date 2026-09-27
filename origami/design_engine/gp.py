"""Residual Gaussian process with Cholesky inference.

    y(x) = α S_physics(x) + β + r(x) + ε
    r ~ GP(0, k_θ)

This is not linear regression: posterior variance is state-dependent and the
kernel is Matérn-5/2. Hyperparameters are optionally fit by maximizing the
log marginal likelihood.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize

from origami.design_engine.kernels import matern52


_JITTER = 1e-9


@dataclass
class GPHyperparameters:
    lengthscale: float = 2.5
    variance: float = 1.0
    noise: float = 0.05


@dataclass
class GPPosterior:
    X: np.ndarray
    mean: np.ndarray
    variance: np.ndarray
    physics_mean: np.ndarray
    residual_mean: np.ndarray
    alpha: float
    beta: float
    interpolated: np.ndarray
    hyperparameters: GPHyperparameters

    @property
    def std(self) -> np.ndarray:
        return np.sqrt(np.maximum(self.variance, 0.0))

    def interval_95(self) -> tuple[np.ndarray, np.ndarray]:
        half = 1.96 * self.std
        return self.mean - half, self.mean + half


class ResidualGP:
    def __init__(self, hypers: GPHyperparameters | None = None) -> None:
        self.hypers = hypers or GPHyperparameters()
        self.X_train: np.ndarray | None = None
        self.r_train: np.ndarray | None = None
        self.alpha = 1.0
        self.beta = 0.0
        self._factor = None
        self.fitted = False

    def _kernel(self, A: np.ndarray, B: np.ndarray, hypers: GPHyperparameters) -> np.ndarray:
        return matern52(A, B, hypers.lengthscale, hypers.variance)

    def _affine(self, S: np.ndarray, y: np.ndarray) -> tuple[float, float]:
        S = np.asarray(S, dtype=float).ravel()
        y = np.asarray(y, dtype=float).ravel()
        if S.size == 0:
            return 1.0, 0.0
        if S.size == 1:
            return 1.0, float(y[0] - S[0])
        A = np.column_stack([S, np.ones_like(S)])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        return float(coef[0]), float(coef[1])

    def _nll(self, params: np.ndarray, X: np.ndarray, r: np.ndarray) -> float:
        ls, var, noise = np.exp(params)
        hypers = GPHyperparameters(lengthscale=ls, variance=var, noise=noise)
        K = self._kernel(X, X, hypers) + (noise**2 + _JITTER) * np.eye(len(X))
        try:
            factor = cho_factor(K, lower=True, check_finite=False)
        except np.linalg.LinAlgError:
            return 1e12
        alpha = cho_solve(factor, r, check_finite=False)
        logdet = 2.0 * np.sum(np.log(np.diag(factor[0])))
        n = len(r)
        return 0.5 * float(r @ alpha + logdet + n * np.log(2.0 * np.pi))

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        S_physics: np.ndarray,
        optimize: bool = True,
    ) -> "ResidualGP":
        X = np.atleast_2d(np.asarray(X, dtype=float))
        y = np.asarray(y, dtype=float).ravel()
        S = np.asarray(S_physics, dtype=float).ravel()
        if X.shape[0] != y.size or y.size != S.size:
            raise ValueError("X, y, and physics mean must align")
        self.alpha, self.beta = self._affine(S, y)
        r = y - (self.alpha * S + self.beta)
        hypers = self.hypers
        if optimize and X.shape[0] >= 3:
            x0 = np.log(
                [
                    max(self.hypers.lengthscale, 1e-3),
                    max(self.hypers.variance, 1e-3),
                    max(self.hypers.noise, 1e-4),
                ]
            )
            bounds = [(np.log(0.3), np.log(20.0)), (np.log(1e-3), np.log(50.0)), (np.log(1e-4), np.log(2.0))]
            result = minimize(self._nll, x0, args=(X, r), method="L-BFGS-B", bounds=bounds)
            if result.success:
                ls, var, noise = np.exp(result.x)
                hypers = GPHyperparameters(lengthscale=float(ls), variance=float(var), noise=float(noise))
        K = self._kernel(X, X, hypers) + (hypers.noise**2 + _JITTER) * np.eye(len(X))
        self._factor = cho_factor(K, lower=True, check_finite=False)
        self.X_train = X
        self.r_train = r
        self.hypers = hypers
        self.fitted = True
        return self

    def predict(self, X_star: np.ndarray, S_physics_star: np.ndarray) -> GPPosterior:
        X_star = np.atleast_2d(np.asarray(X_star, dtype=float))
        S_star = np.asarray(S_physics_star, dtype=float).ravel()
        physics_mean = self.alpha * S_star + self.beta
        if not self.fitted or self.X_train is None or self.X_train.shape[0] == 0:
            var = np.full(X_star.shape[0], self.hypers.variance + self.hypers.noise**2)
            return GPPosterior(
                X=X_star,
                mean=physics_mean,
                variance=var,
                physics_mean=physics_mean,
                residual_mean=np.zeros_like(physics_mean),
                alpha=self.alpha,
                beta=self.beta,
                interpolated=np.zeros(X_star.shape[0], dtype=bool),
                hyperparameters=self.hypers,
            )
        K_ss = self._kernel(X_star, X_star, self.hypers)
        K_s = self._kernel(self.X_train, X_star, self.hypers)
        residual_mean = cho_solve(self._factor, K_s, check_finite=False).T @ self.r_train
        v = cho_solve(self._factor, K_s, check_finite=False)
        var = np.diag(K_ss) - np.sum(K_s * v, axis=0) + self.hypers.noise**2
        var = np.maximum(var, 1e-12)
        mean = physics_mean + residual_mean
        # interpolated if nearest training input is within one lengthscale
        dmin = np.min(
            np.linalg.norm(X_star[:, None, :] - self.X_train[None, :, :], axis=2),
            axis=1,
        )
        interpolated = dmin <= self.hypers.lengthscale
        return GPPosterior(
            X=X_star,
            mean=mean,
            variance=var,
            physics_mean=physics_mean,
            residual_mean=residual_mean,
            alpha=self.alpha,
            beta=self.beta,
            interpolated=interpolated,
            hyperparameters=self.hypers,
        )
