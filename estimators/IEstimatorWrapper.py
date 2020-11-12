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
    def predict(self, X, delta):
        """
        Input: X, delta. Assumed to not be scaled.
        Output: y_pred, a vector of predicted values for the recall score.
        """
        pass

    @abstractmethod
    def fit(self, X, y, delta):
        """
        Input: X, y, delta. Assumed to not be scaled.
        Output: None.
        Fits scalers and estimator to X, delta and y.
        """
        pass
