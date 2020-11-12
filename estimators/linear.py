from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler

from estimators.IEstimatorWrapper import IEstimatorWrapper


class LogisticRegressionEstimator(IEstimatorWrapper):

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.model = None

    def fit(self, X, y, delta, **kwargs):
        self.model = Pipeline([
            ('scale', MinMaxScaler()),
            ('estimator', LogisticRegression(class_weight='balanced', max_iter=1000))
        ])
        self.model.fit(X, y > 0.5)

    def predict(self, X, delta, **kwargs):
        return self.model.predict_proba(X)[:, 1]

    def get_name(self):
        return "Logistic Regression"


class LinearRegressionEstimator(IEstimatorWrapper):

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.model = None

    def fit(self, X, y, delta, **kwargs):
        self.model = Pipeline([
            ('scale', MinMaxScaler()),
            ('estimator', LinearRegression())
        ])
        self.model.fit(X, y)

    def predict(self, X, delta, **kwargs):
        return self.model.predict(X)

    def get_name(self):
        return "Linear Regression"

all_estimators = [
    LinearRegressionEstimator,
    LogisticRegressionEstimator
]