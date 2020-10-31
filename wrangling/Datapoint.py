"""
The serial module provides classes for turning log data into datapoints.
"""
from dataclasses import asdict

from config import NEVER
from wrangling.domain import *


class DictionaryViewWithEncapsulation:
    """
    Subclasses inherit a to_dict() method which does not serialize
    private or protected methods.
    """

    def to_dict(self):
        def dict_factory(data):
            return dict(filter(lambda x: x[0][0]!='_', data))
        return asdict(self, dict_factory=dict_factory)


@enforce_types
@dataclass
class CommonDatapointData(DictionaryViewWithEncapsulation):
    CLICKED: bool = True
    FIRST_EXPOSURE_seconds: int = NEVER
    # event : str = "UNKNOWN"
    __first_exposure_timestamp: int = 0
    __registered_a_click: int = False

    def update_from_log(self, log: CoreLog):
        message, timestamp = log.message, log.timestamp

        if self.__first_exposure_timestamp == 0:
            self.__first_exposure_timestamp = timestamp

        self.update_timestamp(timestamp)

        if message in [REVISION__CLICKED, REVISION__NOT_CLICKED]:
            self.__registered_a_click = True
            if message == REVISION__CLICKED:
                self.CLICKED = True
            if message == REVISION__NOT_CLICKED:
                self.CLICKED = False

        # self.event = message

    def update_from_log_counting_text_interactions_as_clicks(self, log: CoreLog):
        self.update_from_log(log)
        message  = log.message

        if message in [TEXT__WORD_HIGHLIGHTED, TEXT__SENTENCE_READ]:
            self.__registered_a_click = True
            if message == TEXT__WORD_HIGHLIGHTED:
                self.CLICKED = True
            if message == TEXT__SENTENCE_READ:
                self.CLICKED = False

    def update_timestamp(self, timestamp):
        self.FIRST_EXPOSURE_seconds = timestamp - self.__first_exposure_timestamp

    # def to_dict(self):
    #     if not self.__registered_a_click:
    #         raise Exception("Cannot serialize to dictionary. Have not registered a click yet.")
    #     return DictionaryViewWithEncapsulation.to_dict(self)


@enforce_types
@dataclass
class RevisionDatapointPartition(DictionaryViewWithEncapsulation):
    REVISION__CLICKED_amount : int = 0
    REVISION__NOT_CLICKED_amount : int = 0
    REVISION__ALL_amount : int = 0
    REVISION__CLICKED_seconds : int = NEVER
    REVISION__NOT_CLICKED_seconds : int = NEVER
    REVISION__ALL_seconds : int = NEVER
    REVISION_interval_ratio : float = 1
    REVISION_last_interval : int = NEVER
    REVISION_previous_interval : int = 0
    __REVISION__CLICKED_last_timestamp : int = 0
    __REVISION__NOT_CLICKED_last_timestamp : int = 0
    __REVISION_ALL_last_timestamp : int = 0
    __REVISION_previous_message : str = "UNKNOWN"

    def update_from_log(self, log: CoreLog):
        message, timestamp = log.message, log.timestamp

        # Base case: first log
        if self.__REVISION_ALL_last_timestamp == 0:
            self.__REVISION__CLICKED_last_timestamp = timestamp
            self.__REVISION_ALL_last_timestamp      = timestamp

        self.update_seconds_elapsed(timestamp)

        if message not in [REVISION__NOT_CLICKED, REVISION__CLICKED]:
            return

        self.__update_intervals(message,timestamp)
        self.__store_timestamps_for_next_iteration(message,timestamp)

        if self.__REVISION_previous_message != "UNKNOWN":
            # Update amounts based on whether the previous revision was clicked or not.
            self.__update_click_amounts()

        self.REVISION__ALL_amount = self.REVISION__CLICKED_amount + self.REVISION__NOT_CLICKED_amount
        self.__REVISION_previous_message = message

    # def __update_leading_clicks(self):
    #     if self.__REVISION_previous_message in [TEXT__SENTENCE_READ, REVISION__NOT_CLICKED]:
    #         self.REVISION_leading_clicks = 0
    #     if self.__REVISION_previous_message == REVISION__CLICKED:
    #         self.REVISION_leading_clicks += 1

    def update_seconds_elapsed(self, timestamp):
        # Seconds elapsed since last revision outcome
        self.REVISION__CLICKED_seconds = timestamp - self.__REVISION__CLICKED_last_timestamp
        self.REVISION__NOT_CLICKED_seconds = timestamp - self.__REVISION__NOT_CLICKED_last_timestamp \
            if self.__REVISION__NOT_CLICKED_last_timestamp else NEVER
        self.REVISION__ALL_seconds = min(self.REVISION__CLICKED_seconds, self.REVISION__NOT_CLICKED_seconds)

    def __update_intervals(self,message,timestamp):
        # Calculate the last two intervals
        self.REVISION_previous_interval = self.REVISION_last_interval
        self.REVISION_last_interval     = timestamp - self.__REVISION_ALL_last_timestamp

        # Calculate interval ratio
        if self.REVISION_previous_interval != 0:
            self.REVISION_interval_ratio = self.REVISION_last_interval / self.REVISION_previous_interval
        else:
            self.REVISION_interval_ratio = 1

    def __store_timestamps_for_next_iteration(self,message,timestamp):
        if message == REVISION__CLICKED:
            self.__REVISION__CLICKED_last_timestamp = timestamp
        if message == REVISION__NOT_CLICKED:
            self.__REVISION__NOT_CLICKED_last_timestamp = timestamp
        self.__REVISION_ALL_last_timestamp = timestamp

    def __update_click_amounts(self):
    # Update amounts based on whether the previous revision was clicked or not.
        if self.__REVISION_previous_message == REVISION__CLICKED:
            self.REVISION__CLICKED_amount += 1
        if self.__REVISION_previous_message == REVISION__NOT_CLICKED:
            self.REVISION__NOT_CLICKED_amount += 1


