from abc import ABC, abstractmethod
from dataclasses import dataclass
import statistics

import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, balanced_accuracy_score
from sklearn.preprocessing import MinMaxScaler
from sigfig import round


class IEvaluation(ABC):

    @classmethod
    @abstractmethod
    def from_CV(cls, estimator_name, y_true, y_pred, **args):
        pass

    @abstractmethod
    def to_latex_tabular_row(self):
        pass


@dataclass
class LombEvaluation(IEvaluation):
    estimator_name: str
    mae: tuple
    mse: tuple
    wmse_tau: tuple
    wmse_tau_delta: tuple
    wmse_delta: tuple
    classification_report: str

    @classmethod
    def from_CV(cls, estimator_name, y_trues, y_preds, y_previous=None, deltas=None):
        def confidence_interval(metric, *args):
            vals = [metric(*args_) for args_ in zip(y_trues, y_preds, *args)]
            return statistics.mean(vals), 1.96 * statistics.stdev(vals)

        return cls(
            estimator_name=estimator_name,
            mae=confidence_interval(mean_absolute_error),
            mse=confidence_interval(mean_squared_error),
            wmse_tau=confidence_interval(wmse_tau, y_previous),
            wmse_tau_delta=confidence_interval(wmse_tau_delta, y_previous, deltas),
            wmse_delta=confidence_interval(wmse_delta, deltas),
            classification_report=""
        )

    def to_latex_tabular_row(self):
        return f"{self.estimator_name} & {_format_metric_value(self.mse, just_mean=True)} & {_format_metric_value(self.wmse_tau)} & {_format_metric_value(self.wmse_tau_delta)} \\\\"


@dataclass
class DuolingoEvaluation(IEvaluation):
    estimator_name: str
    dataset: str
    mae: tuple
    mmae: tuple
    weighted_binary_accuracy: tuple

    @classmethod
    def from_CV(cls, estimator_name, y_trues, y_preds, dataset='unknown'):
        def confidence_interval(metric, *args):
            vals = [metric(*args_, *args) for args_ in zip(y_trues, y_preds)]
            return statistics.mean(vals), 1.96 * statistics.stdev(vals)

        return cls(
            estimator_name=estimator_name,
            dataset=dataset,
            mae=confidence_interval(mean_absolute_error),
            mmae=confidence_interval(mean_absolute_error_y_less_than, 0.5),
            weighted_binary_accuracy=confidence_interval(balanced_accuracy_score_from_float),
        )

    def to_latex_tabular_row(self):
        def format(mean_confidence_interval, just_mean=False):
            mean, confidence_interval = mean_confidence_interval[0], mean_confidence_interval[1]
            if just_mean:
                return f"{round(np.format_float_positional(mean, 7, trim='k'), 3)}"
            return f"{round(np.format_float_positional(mean, 7, trim='k'), 3)} $\pm$ {round(np.format_float_positional(confidence_interval, 7, trim='k'), 2)}"

        subset_symbols = {
            'all': '$H ^\\frown S ^\\frown \Delta$',
            'only-delta': '$\Delta$',
            'only-history': '$H$',
            'only-session': '$S$',
            'without-delta': '$H ^\\frown S$',
        }

        return f"{self.estimator_name} & { subset_symbols[self.dataset] } & {format(self.mae, just_mean=True)} & {format(self.mmae, just_mean=True)} & {format(self.weighted_binary_accuracy, just_mean=True)} \\\\"


def wmse(y_true, y_pred, w):
    product = np.multiply(w, np.abs(y_true - y_pred))
    product_squared = np.power(product, 2)
    return float(np.mean(product_squared))


def wmse_tau(y_true, y_pred, y_previous):
    tau = np.abs(y_previous - y_true)
    return wmse(y_true, y_pred, tau)


def wmse_tau_delta(y_true, y_pred, y_previous, delta):
    delta_scaled = _1D_scaler(delta)
    tau = np.abs(y_previous - y_true)
    return wmse(y_true, y_pred, np.multiply(tau, delta_scaled))


def wmse_delta(y_true, y_pred, delta):
    delta_scaled = _1D_scaler(delta)
    return wmse(y_true, y_pred, delta_scaled)


def masked_mse(y_true, y_pred, previous_recall_score):
    vals = []
    for i in range(0, 10):
        epsilon = float(i) / 10.
        mask = np.abs(y_true - previous_recall_score) > epsilon
        vals.append(mean_squared_error(y_true[mask], y_pred[mask]))
    return vals


def mean_absolute_error_y_less_than(y_true, y_pred, upper_bound):
    idx = y_true < upper_bound
    return mean_absolute_error(y_true[idx], y_pred[idx])


def balanced_accuracy_score_from_float(y_true, y_pred):
    return balanced_accuracy_score(y_true>0.5, y_pred>0.5)


def _1D_scaler(x):
    x = np.array(x).reshape((len(x), 1))
    x_scaled = MinMaxScaler().fit_transform(x)
    return x_scaled[:, 0].reshape(len(x))


def _format_metric_value(mean_confidence_interval, just_mean=False):
    mean, confidence_interval = mean_confidence_interval[0], mean_confidence_interval[1]
    if just_mean:
        return f"{round(np.format_float_positional(mean, 7, trim='k'), 3)}"
    return f"{round(np.format_float_positional(mean, 7, trim='k'), 3)} $\pm$ {round(np.format_float_positional(confidence_interval, 7, trim='k'), 2)}"

