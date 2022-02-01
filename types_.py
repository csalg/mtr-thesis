from dataclasses import dataclass
from typing import Union

@dataclass
class DatasetConfiguration:
    users: Union[None, list] = None
    filename: str = 'logs-14mo.pkl'
    keep_username: bool = False
    keep_timestamp: bool = False