@enforce_types
@dataclass
class ReadingDatapointPartition(DictionaryViewWithEncapsulation):
    TEXT__WORD_HIGHLIGHTED_amount: int = 0
    TEXT__SENTENCE_CLICK_amount: int = 0
    TEXT__SENTENCE_READ_amount: int = 0
    TEXT__ALL_amount: int = 0
    TEXT__WORD_HIGHLIGHTED_seconds: int = NEVER
    TEXT__SENTENCE_CLICK_seconds: int = NEVER
    TEXT__SENTENCE_READ_seconds: int = NEVER
    TEXT__ALL_seconds: int = NEVER
    __TEXT__WORD_HIGHLIGHTED_timestamp : int = 0
    __TEXT__SENTENCE_CLICK_timestamp : int = 0
    __TEXT__SENTENCE_READ_timestamp : int = 0
    __previous_message : str = ""

    def update_from_log(self, log: CoreLog):
        message, timestamp = log.message, log.timestamp

        # Base case: first log
        if self.TEXT__ALL_seconds == NEVER:
            # First event counts as a click and a highlight
            self.__TEXT__SENTENCE_CLICK_timestamp = timestamp
            self.TEXT__SENTENCE_CLICK_amount += 1
            self.__TEXT__WORD_HIGHLIGHTED_timestamp = timestamp
            self.TEXT__WORD_HIGHLIGHTED_amount += 1

        self.update_timestamp(timestamp)

        # Update counts based on the previous message
        if self.__previous_message == TEXT__SENTENCE_READ:
            self.TEXT__SENTENCE_READ_amount += 1
        if self.__previous_message == TEXT__SENTENCE_CLICK:
            self.TEXT__SENTENCE_CLICK_amount += 1
        if self.__previous_message == TEXT__WORD_HIGHLIGHTED:
            self.TEXT__WORD_HIGHLIGHTED_amount += 1

        # Update previous message
        self.__previous_message = message

        # Update timestamps
        if message == TEXT__SENTENCE_READ:
            self.__TEXT__SENTENCE_READ_timestamp = timestamp
        if message == TEXT__SENTENCE_CLICK:
            self.__TEXT__SENTENCE_CLICK_timestamp = timestamp
        if message == TEXT__WORD_HIGHLIGHTED:
            self.__TEXT__WORD_HIGHLIGHTED_timestamp = timestamp

        self.TEXT__ALL_amount  = self.TEXT__SENTENCE_READ_amount + self.TEXT__SENTENCE_CLICK_amount

    def update_timestamp(self, timestamp):
        # Update seconds elapsed based on previous timestamp
        self.TEXT__SENTENCE_READ_seconds = timestamp - self.__TEXT__SENTENCE_READ_timestamp \
            if self.__TEXT__SENTENCE_READ_timestamp else NEVER
        self.TEXT__SENTENCE_CLICK_seconds = timestamp - self.__TEXT__SENTENCE_CLICK_timestamp \
            if self.__TEXT__SENTENCE_CLICK_timestamp else NEVER
        self.TEXT__WORD_HIGHLIGHTED_seconds = timestamp - self.__TEXT__WORD_HIGHLIGHTED_timestamp \
            if self.__TEXT__WORD_HIGHLIGHTED_timestamp else NEVER
        self.TEXT__ALL_seconds = min(self.TEXT__SENTENCE_READ_seconds, self.TEXT__SENTENCE_CLICK_seconds, self.TEXT__WORD_HIGHLIGHTED_seconds)


