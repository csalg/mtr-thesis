from abc import ABC, abstractmethod
from typing import Callable

import numpy as np
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.ensemble import BaggingRegressor
from sklearn.linear_model import LinearRegression, HuberRegressor, ElasticNetCV, RidgeCV, LassoCV
from sklearn.model_selection import GridSearchCV
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

from estimators.linear import LinearRegressionEstimator


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
        return "MTR-ESq"


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
        return "MTR-Exp"


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
        return "MTR-Hyp"


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
        return "MTR-HSq"


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
        return "MTR-SWP"


class MTRLinearRegression(LinearRegressionEstimator):

    def __init__(self,
                 estimator_filename="LinearRegressionMuEstimator.pkl",
                 memory_trace_functional_form: IMemoryTraceFunctionalForm = SimplifiedWickelgren,
                 estimator_to_wrap_constructor: Callable = LinearRegression,
                 only_delta=False,
                 include_delta=False
                 ):
        super(MTRLinearRegression, self).__init__(estimator_filename)
        self.memory_trace_functional_form = memory_trace_functional_form
        self.estimator_to_wrap_constructor = estimator_to_wrap_constructor
        self.only_delta = only_delta
        self.include_delta = include_delta

    def fit(self, X, retention_rate, **kwargs):
        mu = self.memory_trace_functional_form.calculate_mu(retention_rate, X['delta'])
        self.model = self.estimator_to_wrap_constructor()
        if self.only_delta:
            self.model.fit(X[['delta']], mu, **kwargs)
        elif self.include_delta:
            self.model.fit(X, mu, **kwargs)
        else:
            self.model.fit(X.drop(['delta', ], axis=1), mu, **kwargs)
        self._persist()

    def partial_fit(self, X, retention_rate):
        mu = self.memory_trace_functional_form.calculate_mu(retention_rate, X['delta'])
        self.model = self.estimator_to_wrap_constructor()
        self.model.partial_fit(X.drop(['delta'], axis=1), mu)
        self._persist()

    def predict(self, X, **kwargs):
        mu = self.predict_mu(X)
        delta = X['delta']
        return self.memory_trace_functional_form.calculate_retention_rate(mu, delta)

    def predict_mu(self, X):
        if self.only_delta:
            mu = self.model.predict(X[['delta']], )
        elif self.include_delta:
            mu = self.model.predict(X, )
        else:
            mu = self.model.predict(X.drop(['delta', ], axis=1), )
        return mu.reshape(len(mu))

    def get_name(self):
        return self.memory_trace_functional_form.get_name()

ExpMuEstimator = lambda: MTRLinearRegression(memory_trace_functional_form=Exponential)
ESqMuEstimator = lambda: MTRLinearRegression(memory_trace_functional_form=ExponentialSqrt)
HypMuEstimator = lambda: MTRLinearRegression(memory_trace_functional_form=Hyperbolic)
HSqMuEstimator = lambda: MTRLinearRegression(memory_trace_functional_form=HyperbolicSqrt)
SWPMuEstimator = lambda: MTRLinearRegression(memory_trace_functional_form=SimplifiedWickelgren)
HLRMuEstimator = lambda: MTRLinearRegression(memory_trace_functional_form=HLR)
HLRWithDeltaMuEstimator = lambda: MTRLinearRegression(memory_trace_functional_form=HLR, include_delta=True)

all_estimators = [
    HLRMuEstimator,
    HLRWithDeltaMuEstimator,
    ExpMuEstimator,
    ESqMuEstimator,
    HypMuEstimator,
    HSqMuEstimator,
    SWPMuEstimator
]

class HLRForDuolingo(MTRLinearRegression):
    def __init__(self):
        super().__init__(memory_trace_functional_form=HLR)

    def fit(self, X, retention_rate, delta=None, **kwargs):
        mu = self.memory_trace_functional_form.calculate_mu(retention_rate, delta)
        self.model = self.estimator_to_wrap_constructor()
        self.model.fit(X, mu, **kwargs)
        self._persist()

    def predict(self, X, delta=None, **kwargs):
        mu = self.predict_mu(X)
        return self.memory_trace_functional_form.calculate_retention_rate(mu, delta)

    def predict_mu(self, X):
        mu = self.model.predict(X, )
        return mu.reshape(len(mu))
