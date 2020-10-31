import math
from copy import copy
from functools import partial
from abc import ABC, abstractmethod

from enforce_typing import enforce_types

from wrangling.Datapoint import Datapoint
from wrangling.domain import is_click, is_recall, calculate_recall_score, Log, CoreLog


class IDatapointBuilder(ABC):

    def __init__(self, id):
        self._id = id
        self._logs = []

    @classmethod
    @enforce_types
    def from_log(cls, log: Log):
        """
        Static factory method using a log.
        Input: log
        Output: DatapointBuilder instance
        """
        self = cls(log.id())
        self.add_log(log)
        return self

    @enforce_types
    def add_log(self, log: Log):
        """
        Just adds a log.
        Input: log
        Output: None
        """
        assert log.id() == self._id
        self._logs.append(CoreLog(log.timestamp, log.message))


    @abstractmethod
    def view_all_data_sequence(self, **kwargs):
        pass


    @abstractmethod
    def view_all_data_sequence_for_plotting(self,
                                            interval_between_points=1000,
                                            add_time_after_last_timestamp=0,
                                            return_timesteps=True):
        pass

    def __len__(self):
        return len(self._logs)

class DatapointBuilder(IDatapointBuilder):
    """
    AggregatedDatapointBuilder calculates the recall score for
    intervals of length T and creates one datapoint per interval.
    """

    def view_all_data_sequence_for_plotting(self,
                                            interval_between_points=12*60*60,
                                            add_time_after_last_timestamp=1*24*60*60,
                                            return_timesteps=True):
        datapoints_for_prediction, _ = self.infer_retention_rate()
        datapoints_for_prediction = list(filter(lambda x : x is not None, datapoints_for_prediction))
        datapoints_for_prediction.sort(key=lambda datapoint_dict : datapoint_dict['FIRST_EXPOSURE_seconds'])

        current_timestamp = datapoints_for_prediction[0]['FIRST_EXPOSURE_seconds']
        last_timestamp    = datapoints_for_prediction[-1]['FIRST_EXPOSURE_seconds'] + add_time_after_last_timestamp
        next_datapoint_index = 1
        datapoints = []
        while current_timestamp <= last_timestamp+add_time_after_last_timestamp:
            # Increase the datapoint index?
            while next_datapoint_index != len(datapoints_for_prediction):
                next_datapoint_timestamp = datapoints_for_prediction[next_datapoint_index]['FIRST_EXPOSURE_seconds']
                if next_datapoint_timestamp >= current_timestamp:
                    break
                next_datapoint_index += 1
            # Copy the datapoint
            datapoint_at_current_timestamp = copy(datapoints_for_prediction[next_datapoint_index-1])
            # Increase seconds by delta
            delta = current_timestamp - datapoint_at_current_timestamp['FIRST_EXPOSURE_seconds']
            datapoint_at_current_timestamp['delta'] = delta
            # Append datapoint at current timestamp
            datapoints.append(datapoint_at_current_timestamp)
            # Increase current timestamp
            current_timestamp += interval_between_points

        self.__clean_up_useless_fields(datapoints)
        return datapoints


    def view_all_data_sequence(self, sample_period=24 * 60 * 60, alpha=0.5):
        datapoints, inferred_retention_rates = self.infer_retention_rate(sample_period,alpha)

        for datapoint, inferred_retention_rate in zip(datapoints, inferred_retention_rates):
            if datapoint is not None:
                datapoint['inferred_retention_rate'] = inferred_retention_rate

        datapoints_for_prediction = self.__datapoints_to_prediction_problem(datapoints)
        self.__clean_up_useless_fields(datapoints_for_prediction)
        for datapoint in datapoints_for_prediction:
            datapoint['FIRST_EXPOSURE_seconds'] += datapoint['delta']
        return datapoints_for_prediction

    def infer_retention_rate(self, sample_period=24 * 60 * 60, alpha=0.6):
        """
        Infers retention rate from the events by:
        1. Aggregating events into intervals of length `sample_period`
        and calculating interval retention scores.
        2. Linearly interpolating the recall scores where data is missing
        3. Smoothing by bi-directional Exponential Moving Average with parameter
        `alpha`.

        Input: sample_period, alpha
        Output:
        """
        logs = copy(self._logs)
        logs.sort(key=lambda log: log.timestamp)
        # Subtract first timestamp
        first_timestamp = logs[0].timestamp
        for log in logs:
            log.timestamp -= first_timestamp

        datapoints = self.__aggregate_logs_into_timesteps(logs, sample_period)
        recall_scores = list(map(lambda datapoint: datapoint['recall_score'] if datapoint else None, datapoints))

        # Approximate p:
        # 1. Interpolate missing values
        consecutive_nones = self.__find_consecutive_nones(recall_scores)
        for pair in consecutive_nones:
            self.__interpolate_scores_between_range(recall_scores, *pair)

        # 2. Perform forward and backward exponential moving average
        ema = exponential_moving_average(recall_scores, alpha)
        ema = exponential_moving_average(ema, alpha, reverse=True)

        return datapoints,ema

    def __find_consecutive_nones(self, scores):
        consecutive_nones = []
        i = j = 0
        for k in range(0, len(scores)):
            if scores[k] != None:
                if i != j:
                    consecutive_nones.append((i + 1, j))
                i = j = k
            j = k
        if i != j:
            consecutive_nones.append((i + 1, j))
        return consecutive_nones

    def __interpolate_scores_between_range(self, scores, index_start, index_end):

        if index_end + 1 >= len(scores):
            for x in range(index_start, index_end + 1):
                scores[x] = scores[index_start - 1]
            return

        if scores[0] is None:
            scores[0] = 0.0

        y_0 = scores[index_start - 1]
        x_0 = index_start - 1
        y_1 = scores[index_end + 1]
        x_1 = index_end + 1

        interpolate = partial(linear_interpolation, x_0, y_0, x_1, y_1)
        for x in range(index_start, index_end + 1):
            y = interpolate(x)
            scores[x] = y

        return scores

    def __aggregate_logs_into_timesteps(self, logs, sample_period):
        last_timestamp = logs[-1].timestamp
        datapoints = []
        next_timestamp = sample_period
        i = 0
        datapoint = Datapoint()
        while next_timestamp < last_timestamp + sample_period:
            recalls = 0
            clicks = 0
            while i != len(logs):
                log = logs[i]
                if log.timestamp < next_timestamp:
                    datapoint.update_from_log_counting_text_interactions_as_clicks(log)
                    clicks += is_click(log.message)
                    recalls += is_recall(log.message)
                    i += 1
                    continue
                break
            if recalls or clicks:
                datapoint_dict = datapoint.view_all_data()
                datapoint_dict['recall_score'] = calculate_recall_score(recalls, clicks)
                datapoint_dict['period_start'] = next_timestamp - sample_period
                datapoint_dict['period_end'] = next_timestamp
                datapoints.append(datapoint_dict)
            else:
                datapoints.append(None)
            next_timestamp += sample_period
        return datapoints

    def __datapoints_to_prediction_problem(self, datapoints):
        datapoints_for_prediction = []
        for i, datapoint in enumerate(datapoints):
            datapoint = copy(datapoint)
            if datapoint is None:
                continue
            # Find successor
            j = i + 1
            if j == len(datapoints):
                break
            while datapoints[j] is None:
                j += 1
                if j == len(datapoints):
                    break
            if j == len(datapoints):
                # Not found
                break
            successor = datapoints[j]
            datapoint['delta'] = successor['period_end'] - datapoint['period_end']
            datapoint['previous_recall_score'] = datapoint['recall_score']
            recall_score = successor['recall_score']
            datapoint['recall_score'] = recall_score
            recall_score_clipped = max(0.25, min(0.75, recall_score))
            datapoint['mu'] = (-1 *math.sqrt(datapoint['delta'])) / math.log(recall_score_clipped)
            datapoints_for_prediction.append(datapoint)

        return datapoints_for_prediction

    def __clean_up_useless_fields(self, datapoints_for_prediction):
        for datapoint in datapoints_for_prediction:
            for key_name in [
                "period_start",
                "period_end",
                'CLICKED',
                'recall_score',
                'mu'
            ]:
                try:
                    datapoint.pop(key_name)
                except:
                    pass


def linear_interpolation(x_0, y_0, x_1, y_1, x):
    return y_0 * (1 - (x - x_0) / (x_1 - x_0)) \
           + y_1 * ((x - x_0) / (x_1 - x_0))


def exponential_moving_average(scores, alpha, reverse=False):
    averages = [scores[-1 if reverse else 0] for i in range(len(scores))]
    if reverse:
        for i in range(len(scores) - 2, 0, -1):
            averages[i] = (1 - alpha) * scores[i] + alpha * averages[i + 1]
    else:
        for i in range(1, len(scores), 1):
            averages[i] = (1 - alpha) * scores[i] + alpha * averages[i - 1]
    return averages
