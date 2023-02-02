import scipy
import numpy as np

import PyQt5
import pyqtgraph
from pyqtgraph.functions import mkPen

from osu_analysis import StdScoreData

from app.misc.utils import MathUtils
from app.misc.utils import Utils



class ReplayTOffsetMultimap(PyQt5.QtWidgets.QWidget):

    __OFFSET_OD4 = 55.5  # +/-ms window
    __OFFSET_OD5 = 49.5  # +/-ms window
    __OFFSET_OD6 = 43.5  # +/-ms window
    __OFFSET_OD7 = 37.5  # +/-ms window
    __OFFSET_OD8 = 31.5  # +/-ms window        

    def __init__(self, parent=None):
        PyQt5.QtWidgets.QWidget.__init__(self, parent)

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

        self.__graph.addLine(x=None, y= ReplayTOffsetMultimap.__OFFSET_OD8, pen=pyqtgraph.mkPen((50, 50, 150, 200), width=1))
        self.__graph.addLine(x=None, y=-ReplayTOffsetMultimap.__OFFSET_OD8, pen=pyqtgraph.mkPen((50, 50, 150, 200), width=1))

        # Hit stats
        self.__hit_metrics = pyqtgraph.TextItem('', anchor=(0, 0), )
        self.__graph.addItem(self.__hit_metrics)
        self.__hit_metrics.setText('Select a map to display data')

        # Put it all together
        self.__layout = PyQt5.QtWidgets.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)

        self.__graph.sigRangeChanged.connect(self.__on_view_range_changed)
        self.__on_view_range_changed()


    @Utils.benchmark(__name__)
    def plot_data(self, play_data):
        if play_data.shape[0] == 0:
            self.__hit_metrics.setText('No data to display')

            data_blank = np.asarray([])
            self.__plot.setData(data_blank, data_blank, pen=None, symbol='o', symbolPen=None, symbolSize=2, symbolBrush=(100, 100, 255, 200))
            self.__std_plot.setData(x=data_blank, y=data_blank, top=data_blank, bottom=data_blank, pen=(150, 150, 0, 100))
            self.__miss_plot.setData(x=data_blank, y=data_blank, top=data_blank, bottom=data_blank, pen=mkPen((200, 0, 0, 50), width=5))
            return

        unique_map_mods = np.unique(play_data.index.get_level_values(2))
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


    @Utils.benchmark(f'    {__name__}')
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

        unique_x_data  = np.unique(hit_timings)
        if unique_x_data.shape[0] == hit_timings.shape[0]:
            hit_offsets_avg = hit_offsets
            hit_offsets_std = 1
        else:
            # y_data_avg_out = np.zeros(unique_x_data.shape[0])
            # y_data_dev_out = np.zeros(unique_x_data.shape[0])

            print('unique_x_data len = ', unique_x_data.shape[0])

            # MathUtils.avg_xy_data(hit_timings, hit_offsets, y_data_avg_out)
            # MathUtils.dev_xy_data(hit_timings, hit_offsets, y_data_avg_out, y_data_dev_out)

            # Find avg and dev for same hit timing across x-axis
            hit_offsets_avg = np.asarray([ np.mean(hit_offsets[hit_timings == hit_timing]) for hit_timing in unique_x_data ])
            hit_offsets_std = np.asarray([
                2*np.std(hit_offsets[hit_timings == hit_timing]) if hit_offsets[hit_timings == hit_timing].shape[0] > 1 else 1
                for hit_timing in unique_x_data
            ])
            hit_timings     = unique_x_data
            # hit_offsets_avg = y_data_avg_out 
            # hit_offsets_std = y_data_dev_out

        # Calculate view
        xMin = min(hit_timings) - 100
        xMax = max(hit_timings) + 100

        # Set plot data
        self.__plot.setData(hit_timings, hit_offsets_avg, pen=None, symbol='o', symbolPen=None, symbolSize=2, symbolBrush=(100, 100, 255, 200))
        self.__std_plot.setData(x=hit_timings, y=hit_offsets_avg, top=hit_offsets_std/2, bottom=hit_offsets_std/2, pen=(150, 150, 0, 100))

        self.__graph.setLimits(xMin=xMin - 100, xMax=xMax + 100)
        self.__graph.setRange(xRange=[ xMin - 100, xMax + 100 ])


    @Utils.benchmark(f'    {__name__}')
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


    @Utils.benchmark(f'    {__name__}')
    def __update_hit_stats(self, play_data):
        unique_map_timestamps = np.unique(play_data.index.get_level_values(1))
        num_plays = unique_map_timestamps.shape[0]

        # Extract hit press data
        #
        # NOTE: If only hitcircles are extracted for processing (no sliders), then
        # results tend to display very low probability outcomes. This is because a lot
        # of accuracy increasing hits come from sliders. The slider filtering portion of
        # this filter has been commented out as a result.
        all_select = \
            (play_data['TYPE_MAP'].values == StdScoreData.ACTION_PRESS)

        slider_select = np.zeros(play_data.shape[0], dtype=np.bool8)
        slider_select[:-1] = \
            (play_data['TYPE_MAP'].values[:-1] == StdScoreData.ACTION_PRESS) & (
                (play_data['TYPE_MAP'].values[1:] == StdScoreData.ACTION_HOLD) | \
                (play_data['TYPE_MAP'].values[1:] == StdScoreData.ACTION_RELEASE)
            )

        # circle_select = \
        #     (play_data['TYPE_MAP'].values[:-1] == StdScoreData.ACTION_PRESS) & ~(
        #         (play_data['TYPE_MAP'].values[1:] == StdScoreData.ACTION_HOLD) | \
        #         (play_data['TYPE_MAP'].values[1:] == StdScoreData.ACTION_RELEASE)
        #     )

        # Reduce data to just contain hitobject press info
        hitcircles_data = play_data[all_select]
        hit_timings = hitcircles_data['T_MAP'].values
        hit_offsets = hitcircles_data['T_HIT'].values - hitcircles_data['T_MAP'].values

        # Determine number of circles and sliders in the map
        unique_hit_timings, unique_idx = np.unique(hit_timings, return_index=True)
        num_total = unique_idx.shape[0]

        slider_mask = slider_select[all_select][unique_idx]
        num_sliders = np.count_nonzero(slider_mask)
        num_circles = num_total - num_sliders

        # Determine number of misses per hitobject
        miss_select = \
            (play_data['TYPE_HIT'].values == StdScoreData.TYPE_MISS) & \
            (play_data['TYPE_MAP'].values == StdScoreData.ACTION_PRESS)
        miss_mask = miss_select[all_select]

        miss_count = np.asarray([ hit_timings[(hit_timings == hit_timing) & miss_mask].shape[0] for hit_timing in unique_hit_timings ])

        # Stacks hits for each timestamp and calculates average and deviation
        avgs = np.asarray([ np.mean(hit_offsets[hit_timings == hit_timing]) for hit_timing in unique_hit_timings ])
        devs = np.asarray([ 
            np.std(hit_offsets[hit_timings == hit_timing]) if hit_offsets[hit_timings == hit_timing].shape[0] > 1 else 1
            for hit_timing in unique_hit_timings
        ])

        devs[devs == 0] = 1

        print('Avg info:')
        print(f'  OD4 Num = {np.count_nonzero((-ReplayTOffsetMultimap.__OFFSET_OD4 <= avgs) & (avgs <= ReplayTOffsetMultimap.__OFFSET_OD4))}')
        print(f'  OD5 Num = {np.count_nonzero((-ReplayTOffsetMultimap.__OFFSET_OD5 <= avgs) & (avgs <= ReplayTOffsetMultimap.__OFFSET_OD5))}')
        print(f'  OD6 Num = {np.count_nonzero((-ReplayTOffsetMultimap.__OFFSET_OD6 <= avgs) & (avgs <= ReplayTOffsetMultimap.__OFFSET_OD6))}')
        print(f'  OD7 Num = {np.count_nonzero((-ReplayTOffsetMultimap.__OFFSET_OD7 <= avgs) & (avgs <= ReplayTOffsetMultimap.__OFFSET_OD7))}')
        print(f'  OD8 Num = {np.count_nonzero((-ReplayTOffsetMultimap.__OFFSET_OD8 <= avgs) & (avgs <= ReplayTOffsetMultimap.__OFFSET_OD8))}')

        print('Dev info:')
        print(f'  OD4 Num = {np.count_nonzero((-ReplayTOffsetMultimap.__OFFSET_OD4 <= (avgs - devs)) & ((avgs + devs) <= ReplayTOffsetMultimap.__OFFSET_OD4))}')
        print(f'  OD5 Num = {np.count_nonzero((-ReplayTOffsetMultimap.__OFFSET_OD5 <= (avgs - devs)) & ((avgs + devs) <= ReplayTOffsetMultimap.__OFFSET_OD5))}')
        print(f'  OD6 Num = {np.count_nonzero((-ReplayTOffsetMultimap.__OFFSET_OD6 <= (avgs - devs)) & ((avgs + devs) <= ReplayTOffsetMultimap.__OFFSET_OD6))}')
        print(f'  OD7 Num = {np.count_nonzero((-ReplayTOffsetMultimap.__OFFSET_OD7 <= (avgs - devs)) & ((avgs + devs) <= ReplayTOffsetMultimap.__OFFSET_OD7))}')
        print(f'  OD8 Num = {np.count_nonzero((-ReplayTOffsetMultimap.__OFFSET_OD8 <= (avgs - devs)) & ((avgs + devs) <= ReplayTOffsetMultimap.__OFFSET_OD8))}')

        # Calculate needed 300s for 99% accuracy
        num_50s_99  = num_circles*0.0
        num_100s_99 = num_circles*0.010  # 1.00% of score presses
        needed_num_300s_99 = int((num_circles + num_sliders) - (num_100s_99 + num_50s_99))

        # Calculate needed 300s for 98% accuracy
        num_50s_98  = num_circles*0.0
        num_100s_98 = num_circles*0.024  # 2.40% of score presses
        needed_num_300s_98 = int((num_circles + num_sliders) - (num_100s_98 + num_50s_98))

        # Calculate needed 300s for 97% accuracy
        num_50s_97  = num_circles*0.0
        num_100s_97 = num_circles*0.040  # 4.00% of score presses
        needed_num_300s_97 = int((num_circles + num_sliders) - (num_100s_97 + num_50s_97))

        # Calculate needed 300s for 95% accuracy
        num_50s_95  = num_circles*0.003   # 0.30% of score presses
        num_100s_95 = num_circles*0.0625  # 6.25% of score presses
        needed_num_300s_95 = int((num_circles + num_sliders) - (num_100s_95 + num_50s_95))

        # For each score point, calculate probability it would be within OD window for one of the plays
        # Sliders are excluded from required 300s by marking them as 100% change of 300s because
        # osu! slider hit window is so lenient it may as well be a free hit
        # Misses are averaged into the probabilities
        prob_greater_than_neg = scipy.stats.norm.cdf(-ReplayTOffsetMultimap.__OFFSET_OD4, loc=avgs, scale=devs)
        prob_less_than_pos    = scipy.stats.norm.cdf(ReplayTOffsetMultimap.__OFFSET_OD4, loc=avgs, scale=devs)
        prob_300_OD4s = prob_less_than_pos - prob_greater_than_neg
        prob_300_OD4s[slider_mask] = 1.0
        prob_300_OD4s *= 1 - miss_count/num_plays

        prob_greater_than_neg = scipy.stats.norm.cdf(-ReplayTOffsetMultimap.__OFFSET_OD5, loc=avgs, scale=devs)
        prob_less_than_pos    = scipy.stats.norm.cdf(ReplayTOffsetMultimap.__OFFSET_OD5, loc=avgs, scale=devs)
        prob_300_OD5s = prob_less_than_pos - prob_greater_than_neg
        prob_300_OD5s[slider_mask] = 1.0
        prob_300_OD5s *= 1 - miss_count/num_plays
        
        prob_greater_than_neg = scipy.stats.norm.cdf(-ReplayTOffsetMultimap.__OFFSET_OD6, loc=avgs, scale=devs)
        prob_less_than_pos    = scipy.stats.norm.cdf(ReplayTOffsetMultimap.__OFFSET_OD6, loc=avgs, scale=devs)
        prob_300_OD6s = prob_less_than_pos - prob_greater_than_neg
        prob_300_OD6s[slider_mask] = 1.0
        prob_300_OD6s *= 1 - miss_count/num_plays

        prob_greater_than_neg = scipy.stats.norm.cdf(-ReplayTOffsetMultimap.__OFFSET_OD7, loc=avgs, scale=devs)
        prob_less_than_pos    = scipy.stats.norm.cdf(ReplayTOffsetMultimap.__OFFSET_OD7, loc=avgs, scale=devs)
        prob_300_OD7s = prob_less_than_pos - prob_greater_than_neg
        prob_300_OD7s[slider_mask] = 1.0
        prob_300_OD7s *= 1 - miss_count/num_plays

        prob_greater_than_neg = scipy.stats.norm.cdf(-ReplayTOffsetMultimap.__OFFSET_OD8, loc=avgs, scale=devs)
        prob_less_than_pos    = scipy.stats.norm.cdf(ReplayTOffsetMultimap.__OFFSET_OD8, loc=avgs, scale=devs)
        prob_300_OD8s = prob_less_than_pos - prob_greater_than_neg
        prob_300_OD8s[slider_mask] = 1.0
        prob_300_OD8s *= 1 - miss_count/num_plays

        poibin_300_OD4s = MathUtils.PoiBin(prob_300_OD4s)
        poibin_300_OD5s = MathUtils.PoiBin(prob_300_OD5s)
        poibin_300_OD6s = MathUtils.PoiBin(prob_300_OD6s)
        poibin_300_OD7s = MathUtils.PoiBin(prob_300_OD7s)
        poibin_300_OD8s = MathUtils.PoiBin(prob_300_OD8s)

        prob_OD4_99 = np.sum(np.asarray([ poibin_300_OD4s.pdf(i) for i in range(needed_num_300s_99, num_total) ]))
        prob_OD5_99 = np.sum(np.asarray([ poibin_300_OD5s.pdf(i) for i in range(needed_num_300s_99, num_total) ]))
        prob_OD6_99 = np.sum(np.asarray([ poibin_300_OD6s.pdf(i) for i in range(needed_num_300s_99, num_total) ]))
        prob_OD7_99 = np.sum(np.asarray([ poibin_300_OD7s.pdf(i) for i in range(needed_num_300s_99, num_total) ]))
        prob_OD8_99 = np.sum(np.asarray([ poibin_300_OD8s.pdf(i) for i in range(needed_num_300s_99, num_total) ]))

        prob_OD4_98 = np.sum(np.asarray([ poibin_300_OD4s.pdf(i) for i in range(needed_num_300s_98, num_total) ]))
        prob_OD5_98 = np.sum(np.asarray([ poibin_300_OD5s.pdf(i) for i in range(needed_num_300s_98, num_total) ]))
        prob_OD6_98 = np.sum(np.asarray([ poibin_300_OD6s.pdf(i) for i in range(needed_num_300s_98, num_total) ]))
        prob_OD7_98 = np.sum(np.asarray([ poibin_300_OD7s.pdf(i) for i in range(needed_num_300s_98, num_total) ]))
        prob_OD8_98 = np.sum(np.asarray([ poibin_300_OD8s.pdf(i) for i in range(needed_num_300s_99, num_total) ]))

        prob_OD4_97 = np.sum(np.asarray([ poibin_300_OD4s.pdf(i) for i in range(needed_num_300s_97, num_total) ]))
        prob_OD5_97 = np.sum(np.asarray([ poibin_300_OD5s.pdf(i) for i in range(needed_num_300s_97, num_total) ]))
        prob_OD6_97 = np.sum(np.asarray([ poibin_300_OD6s.pdf(i) for i in range(needed_num_300s_97, num_total) ]))
        prob_OD7_97 = np.sum(np.asarray([ poibin_300_OD7s.pdf(i) for i in range(needed_num_300s_97, num_total) ]))
        prob_OD8_97 = np.sum(np.asarray([ poibin_300_OD8s.pdf(i) for i in range(needed_num_300s_97, num_total) ]))

        prob_OD4_95 = np.sum(np.asarray([ poibin_300_OD4s.pdf(i) for i in range(needed_num_300s_95, num_total) ]))
        prob_OD5_95 = np.sum(np.asarray([ poibin_300_OD5s.pdf(i) for i in range(needed_num_300s_95, num_total) ]))
        prob_OD6_95 = np.sum(np.asarray([ poibin_300_OD6s.pdf(i) for i in range(needed_num_300s_95, num_total) ]))
        prob_OD7_95 = np.sum(np.asarray([ poibin_300_OD7s.pdf(i) for i in range(needed_num_300s_95, num_total) ]))
        prob_OD8_95 = np.sum(np.asarray([ poibin_300_OD8s.pdf(i) for i in range(needed_num_300s_95, num_total) ]))

        self.__hit_metrics.setText(
            f'''
            Num scores: {num_plays}
            Num hitobjects: {num_circles} + {num_sliders} sliders
            99% 300s: {needed_num_300s_99}   98% 300s: {needed_num_300s_98}   97% 300s: {needed_num_300s_97}   95% 300s: {needed_num_300s_95}

            OD4 | E[300]: {np.sum(prob_300_OD4s):.0f}   P(99%): {100*prob_OD4_99:.4f}%   P(98%): {100*prob_OD4_98:.4f}%   P(97%): {100*prob_OD4_97:.4f}%   P(95%): {100*prob_OD4_95:.4f}%
            OD5 | E[300]: {np.sum(prob_300_OD5s):.0f}   P(99%): {100*prob_OD5_99:.4f}%   P(98%): {100*prob_OD5_98:.4f}%   P(97%): {100*prob_OD5_97:.4f}%   P(95%): {100*prob_OD5_95:.4f}%
            OD6 | E[300]: {np.sum(prob_300_OD6s):.0f}   P(99%): {100*prob_OD6_99:.4f}%   P(98%): {100*prob_OD6_98:.4f}%   P(97%): {100*prob_OD6_97:.4f}%   P(95%): {100*prob_OD6_95:.4f}%
            OD7 | E[300]: {np.sum(prob_300_OD7s):.0f}   P(99%): {100*prob_OD7_99:.4f}%   P(98%): {100*prob_OD7_98:.4f}%   P(97%): {100*prob_OD7_97:.4f}%   P(95%): {100*prob_OD7_95:.4f}%
            OD8 | E[300]: {np.sum(prob_300_OD8s):.0f}   P(99%): {100*prob_OD8_99:.4f}%   P(98%): {100*prob_OD8_98:.4f}%   P(97%): {100*prob_OD8_97:.4f}%   P(95%): {100*prob_OD8_95:.4f}%
            '''
        )


    def __on_view_range_changed(self, _=None):
        view = self.__graph.viewRect()
        pos_x = view.left()
        pos_y = view.bottom()

        margin_x = 0.001*(view.right() - view.left())
        margin_y = 0.001*(view.top() - view.bottom())

        self.__hit_metrics.setPos(pos_x + margin_x, pos_y + margin_y)
