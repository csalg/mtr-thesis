from collections import defaultdict, namedtuple

import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import pandas as pd
from sortedcontainers import SortedKeyList

from wrangling.domain import *
from wrangling.DatapointBuilder import DatapointBuilder


@dataclass
class PlotConfig:
    message_to_color = {
        REVISION__CLICKED: "red",
        TEXT__WORD_HIGHLIGHTED: "purple",
        REVISION__NOT_CLICKED: "blue",
        TEXT__SENTENCE_READ: "green",
        TEXT__SENTENCE_CLICK: "grey"
    }
    message_to_height = {
        REVISION__CLICKED: 0.,
        TEXT__WORD_HIGHLIGHTED: 0.1,
        REVISION__NOT_CLICKED: 1.,
        TEXT__SENTENCE_READ: 0.9,
        TEXT__SENTENCE_CLICK: 0.5
    }
    recall_score_colour = "grey"
    interval_between_points = 12 * 60 * 60
    add_time_after_last_timestamp = 10 * 24 * 60 * 60,

default_plot_config = PlotConfig()

EstimatorPlotDTO = namedtuple("EstimatorPlotDTO", ["name", "color", "estimator"])

class PlotFactory:

    def __init__(self,
                 config=default_plot_config,
                 estimators=None
                 ):
        self.config = config
        self.estimators = estimators
        self.lemmas_to_logs = defaultdict(list)
        pass

    def add_logs(self, log_dicts):
        """
        Adds logs to internal member data.
        """
        for log_dict in log_dicts:
            try:
                log = Log.from_dictionary(log_dict)
                self.lemmas_to_logs[log.id()].append(log)
            except:
                pass

    def top_lemmas(self, n=100):
        """
        Returns a list of (lemma, username, number of events) tuples
        for the n lemmas with the most events.
        """
        lemmas_lengths = SortedKeyList(key=lambda key_val: -key_val[1])
        for key, val in self.lemmas_to_logs.items():
            lemmas_lengths.add((key, len(val)))
        return list(lemmas_lengths)[0:n]

    def plot(self, id=None, fig_ax=None):
        """
        Plots time as X and recall score as y.
        Events are plotted as scatter, recall score is plotted as a
        dotted line and estimator, if available, is plotted as a solid
        line.
        """
        try:
            logs = self.lemmas_to_logs[id]
            logs.sort(key=lambda log: log.timestamp)
        except:
            raise ValueError(f"No logs have been added for lemma id: {id}")

        if not fig_ax:
            fig, ax = plt.subplots(figsize=(40, 20))
        else:
            fig, ax = fig_ax

        self.__set_text_and_axes(ax, id)
        self.__plot_scatter(ax, logs)
        self.__plot_smoothed_recall_score(ax, logs)
        if self.estimators:
            for estimator in self.estimators:
                self.__plot_predicted_retention_rate(ax, logs, estimator.estimator, estimator.color)

    def __set_text_and_axes(self, ax, id):
        """
        Sets the title, labels and legend (basically
        everything that is not data).
        """
        # ax.set_title(id)
        ax.set_ylim([-0.1, 1.1])
        ax.set_xlabel("Days elapsed since first known exposure", fontsize=40)
        ax.set_ylabel("Probability of recall", fontsize=40)
        ax.tick_params(labelsize=32)
        self.__set_legend(ax)

    def __set_legend(self, ax):
        plt.rcParams.update({
            'legend.fontsize': 20
        })
        handles, labels = [], []

        if self.estimators:
            labels += [estimator.name for estimator in self.estimators]
            handles += [mlines.Line2D([],[],color=estimator.color) for estimator in self.estimators]

        labels += ['Smoothed recall score']
        handles += [mlines.Line2D([],[],linewidth=6, color=self.config.recall_score_colour, linestyle=(0, (1, 2))) ]

        labels += self.config.message_to_color.keys()
        handles += [mlines.Line2D([],[],
                              marker='o',
                              markersize=20,
                              linewidth=0,
                                alpha=0.3,
                              color=color) for color in self.config.message_to_color.values()]
        ax.legend(handles, labels, loc=4, prop={'size': 30})

    def __plot_scatter(self, ax, logs):
        timestamps = list(map(lambda log: (log.timestamp - logs[0].timestamp) / (24 * 60 * 60), logs))
        colours = list(map(lambda log: self.config.message_to_color[log.message], logs))
        heights = list(map(lambda log: self.config.message_to_height[log.message], logs))

        ax.scatter(timestamps, heights, c=colours, alpha=0.3, s=400)

    def __plot_smoothed_recall_score(self, ax, logs):
        builder = DatapointBuilder.from_log(logs[0])
        for log in logs[1:]:
            builder.add_log(log)

        sample_period = 24 * 60 * 60
        _, inferred_retention_rate = builder.infer_retention_rate(sample_period=sample_period)
        timesteps = [(i + 1) for i in range(0, len(inferred_retention_rate))]

        ax.plot(timesteps, inferred_retention_rate, linewidth=6, color=self.config.recall_score_colour, linestyle=(0, (1, 6)))


    def __plot_predicted_retention_rate(self, ax, logs, estimator, color):
        # Create datapoints
        builder = DatapointBuilder.from_log(logs[0])
        for log in logs[1:]:
            builder.add_log(log)
        datapoints = builder.view_all_data_sequence_for_plotting(
            interval_between_points=self.config.interval_between_points,
            add_time_after_last_timestamp=self.config.add_time_after_last_timestamp
        )
        df = pd.DataFrame(datapoints)
        timesteps = [(datapoints[0]["FIRST_EXPOSURE_seconds"] + i * self.config.interval_between_points)/(24*60*60) for i in range(0, len(datapoints))]

        # Get y from the estimator
        predicted_retention_rate = estimator.predict(df, )

        # Plot solid line using colour from config
        ax.plot(timesteps, predicted_retention_rate, color=color, linewidth=4, linestyle="-")

    def plot_many(self, ids=[]):
        fig, ax = plt.subplots(len(ids), 1, figsize=(30, len(ids) * 15))

        for i, row in enumerate(ax):
            self.plot(ids[i], (fig, row))

        plt.show()