@enforce_types
@dataclass
class AllDatapointPartition(DictionaryViewWithEncapsulation):
    ALL_amount: int  = 0
    ALL_seconds: int = NEVER
    ALL_leading_failures_amount : int = 0
    ALL_leading_failures_seconds : int = 0
    ALL_leading_recalls_amount : int  = 0
    ALL_leading_recalls_seconds : int  = 0
    ALL_longest_leading_recalls_seconds : int = 0
    __last_timestamp : int = 0
    __last_message : str   = "UNKNOWN"
    __first_recall_in_streak_timestamp : int = 0
    __first_failure_in_streak_timestamp : int = 0

    def update_from_log(self, log: CoreLog):
        self.update_timestamp(log.timestamp)
        self.ALL_amount += 1
        self.__last_timestamp = log.timestamp
        self.__last_message = log.message

    def update_timestamp(self, timestamp):
        self.ALL_seconds = timestamp - self.__last_timestamp
        self.__update_streak()
        self.__last_message = "UNKNOWN"

    def __update_streak(self):
        # Calculates the amount of consecutive successful recalls
        # As well as the interval without looking at a definition
        if self.__last_message in [REVISION__CLICKED, TEXT__WORD_HIGHLIGHTED]:
            if self.__first_failure_in_streak_timestamp == 0:
                self.__first_failure_in_streak_timestamp = self.__last_timestamp
            self.__update_failure_streak()

        if self.__last_message in [REVISION__NOT_CLICKED, TEXT__SENTENCE_READ]:
            if self.__first_recall_in_streak_timestamp == 0:
                self.__first_recall_in_streak_timestamp = self.__last_timestamp
            self.__update_recall_streak()

        if self.__last_message == TEXT__SENTENCE_CLICK:
        # Special case: continues the trend but doesn't establish a new one
            if self.__first_recall_in_streak_timestamp != 0:
                self.__update_recall_streak()
            elif self.__first_failure_in_streak_timestamp != 0:
                self.__update_failure_streak()

    def __update_failure_streak(self):
        # Increase count
        self.ALL_leading_failures_amount += 1
        # Update seconds elapsed
        self.ALL_leading_failures_seconds = self.__last_timestamp - self.__first_failure_in_streak_timestamp
        # Reset recall count and time
        self.ALL_leading_recalls_amount = 0
        self.ALL_leading_recalls_seconds = 0
        self.__first_recall_in_streak_timestamp = 0

    def __update_recall_streak(self):
        # Increase count
        self.ALL_leading_recalls_amount += 1
        # Update seconds elapsed
        self.ALL_leading_recalls_seconds = self.__last_timestamp - self.__first_recall_in_streak_timestamp
        # Update longest streak
        if self.ALL_longest_leading_recalls_seconds < self.ALL_leading_recalls_seconds:
            self.ALL_longest_leading_recalls_seconds = self.ALL_leading_recalls_seconds
        # Reset recall count and time
        self.ALL_leading_failures_amount = 0
        self.ALL_leading_failures_seconds = 0
        self.__first_failure_in_streak_timestamp = 0


class Datapoint:
    """
    A datapoint is a composite of other smaller objects known as
    datapoint partitions, which only store part of the data.

    A Datapoint is therefore a composite object which keeps track of all the
    partitions and exposes an interface to both update the partitions together
    and to retrieve a dictionary containing either the full data, only the
    revision data, or only the reading data.
    """

    def __init__(self):
        self.common = CommonDatapointData()
        self.reading = ReadingDatapointPartition()
        self.revision = RevisionDatapointPartition()
        self.all = AllDatapointPartition()

    def __base_update_from_log(self, log):
        self.reading.update_from_log(log)
        self.revision.update_from_log(log)
        self.all.update_from_log(log)

    def update_from_log(self, log):
        self.common.update_from_log(log)
        self.__base_update_from_log(log)

    def update_from_log_counting_text_interactions_as_clicks(self, log):
        self.common.update_from_log_counting_text_interactions_as_clicks(log)
        self.__base_update_from_log(log)

    def update_timestamp(self, timestamp):
        self.common.update_timestamp(timestamp)
        self.reading.update_timestamp(timestamp)
        self.revision.update_seconds_elapsed(timestamp)
        self.all.update_timestamp(timestamp)

    def view_reading_data(self):
        return {**self.common.to_dict(), **self.reading.to_dict()}

    def view_revision_data(self):
        return {**self.common.to_dict(), **self.revision.to_dict()}

    def view_all_data(self):
        # Aggregate the
        return {**self.common.to_dict(), **self.reading.to_dict(), **self.revision.to_dict(), **self.all.to_dict()}
