import math
from dataclasses import dataclass

from enforce_typing import enforce_types

TEXT__WORD_HIGHLIGHTED = "TEXT__WORD_HIGHLIGHTED"
TEXT__SENTENCE_CLICK = "TEXT__SENTENCE_CLICK"
TEXT__SENTENCE_READ = "TEXT__SENTENCE_READ"
REVISION__CLICKED = "REVISION__CLICKED"
REVISION__NOT_CLICKED = "REVISION__NOT_CLICKED"
VALID_LOG_MESSAGES = [
                        TEXT__WORD_HIGHLIGHTED,
                        TEXT__SENTENCE_CLICK,
                        TEXT__SENTENCE_READ,
                        REVISION__CLICKED,
                        REVISION__NOT_CLICKED
                    ]


@enforce_types
@dataclass
class CoreLog:
    timestamp: int
    message: str

    def __post_init__(self):
        if self.message not in VALID_LOG_MESSAGES:
            raise ValueError(f'{self.message} is not a valid log message.')


@enforce_types
@dataclass
class Log(CoreLog):
    user: str
    lemma: str

    def __post_init__(self):
        if self.message not in VALID_LOG_MESSAGES:
            raise ValueError(f'{self.message} is not a valid log message.')

    @classmethod
    def from_dictionary(cls, log_dict: dict):
        return cls(log_dict['timestamp'], log_dict['message'], log_dict['user'], log_dict['lemma'])

    def id(self):
        return f"{self.user}_{self.lemma}"


def calculate_recall_score(recalls, clicks):
    return math.sqrt(recalls) / (math.sqrt(recalls) + clicks)


def is_click(message):
    return message in [TEXT__WORD_HIGHLIGHTED, REVISION__CLICKED]


def is_recall(message):
    return message in [TEXT__SENTENCE_READ, REVISION__NOT_CLICKED]
