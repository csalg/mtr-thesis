from abc import ABC, abstractmethod


class IEstimatorWrapper(ABC):
    """
    Wrapper class for estimators. Abstracts the logic
    for transforming X into the right format and persisting /
    reloading the estimator to / from a file.
    """

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def predict(self, X):
        """
        Loads estimator from saved model, scales X, splits if required.

        Input: X, with delta in the first column, assumed to not be scaled.
        Output: y_pred, a vector of predicted values for the recall score.
        """
        pass

    @abstractmethod
    def fit(self, X, y):
        """
        Scales dataset and persists scaler.
        Pre-processes X.
        Fits model to X and y.
        Persists model.
        """
        pass
