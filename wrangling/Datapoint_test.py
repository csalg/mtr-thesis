import pytest
from wrangling.Datapoint import *
from config import NEVER

logs = [
    {
        'user': 'user',
        'lemma': 'lemma',
        'timestamp': 1000,
        'message': TEXT__WORD_HIGHLIGHTED
    },
    {
        'user': 'user',
        'lemma': 'lemma',
        'timestamp': 1050,
        'message': TEXT__SENTENCE_CLICK
    },
    {
        'user': 'user',
        'lemma': 'lemma',
        'timestamp': 2000,
        'message': REVISION__CLICKED
    },
    {
        'user': 'user',
        'lemma': 'lemma',
        'timestamp': 2050,
        'message': REVISION__CLICKED
    },
    {
        'user': 'user',
        'lemma': 'lemma',
        'timestamp': 2060,
        'message': REVISION__NOT_CLICKED
    },
    {
        'user': 'user',
        'lemma': 'lemma',
        'timestamp': 100,
        'message': TEXT__WORD_HIGHLIGHTED
    },
]
logs_insufficient_data = [logs[0], logs[1]]

def test_DatapointBuilder():

    # Create a valid datapoint builder
    log = Log.from_dictionary(logs_insufficient_data[0])
    builder = DatapointBuilder.from_log(log)

    # For the builder to create datapoints, at least an initial event and
    # an additional revision event are required
    def assert_views_throw_exceptions():
        with pytest.raises(Exception):
            builder.view_all_data_sequence()
            builder.view_all_data_flattened()
            builder.view_reading_data_sequence()
            builder.view_reading_data_flattened()
            builder.view_all_data_sequence()
            builder.view_all_data_flattened()

    # We only have only logged a log instance in the builder, so we shouldn't
    # be allowed to build a data point.
    assert_views_throw_exceptions()

    # Should also throw an exception when there are several logs, but no revision
    # events (without considering the initial event)
    log = Log.from_dictionary(logs_insufficient_data[-1])
    builder.add_log(log)
    assert_views_throw_exceptions()

    # Add all the logs
    log = Log.from_dictionary(logs[0])
    builder = DatapointBuilder.from_log(log)
    for log in logs[1:]:
        log = Log.from_dictionary(log)
        builder.add_log(log)

    # Check the complete data point sequence is correct.
    # (All other query methods are subsets of this sequence)
    sequence = builder.view_all_data_sequence()

    # Three revision events, so there should be three data points
    assert len(sequence) == 3

    # First datapoint
    assert sequence[0]["CLICKED"] == True
    assert sequence[0]["FIRST_EXPOSURE_seconds"] == 1900
    assert sequence[0]["REVISION__CLICKED_amount"] == 0
    assert sequence[0]["REVISION__NOT_CLICKED_amount"] == 0
    assert sequence[0]["REVISION__CLICKED_seconds"] == 1900  # The first occurrence counts as a revision click as well
    assert sequence[0]["REVISION__NOT_CLICKED_seconds"] == NEVER
    assert sequence[0]["REVISION_last_interval"] == 1900  # The interval between the current revision log and the one before that.
    assert sequence[0]["REVISION_previous_interval"] == NEVER  # The interval between the previous revision event and its previous revision event
    assert sequence[0]["TEXT__WORD_HIGHLIGHTED_amount"] == 3 # The first event counts as a highlight
    assert sequence[0]["TEXT__SENTENCE_CLICK_amount"] == 2 # The first event counts as a click
    assert sequence[0]["TEXT__SENTENCE_READ_amount"] == 0
    assert sequence[0]["TEXT__ALL_amount"] == 2 # It is not possible to highlight a word without clicking on the sentence.
    assert sequence[0]["TEXT__WORD_HIGHLIGHTED_seconds"] == 1000
    assert sequence[0]["TEXT__SENTENCE_CLICK_seconds"] == 950 # First event counts as a click
    assert sequence[0]["TEXT__SENTENCE_READ_seconds"] == NEVER
    assert sequence[0]["TEXT__ALL_seconds"] == 950
    assert sequence[0]["ALL_amount"] == 4
    assert sequence[0]["ALL_seconds"] == 950

    # Last datapoint
    assert sequence[-1]["CLICKED"] == False
    assert sequence[-1]["FIRST_EXPOSURE_seconds"] == 1960
    assert sequence[-1]["REVISION__CLICKED_amount"] == 2
    assert sequence[-1]["REVISION__NOT_CLICKED_amount"] == 0
    assert sequence[-1]["REVISION__ALL_amount"] == 2
    assert sequence[-1]["REVISION__CLICKED_seconds"] == 10
    assert sequence[-1]["REVISION__NOT_CLICKED_seconds"] == NEVER
    assert sequence[-1]["REVISION__ALL_seconds"] == 10
    assert sequence[-1]["TEXT__WORD_HIGHLIGHTED_amount"] == 3
    assert sequence[-1]["TEXT__SENTENCE_CLICK_amount"] == 2
    assert sequence[-1]["TEXT__SENTENCE_READ_amount"] == 0
    assert sequence[-1]["TEXT__ALL_amount"] == 2
    assert sequence[-1]["TEXT__WORD_HIGHLIGHTED_seconds"] == 1060
    assert sequence[-1]["TEXT__SENTENCE_CLICK_seconds"] == 1010
    assert sequence[-1]["TEXT__SENTENCE_READ_seconds"] == NEVER
    assert sequence[-1]["TEXT__ALL_seconds"] == 1010
    assert sequence[-1]["ALL_amount"] == 6
    assert sequence[-1]["ALL_seconds"] == 10

    sequence = builder.view_all_data_sequence_counting_text_interactions_as_clicks()
    assert len(sequence) == 4

def test_Datapoint():
    pass

