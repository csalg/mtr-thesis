import pytest

from wrangling.Datapoint_test import logs, logs_insufficient_data
from wrangling.DatasetFactory import DatasetFactory
from wrangling.Log_test import invalid_logs


def test_DatasetFactory():
    factory = DatasetFactory()

    with pytest.raises(Exception, match="logs"):
        factory.create_dataframe_with_all_data_sequence()

    # Should fail silently attempting to add incorrectly formatted logs
    for log in invalid_logs:
        _, log = log
        factory.add_logs([log,])

    # Should raise an exception because no logs were added
    with pytest.raises(Exception, match="logs"):
        factory.create_dataframe_with_all_data_sequence()

    # Datapoints with insufficient data will not be created
    factory = DatasetFactory()
    factory.add_logs(logs_insufficient_data)
    with pytest.raises(Exception, match="logs"):
        factory.create_dataframe_with_all_data_sequence()

    # Create different views from logs
    factory.add_logs(logs)
    all_data_sequence = factory.create_dataframe_with_all_data_sequence()
    all_data_flattened = factory.create_dataframe_with_all_data_flattened()
    revision_data_sequence = factory.create_dataframe_with_only_revision_data_sequence()
    revision_data_flattened = factory.create_dataframe_with_only_revision_data_flattened()
    reading_data_sequence = factory.create_dataframe_with_only_reading_data_sequence()
    reading_data_flattened = factory.create_dataframe_with_only_reading_data_flattened()

    # Assert lengths are correct
    for df in [all_data_flattened, revision_data_flattened, reading_data_flattened]:
        assert len(df) == 1
    for df in [all_data_sequence, revision_data_sequence, reading_data_sequence]:
        assert len(df) == 3

    # Assert each dataframe has fields according to requirements.
    common_columns = {'CLICKED', 'FIRST_EXPOSURE_seconds'}
    reading_columns = {'TEXT__WORD_HIGHLIGHTED_amount', 'TEXT__SENTENCE_CLICK_amount', 'TEXT__SENTENCE_READ_amount',
                       'TEXT__ALL_amount', 'TEXT__WORD_HIGHLIGHTED_seconds', 'TEXT__SENTENCE_CLICK_seconds',
                       'TEXT__SENTENCE_READ_seconds', 'TEXT__ALL_seconds'}
    revision_columns = {'REVISION__CLICKED_amount', 'REVISION__NOT_CLICKED_amount', 'REVISION__ALL_amount',
                        'REVISION__CLICKED_seconds', 'REVISION__NOT_CLICKED_seconds', 'REVISION__ALL_seconds',
                        'REVISION_last_interval', 'REVISION_previous_interval', 'REVISION_interval_ratio'}
    both_columns =  {'ALL_amount', 'ALL_seconds'}

    for df in [all_data_flattened, all_data_sequence]:
        assert not set(list(df.columns)) - common_columns.union(reading_columns, revision_columns, both_columns)
    for df in [reading_data_flattened, reading_data_sequence]:
        assert not set(list(df.columns)) - common_columns.union(reading_columns)
    for df in [revision_data_flattened, revision_data_sequence]:
        assert not set(list(df.columns)) - common_columns.union(revision_columns)
