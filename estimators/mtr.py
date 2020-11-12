from abc import ABC, abstractmethod
from typing import Callable

import numpy as np
from sklearn.linear_model import LinearRegression, HuberRegressor, ElasticNetCV, RidgeCV, LassoCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler

from estimators.IEstimatorWrapper import IEstimatorWrapper


class IMemoryTraceFunctionalForm(ABC):
    """
    Infers mu from p and delta, and also delta from mu and p
    """

    @staticmethod
    @abstractmethod
    def calculate_mu(retention_rate, delta):
        pass

    @staticmethod
    @abstractmethod
    def calculate_retention_rate(mu, delta):
        pass

    @staticmethod
    @abstractmethod
    def get_name():
        pass


class ExponentialSqrt(IMemoryTraceFunctionalForm):

    @staticmethod
    def calculate_mu(retention_rate, delta):
        retention_rate_clipped = np.clip(retention_rate, 0.1, 0.9)
        return (-1 * np.sqrt(delta + 1)) / np.log(retention_rate_clipped)

    @staticmethod
    def calculate_retention_rate(mu, delta):
        exponent = -1 * np.sqrt(delta + 1) / mu
        return np.exp(exponent)

    @staticmethod
    def get_name():
        return "ESq"


class Exponential(IMemoryTraceFunctionalForm):

    @staticmethod
    def calculate_mu(retention_rate, delta):
        retention_rate_clipped = np.clip(retention_rate, 0.1, 0.9)
        return (-1 * delta) / np.log(retention_rate_clipped)

    @staticmethod
    def calculate_retention_rate(mu, delta):
        exponent = -1 * delta / mu
        return np.exp(exponent)

    @staticmethod
    def get_name():
        return "Exp"


class Hyperbolic(IMemoryTraceFunctionalForm):

    @staticmethod
    def calculate_mu(retention_rate, delta):
        retention_rate_clipped = np.clip(retention_rate, 0.1, 0.9)
        return np.divide(np.multiply(delta, retention_rate), 1. - retention_rate_clipped)

    @staticmethod
    def calculate_retention_rate(mu, delta):
        return np.divide(1., 1. + np.divide(delta, mu))

    @staticmethod
    def get_name():
        return "Hyp"


class HyperbolicSqrt(IMemoryTraceFunctionalForm):

    @staticmethod
    def calculate_mu(retention_rate, delta):
        retention_rate_clipped = np.clip(retention_rate, 0.1, 0.9)
        return np.divide(np.multiply(np.sqrt(delta), retention_rate), 1. - retention_rate_clipped)

    @staticmethod
    def calculate_retention_rate(mu, delta):
        return np.divide(1., 1. + np.divide(np.sqrt(delta), mu))

    @staticmethod
    def get_name():
        return "HSq"


class HLR(IMemoryTraceFunctionalForm):

    @staticmethod
    def calculate_mu(retention_rate, delta):
        retention_rate_clipped = np.clip(retention_rate, 0.001, 0.999)
        term = (-1 * delta) / np.log2(retention_rate_clipped)
        return np.log2(term)

    @staticmethod
    def calculate_retention_rate(mu, delta):
        exponent = np.divide(-1 * delta, np.power(2., mu))
        return np.power(2., exponent)

    @staticmethod
    def get_name():
        return "HLR"


class SimplifiedWickelgren(IMemoryTraceFunctionalForm):

    @staticmethod
    def calculate_mu(retention_rate, delta):
        delta_ = delta / (24 * 60 * 60)
        retention_rate_clipped = np.clip(retention_rate, 0.1, 0.9)
        return -1. * np.divide(np.log(1 + delta_), (np.log(retention_rate_clipped)))

    @staticmethod
    def calculate_retention_rate(mu, delta):
        delta_ = delta / (24 * 60 * 60)
        mu_clipped = np.clip(mu, 1e-10, 1e10)
        exponent = np.divide(-1., mu_clipped)
        return np.power(1. + delta_, exponent)

    @staticmethod
    def get_name():
        return "SWP"


class MTRLinearRegression(IEstimatorWrapper):

    def __init__(self,
                 memory_trace_functional_form: Callable[[], IMemoryTraceFunctionalForm] = SimplifiedWickelgren,
                 drop_delta_in_X=True,
                 **kwargs):
        super().__init__(**kwargs)
        self.memory_trace_functional_form  = memory_trace_functional_form
        self.drop_delta_in_X               = drop_delta_in_X

    def fit(self, X, y, delta, **kwargs):
        # Calculate mu
        mu = self.memory_trace_functional_form.calculate_mu(y, delta)

        assert np.isfinite(X).values.all()
        assert not np.isnan(X).values.all()
        assert np.isfinite(mu).values.all()
        assert not np.isnan(mu).values.all()

        # Fit model
        self.model = Pipeline([
            ('scale', MinMaxScaler()),
            ('estimator', LinearRegression())
        ])

        if self.drop_delta_in_X:
            self.model.fit(X.drop(['delta', ], axis=1), mu, **kwargs)
        else:
            self.model.fit(X, mu, **kwargs)

    def predict(self, X, delta, **kwargs):
        mu = self.predict_mu(X)
        return self.memory_trace_functional_form.calculate_retention_rate(mu, delta)

    def predict_mu(self, X):
        if self.drop_delta_in_X:
            mu = self.model.predict(X.drop(['delta', ], axis=1), )
        else:
            mu = self.model.predict(X)
        return mu.reshape(len(mu))

    def get_name(self):
        form_name = self.memory_trace_functional_form.get_name()
        if form_name == "HLR":
            return "HLR"
        return 'MTR-'+form_name

ExpMTREstimator = lambda: MTRLinearRegression(memory_trace_functional_form=Exponential)
ESqMTREstimator = lambda: MTRLinearRegression(memory_trace_functional_form=ExponentialSqrt)
HypMTREstimator = lambda: MTRLinearRegression(memory_trace_functional_form=Hyperbolic)
HSqMTREstimator = lambda: MTRLinearRegression(memory_trace_functional_form=HyperbolicSqrt)
SWPMTREstimator = lambda: MTRLinearRegression(memory_trace_functional_form=SimplifiedWickelgren)
HLRMTREstimator = lambda: MTRLinearRegression(memory_trace_functional_form=HLR)
HLRWithDeltaMTREstimator = lambda: MTRLinearRegression(memory_trace_functional_form=HLR, drop_delta_in_X=False)

all_estimators = [
    HLRMTREstimator,
    HLRWithDeltaMTREstimator,
    ExpMTREstimator,
    ESqMTREstimator,
    HypMTREstimator,
    HSqMTREstimator,
    SWPMTREstimator
]
