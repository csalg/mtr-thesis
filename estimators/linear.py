from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
import pickle
import os

from estimators.IEstimatorWrapper import IEstimatorWrapper


class LinearRegressionEstimator(IEstimatorWrapper):

    def __init__(self, estimator_filename="LinearRegressionEstimator.pkl", **kwargs):
        super().__init__(**kwargs)
        self.estimator_filename = estimator_filename
        self.model = None
        self.scaler = None

    def fit(self, X, y, **kwargs):
        X_scaled = self._scaler_fit_transform(X)
        self.model = LinearRegression()
        self.model.fit(X_scaled, y)
        self._persist()

    def predict(self, X, **kwargs):
        self._load()
        X_scaled = self._scaler_transform(X)
        return self.model.predict(X_scaled, )

    def _scaler_fit_transform(self, X):
        self.scaler = MinMaxScaler()
        self.scaler.fit(X)
        return self.scaler.transform(X)

    def _scaler_transform(self, X):
        return self.scaler.transform(X)

    def _persist(self):
        with open('saved_models/' + self.estimator_filename, 'wb') as file:
            pickle.dump((self.model, self.scaler), file)

    def _load(self):
        if os.path.exists('saved_models/' + self.estimator_filename):
            with open('saved_models/' + self.estimator_filename, 'rb') as file:
                self.model, self.scaler = pickle.load(file)

    def get_name(self):
        return "Linear Regression"


class LogisticRegressionEstimator(LinearRegressionEstimator):

    def __init__(self,
                 estimator_filename="LogisticRegressionEstimator.pkl"):
        super(LogisticRegressionEstimator, self).__init__(estimator_filename)

    def fit(self, X, y, **kwargs):
        # X_scaled = self._scaler_fit_transform(X)
        self.model = Pipeline([
            ('scale', MinMaxScaler()),
            ('estimator', LogisticRegression(class_weight='balanced'))
        ])
        self.model.fit(X, y > 0.5)
        self._persist()

    def predict(self, X, **kwargs):
        # self._load()
        # X_scaled = self._scaler_transform(X)
        return self.model.predict_proba(X)[:, 1]

    def get_name(self):
        return "Logistic Regression"

all_estimators = [
    LinearRegressionEstimator,
    LogisticRegressionEstimator
]