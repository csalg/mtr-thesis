from __future__ import annotations

import statistics
from collections import defaultdict
from typing import List, Dict, Callable

import pandas

from config import OUTLIERS_COEFFICIENT
from wrangling.DatapointBuilder import DatapointBuilder, IDatapointBuilder
from wrangling.domain import Log

class DatasetFactory:
    def __init__(self, builder_constructor = DatapointBuilder):
        self.__logs : List[Log] = []
        self.cache = {}
        self.builder_constructor = builder_constructor

    def add_logs(self, logs : List[dict], users=None):
        for log in logs:
            should_add = users == None
            if users != None:
                should_add = log['user'] in users
            if should_add:
                try:
                    log = Log.from_dictionary(log)
                    self.__logs.append(log)
                except:
                    pass

    def create_dataframe_with_all_data_flattened(self) -> pandas.DataFrame:
        return self.__create_dataframe_flattened( lambda builder : builder.view_all_data_flattened())

    def create_dataframe_with_only_reading_data_flattened(self) -> pandas.DataFrame:
        return self.__create_dataframe_flattened( lambda builder : builder.view_reading_data_flattened())

    def create_dataframe_with_only_revision_data_flattened(self) -> pandas.DataFrame:
        return self.__create_dataframe_flattened( lambda builder : builder.view_revision_data_flattened())

    def create_dataframe_with_all_data_sequence(self) -> pandas.DataFrame:
        return self.__create_dataframe_sequence( lambda builder : builder.view_all_data_sequence())

    def create_dataframe_with_all_data_sequence_counting_text_interactions_as_clicks(self) -> pandas.DataFrame:
        return self.__create_dataframe_sequence( lambda builder : builder.view_all_data_sequence_counting_text_interactions_as_clicks())

    def create_dataframe_for_self_learning(self) -> pandas.DataFrame:
        return self.__create_dataframe_sequence( lambda builder : builder.view_all_data_sequence_with_event_labels_counting_text_interactions_as_clicks() )

    def create_dataframe_with_only_reading_data_sequence(self) -> pandas.DataFrame:
        return self.__create_dataframe_sequence( lambda builder : builder.view_reading_data_sequence())

    def create_dataframe_with_only_revision_data_sequence(self) -> pandas.DataFrame:
        return self.__create_dataframe_sequence( lambda builder : builder.view_revision_data_sequence())

    def create_unlabeled_dataframe(self, interval_between_points=24*60*60) -> pandas.DataFrame:
        return self.__create_dataframe_sequence(
            lambda builder : builder.view_all_data_sequence_for_plotting(
                interval_between_points=interval_between_points,
                return_timesteps=False,
            )
            )

    def __create_dataframe_flattened(self, method_call :Callable[[DatapointBuilder], dict]):
        builders = self.__builders()
        data = []
        for builder in builders:
            try:
                data.append(method_call(builder))
            except:
                pass
        return pandas.DataFrame(data)


    def __create_dataframe_sequence(self, method_call :Callable[[DatapointBuilder], dict]):
        builders = self.__builders()
        data = []
        for builder in builders:
            try:
                data += method_call(builder)
            except:
                pass
        return pandas.DataFrame(data)

    def create_sequence_for_rnn(self):
        builders = self.__builders()
        data = []
        for builder in builders:
            try:
                # First, get the sequence
                sequence = builder.view_all_data_sequence()

                # Then, create subsequences
                subsequences = []
                for i,datapoint in enumerate(sequence):
                    if i == 0:
                        subsequences.append([datapoint,])
                        continue
                    subsequences.append(subsequences[i-1]+[datapoint,])

                # Extend the data array with the subsequences
                data += subsequences
            except:
                # Can throw an error if not enough data to build a datapoint,
                # but there is no need to handle.
                pass
            # Now we have to convert the data array into a 3rd order tensor.

        return data

    def __builders(self) -> List[DatapointBuilder]:
        builders = self.__make_builders()
        return self.__filter_outliers(builders)
    
    def __make_builders(self) -> List[IDatapointBuilder]:

        # Pre-conditions
        if len(self.__logs) <= 1:
            raise Exception("Need at least two logs to produce a datapoint!")

        builders : Dict[str, DatapointBuilder] = {}
        for log in self.__logs:
            if log.id() in builders:
                builders[log.id()].add_log(log)
            else:
                try:
                    builders[log.id()] = self.builder_constructor.from_log(log)
                except:
                    pass
        
        return list(builders.values())

    def create_sequence_of_messages_for_rnns(self):
        # Sort logs by timestamp
        logs_sorted = sorted(self.__logs, key=lambda log: log.timestamp)

        # Hashmap id to logs
        id_to_logs = defaultdict(list)
        for log in logs_sorted:
            id_to_logs[log.id()].append({
                'message': log.message,
                'timestamp': log.timestamp
            })
        log_sequences = self.__filter_outliers(list(id_to_logs.values()))

        # Subtract first timestamp to each sequence
        for log_sequence in log_sequences:
            first_timestamp = log_sequence[0]['timestamp']
            for log in log_sequence:
                log['timestamp'] -= first_timestamp

        return log_sequences

    def __filter_outliers(self, builders):
        # return builders
        if len(builders) == 1:
            return builders

        lengths = list(map(len, builders))
        mean    = statistics.mean(lengths)
        std_dev = statistics.stdev(lengths)
        lower_bound = mean - OUTLIERS_COEFFICIENT*std_dev
        upper_bound = mean + OUTLIERS_COEFFICIENT*std_dev
        return list(filter(lambda builder : lower_bound < len(builder) and len(builder) < upper_bound, builders))

