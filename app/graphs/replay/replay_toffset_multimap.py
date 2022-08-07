import math
import scipy
import numpy as np

import pyqtgraph
from pyqtgraph.Qt import QtGui
from pyqtgraph.functions import mkPen

from osu_analysis import StdScoreData

from app.misc.utils import MathUtils
from app.data_recording.data import PlayNpyData



class ReplayTOffsetMultimap(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.cache_miss_count = 0

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Hit offset graph')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLimits(yMin=-200, yMax=200)
        self.__graph.setRange(xRange=[-10, 10000], yRange=[-250, 250])
        self.__graph.setLabel('left', 't-offset', units='ms', unitPrefix='')
        self.__graph.setLabel('bottom', 'time', units='ms', unitPrefix='')
        self.__graph.addLegend()

        self.__plot = self.__graph.plot()

        self.__std_plot = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__std_plot)

        self.__miss_plot = pyqtgraph.ErrorBarItem(beam=0)
        self.__graph.addItem(self.__miss_plot)

        self.__graph.addLine(x=None, y=0, pen=pyqtgraph.mkPen((0, 150, 0, 255), width=1))

        # Hit stats
        self.__hit_metrics = pyqtgraph.TextItem('', anchor=(0, 0), )
        self.__graph.addItem(self.__hit_metrics)
        self.__hit_metrics.setText('Select a map to display data')

        # Put it all together
        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)

        self.__graph.sigRangeChanged.connect(self.__on_view_range_changed)
        self.__on_view_range_changed()


    def plot_data(self, play_data):
        if play_data.shape[0] == 0:
            self.__hit_metrics.setText('No data to display')

            data_blank = np.asarray([])
            self.__plot.setData(data_blank, data_blank, pen=None, symbol='o', symbolPen=None, symbolSize=2, symbolBrush=(100, 100, 255, 200))
            self.__std_plot.setData(x=data_blank, y=data_blank, top=data_blank, bottom=data_blank, pen=(150, 150, 0, 100))
            self.__miss_plot.setData(x=data_blank, y=data_blank, top=data_blank, bottom=data_blank, pen=mkPen((200, 0, 0, 50), width=5))
            return

        unique_map_mods = np.unique(play_data['MODS'])
        if unique_map_mods.shape[0] > 1:
            self.__hit_metrics.setText('Data is displayed only when one mod combination is selected')

            data_blank = np.asarray([])
            self.__plot.setData(data_blank, data_blank, pen=None, symbol='o', symbolPen=None, symbolSize=2, symbolBrush=(100, 100, 255, 200))
            self.__std_plot.setData(x=data_blank, y=data_blank, top=data_blank, bottom=data_blank, pen=(150, 150, 0, 100))
            self.__miss_plot.setData(x=data_blank, y=data_blank, top=data_blank, bottom=data_blank, pen=mkPen((200, 0, 0, 50), width=5))
            return

        self.__plot_misses(play_data)
        self.__plot_hit_offsets(play_data)
        self.__update_hit_stats(play_data)


    def __plot_hit_offsets(self, play_data):
        # Determine what was the latest play
        data_filter = \
            (play_data['TYPE_HIT'] == StdScoreData.TYPE_HITP)
        data = play_data[data_filter]

        if data.shape[0] == 0:
            blank_data = np.asarray([])
            self.__plot.setData(blank_data, blank_data)
            self.__std_plot.setData(x=blank_data, y=blank_data, top=blank_data, bottom=blank_data, pen=mkPen((200, 0, 0, 50), width=5))
            return

        # Extract timings and hit_offsets
        hit_timings = data['T_MAP']
        hit_offsets = data['T_HIT'] - data['T_MAP']

        # Process overlapping data points along x-axis
        hit_offsets_avg = np.asarray([ np.mean(hit_offsets[hit_timings == hit_timing]) for hit_timing in np.unique(hit_timings) ])
        hit_offsets_std = np.asarray([ 
            2*np.std(hit_offsets[hit_timings == hit_timing], ddof=1) if hit_offsets[hit_timings == hit_timing].shape[0] > 1 else 200
            for hit_timing in np.unique(hit_timings) 
        ])
        hit_timings = np.unique(hit_timings)

        # Calculate view
        xMin = min(hit_timings) - 100
        xMax = max(hit_timings) + 100

        # Set plot data
        self.__plot.setData(hit_timings, hit_offsets_avg, pen=None, symbol='o', symbolPen=None, symbolSize=2, symbolBrush=(100, 100, 255, 200))
        self.__std_plot.setData(x=hit_timings, y=hit_offsets_avg, top=hit_offsets_std/2, bottom=hit_offsets_std/2, pen=(150, 150, 0, 100))

        self.__graph.setLimits(xMin=xMin - 100, xMax=xMax + 100)
        self.__graph.setRange(xRange=[ xMin - 100, xMax + 100 ])


    def __plot_misses(self, play_data):
        # Select press misses
        select_press_miss = \
            (play_data['TYPE_HIT'] == StdScoreData.TYPE_MISS) & \
            (play_data['TYPE_MAP'] == StdScoreData.ACTION_PRESS)
        data = play_data[select_press_miss]

        if data.shape[0] == 0:
            blank_data = np.asarray([])
            self.__miss_plot.setData(x=blank_data, y=blank_data, top=blank_data, bottom=blank_data, pen=mkPen((200, 0, 0, 50), width=5))
            return

        # Extract data and plot
        hit_timings = data['T_MAP']
        
        # Process overlapping data points along x-axis
        miss_count = np.asarray([ hit_timings[hit_timings == hit_timing].shape[0] for hit_timing in np.unique(hit_timings) ])
        hit_timings = np.unique(hit_timings)

        max_miss_count = np.max(miss_count)

        x = hit_timings
        y = 50*(miss_count/max_miss_count if max_miss_count > 0 else miss_count)

        self.__miss_plot.setData(x=x, y=y/2, top=y/2, bottom=y/2, pen=mkPen((200, 0, 0, 50), width=5))

        self.cache_miss_count = np.sum(miss_count)


    def __update_hit_stats(self, play_data):
        unique_map_timestamps = np.unique(play_data.index.get_level_values(1))
        num_plays = unique_map_timestamps.shape[0]

        # Extract hitcircle data
        data_filter = \
            (play_data['TYPE_HIT'] == StdScoreData.TYPE_HITP)

        hitcircles_data = play_data[1:][data_filter]
        hit_timings = hitcircles_data['T_MAP'].values
        hit_offsets = hitcircles_data['T_HIT'].values - hitcircles_data['T_MAP'].values

        # Stacks hits for each timestamp and calculates average and deviation
        avgs = np.asarray([ np.mean(hit_offsets[hit_timings == hit_timing]) for hit_timing in np.unique(hit_timings) ])
        devs = np.asarray([ 
            2*np.std(hit_offsets[hit_timings == hit_timing], ddof=1) if hit_offsets[hit_timings == hit_timing].shape[0] > 1 else 200
            for hit_timing in np.unique(hit_timings) 
        ])

        # Determine what was the latest play
        latest_timestamp = np.max(unique_map_timestamps)
        num_sliders = None
        num_circles = None

        # Determine number of sliders within the map
        for entry in play_data.groupby(level=1):
            if entry[0] != latest_timestamp:
                continue

            data = entry[1]

            # Extract slider data
            data_select = np.zeros(data.shape[0], dtype=bool)
            data_select[:-1] = \
                (data['TYPE_MAP'].values[:-1] == StdScoreData.ACTION_PRESS) & (
                    (data['TYPE_MAP'].values[1:] == StdScoreData.ACTION_HOLD) | \
                    (data['TYPE_MAP'].values[1:] == StdScoreData.ACTION_RELEASE)
                )
            num_sliders = np.sum(data_select)

            # Extract slider data
            data_select[:-1] = \
                (data['TYPE_MAP'].values[:-1] == StdScoreData.ACTION_PRESS) & ~(
                    (data['TYPE_MAP'].values[1:] == StdScoreData.ACTION_HOLD) | \
                    (data['TYPE_MAP'].values[1:] == StdScoreData.ACTION_RELEASE)
                )
            num_circles = np.sum(data_select)
            
            break
        
        if (num_sliders is None) or (num_circles is None):
            return

        offset_OD4 = 55.5  # +/-ms window
        offset_OD5 = 49.5  # +/-ms window
        offset_OD6 = 43.5  # +/-ms window
        offset_OD7 = 37.5  # +/-ms window
        offset_OD8 = 31.5  # +/-ms window

        # Calculate needed 300s for 99% accuracy
        num_50s_99  = 0
        num_100s_99 = num_circles*0.01   # 1% of score presses
        needed_num_300s_99 = math.ceil(.99*(num_circles + num_sliders) - (300*num_sliders + 100*num_50s_99 + 50*num_100s_99)/300)

        # Calculate needed 300s for 97% accuracy
        num_50s_97  = 0
        num_100s_97 = num_circles*0.04   # 4% of score presses
        needed_num_300s_97 = math.ceil(.97*(num_circles + num_sliders) - (300*num_sliders + 100*num_50s_97 + 50*num_100s_97)/300)

        # Calculate needed 300s for 95% accuracy
        num_50s_95  = num_circles*0.003  # 0.3% of score presses
        num_100s_95 = num_circles*0.625  # 6.25% of score presses
        needed_num_300s_95 = math.ceil(.95*(num_circles + num_sliders) - (300*num_sliders + 100*num_50s_95 + 50*num_100s_95)/300)

        # Need at least 2 plays for probability calc
        if num_plays < 2:
            self.__hit_metrics.setText(
               f'''
                Num hit circles: {num_circles} ({num_sliders} sliders excluded)
                Num scores: {num_plays}
                99% needed 300s: {needed_num_300s_99}      97% needed 300s: {needed_num_300s_97}      95% needed 300s: {needed_num_300s_95}

                Probabilities unavailable for <2 plays
                '''
            )
            return

        # For each score point, calculate probability it would be within OD window for one of the plays
        acc_window = 200   # 95% dev (ms)

        devs = np.copy(devs)
        devs[devs == 0] = acc_window

        prob_greater_than_neg = scipy.stats.norm.cdf(-offset_OD4, loc=avgs, scale=devs)
        prob_less_than_pos    = scipy.stats.norm.cdf(offset_OD4, loc=avgs, scale=devs)
        prob_300_OD4s = np.sort(prob_less_than_pos - prob_greater_than_neg)

        prob_greater_than_neg = scipy.stats.norm.cdf(-offset_OD5, loc=avgs, scale=devs)
        prob_less_than_pos    = scipy.stats.norm.cdf(offset_OD5, loc=avgs, scale=devs)
        prob_300_OD5s = np.sort(prob_less_than_pos - prob_greater_than_neg)
        
        prob_greater_than_neg = scipy.stats.norm.cdf(-offset_OD6, loc=avgs, scale=devs)
        prob_less_than_pos    = scipy.stats.norm.cdf(offset_OD6, loc=avgs, scale=devs)
        prob_300_OD6s = np.sort(prob_less_than_pos - prob_greater_than_neg)

        prob_greater_than_neg = scipy.stats.norm.cdf(-offset_OD7, loc=avgs, scale=devs)
        prob_less_than_pos    = scipy.stats.norm.cdf(offset_OD7, loc=avgs, scale=devs)
        prob_300_OD7s = np.sort(prob_less_than_pos - prob_greater_than_neg)

        prob_greater_than_neg = scipy.stats.norm.cdf(-offset_OD8, loc=avgs, scale=devs)
        prob_less_than_pos    = scipy.stats.norm.cdf(offset_OD8, loc=avgs, scale=devs)
        prob_300_OD8s = np.sort(prob_less_than_pos - prob_greater_than_neg)

        # Calculate probabilities of achieving of accuracies based on probabilities of achieving 300s
        # The highest probabilities are used for the calculation.
        prob_OD4_99 = np.prod(prob_300_OD4s[-needed_num_300s_99:])
        prob_OD5_99 = np.prod(prob_300_OD5s[-needed_num_300s_99:])
        prob_OD6_99 = np.prod(prob_300_OD6s[-needed_num_300s_99:])
        prob_OD7_99 = np.prod(prob_300_OD7s[-needed_num_300s_99:])
        prob_OD8_99 = np.prod(prob_300_OD8s[-needed_num_300s_99:])

        prob_OD4_97 = np.prod(prob_300_OD4s[-needed_num_300s_97:])
        prob_OD5_97 = np.prod(prob_300_OD5s[-needed_num_300s_97:])
        prob_OD6_97 = np.prod(prob_300_OD6s[-needed_num_300s_97:])
        prob_OD7_97 = np.prod(prob_300_OD7s[-needed_num_300s_97:])
        prob_OD8_97 = np.prod(prob_300_OD8s[-needed_num_300s_97:])

        prob_OD4_95 = np.prod(prob_300_OD4s[-needed_num_300s_95:])
        prob_OD5_95 = np.prod(prob_300_OD5s[-needed_num_300s_95:])
        prob_OD6_95 = np.prod(prob_300_OD6s[-needed_num_300s_95:])
        prob_OD7_95 = np.prod(prob_300_OD7s[-needed_num_300s_95:])
        prob_OD8_95 = np.prod(prob_300_OD8s[-needed_num_300s_95:])

        # Sliders are excluded from required 300s because
        # osu! doesn't process slider hit accuracy the same way for hitcircles
        # They are *kinda* excluded from probability calc by taking highest prob of 300s,
        #   but if there are sliders that have good accuracy, oh well, good for you
        self.__hit_metrics.setText(
            f'''
            Num hit circles: {num_circles} ({num_sliders} sliders excluded)
            Num scores: {num_plays}
            99% needed 300s: {needed_num_300s_99 + num_sliders}      97% needed 300s: {needed_num_300s_97 + num_sliders}      95% needed 300s: {needed_num_300s_95 + num_sliders}

            OD4 | E[300's]: {np.sum(prob_300_OD4s):.0f}   prob 99% acc: {100*prob_OD4_99:.4f}%   prob 97% acc: {100*prob_OD4_97:.4f}%   prob 95% acc: {100*prob_OD4_95:.4f}%
            OD5 | E[300's]: {np.sum(prob_300_OD5s):.0f}   prob 99% acc: {100*prob_OD5_99:.4f}%   prob 97% acc: {100*prob_OD5_97:.4f}%   prob 95% acc: {100*prob_OD5_95:.4f}%
            OD6 | E[300's]: {np.sum(prob_300_OD6s):.0f}   prob 99% acc: {100*prob_OD6_99:.4f}%   prob 97% acc: {100*prob_OD6_97:.4f}%   prob 95% acc: {100*prob_OD6_95:.4f}%
            OD7 | E[300's]: {np.sum(prob_300_OD7s):.0f}   prob 99% acc: {100*prob_OD7_99:.4f}%   prob 97% acc: {100*prob_OD7_97:.4f}%   prob 95% acc: {100*prob_OD7_95:.4f}%
            OD8 | E[300's]: {np.sum(prob_300_OD8s):.0f}   prob 99% acc: {100*prob_OD8_99:.4f}%   prob 97% acc: {100*prob_OD8_97:.4f}%   prob 95% acc: {100*prob_OD8_95:.4f}%
            '''
        )


    def __on_view_range_changed(self, _=None):
        view = self.__graph.viewRect()
        pos_x = view.left()
        pos_y = view.bottom()

        margin_x = 0.001*(view.right() - view.left())
        margin_y = 0.001*(view.top() - view.bottom())

        self.__hit_metrics.setPos(pos_x + margin_x, pos_y + margin_y)
