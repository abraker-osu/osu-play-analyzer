import numpy as np

import pyqtgraph
from pyqtgraph.Qt import QtGui

from osu_analysis import StdScoreData

from app.misc.utils import MathUtils
from app.data_recording.data import RecData
from app.widgets.miss_plot import MissPlotItem
import osu_analysis


class HitOffsetGraph(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

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

        self.__miss_plot = MissPlotItem()
        self.__graph.addItem(self.__miss_plot)

        self.__graph.addLine(x=None, y=0, pen=pyqtgraph.mkPen((0, 150, 0, 255), width=1))

        self.__offset_avg_line = pyqtgraph.InfiniteLine(angle=0, pen=pyqtgraph.mkPen((255, 255, 0, 150), width=1))
        self.__graph.addItem(self.__offset_avg_line)

        self.__offset_std_line_pos = pyqtgraph.InfiniteLine(angle=0, pen=pyqtgraph.mkPen((255, 150, 0, 150), width=1))
        self.__offset_std_line_neg = pyqtgraph.InfiniteLine(angle=0, pen=pyqtgraph.mkPen((255, 150, 0, 150), width=1))

        self.__graph.addItem(self.__offset_std_line_pos)
        self.__graph.addItem(self.__offset_std_line_neg)

        # Hit stats
        self.hit_metrics = pyqtgraph.TextItem('', anchor=(0, 0), )
        self.__graph.addItem(self.hit_metrics)

        # Put it all together
        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)

        self.__graph.sigRangeChanged.connect(self.__on_view_range_changed)
        self.__on_view_range_changed()


    def plot_data(self, play_data):
        if play_data.shape[0] == 0:
            return

        self.__plot_misses(play_data)
        self.__plot_hit_offsets(play_data)
        self.__plot_avg_global(play_data)
        self.__update_hit_stats(play_data)


    def __plot_hit_offsets(self, play_data):
        # Determine what was the latest play
        data_filter = \
            (play_data[:, RecData.TIMESTAMP] == max(play_data[:, RecData.TIMESTAMP])) & \
            (play_data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_HITP)
        data = play_data[data_filter]

        # Extract timings and hit_offsets
        hit_timings = data[:, RecData.TIMINGS]
        hit_offsets = data[:, RecData.T_OFFSETS]

        # Calculate view
        xMin = min(hit_timings) - 100
        xMax = max(hit_timings) + 100

        # Set plot data
        self.__plot.setData(hit_timings, hit_offsets, pen=None, symbol='o', symbolPen=None, symbolSize=2, symbolBrush=(100, 100, 255, 200))
        self.__graph.setLimits(xMin=xMin - 100, xMax=xMax + 100)
        self.__graph.setRange(xRange=[xMin - 100, xMax + 100])


    def __plot_misses(self, play_data):
        # Determine what was the latest play
        data_filter = \
            (play_data[:, RecData.TIMESTAMP] == max(play_data[:, RecData.TIMESTAMP])) & \
            (play_data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_MISS)
        data = play_data[data_filter]

        # Extract data and plot
        hit_timings = data[:, RecData.TIMINGS]
        self.__miss_plot.setData(hit_timings)


    def __plot_avg_global(self, play_data):
        # Determine what was the latest play
        data_filter = \
            (play_data[:, RecData.TIMESTAMP] == max(play_data[:, RecData.TIMESTAMP])) & \
            (play_data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_HITP)
        data = play_data[data_filter]

        # Extract timings and hit_offsets
        hit_offsets = data[:, RecData.T_OFFSETS]
        mean_offset = np.mean(hit_offsets)
        std_offset = np.std(hit_offsets)

        # Set plot data
        self.__offset_avg_line.setValue(mean_offset)
        self.__offset_std_line_pos.setValue(std_offset*2 + mean_offset)
        self.__offset_std_line_neg.setValue(-std_offset*2 + mean_offset)

        print(f'mean = {mean_offset:.2f} ms    std = {std_offset:.2f} ms')


    def __update_hit_stats(self, play_data):
        # Determine what was the latest play
        data_filter = \
            (play_data[:, RecData.TIMESTAMP] == max(play_data[:, RecData.TIMESTAMP]))
        data = play_data[data_filter]
        
        free_misses = \
            (data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_MISS) & \
            (data[:, RecData.ACT_TYPE] == StdScoreData.ACTION_FREE)
        num_free_misses = np.count_nonzero(free_misses)

        press_misses = \
            (data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_MISS) & \
            (data[:, RecData.ACT_TYPE] == StdScoreData.ACTION_PRESS)
        num_press_misses = np.count_nonzero(press_misses)

        release_misses = \
            (data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_MISS) & \
            (data[:, RecData.ACT_TYPE] == StdScoreData.ACTION_RELEASE)
        num_release_misses = np.count_nonzero(release_misses)

        hold_misses = \
            (data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_MISS) & \
            (data[:, RecData.ACT_TYPE] == StdScoreData.ACTION_HOLD)
        num_hold_misses = np.count_nonzero(hold_misses)

        hits = \
            (data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_HITP)
        data = play_data[hits]

        t_offsets = data[:, RecData.T_OFFSETS]

        acc_window = 200  # 95% dev (ms)
        acc_score = MathUtils.normal_distr(t_offsets, 0, acc_window/2)/MathUtils.normal_distr(0, 0, acc_window/2)
        acc = acc_score.sum() / (len(acc_score) + num_press_misses + num_release_misses + num_hold_misses)

        self.hit_metrics.setText(
            f'''
            num free misses: {num_free_misses}
            num press misses: {num_press_misses}
            num release misses: {num_release_misses}
            num hold misses: {num_hold_misses}
            acc: {100*acc:.2f}%
            '''
        )

    def __on_view_range_changed(self, _=None):
        view = self.__graph.viewRect()
        pos_x = view.left()
        pos_y = view.bottom()

        margin_x = 0.001*(view.right() - view.left())
        margin_y = 0.001*(view.top() - view.bottom())

        self.hit_metrics.setPos(pos_x + margin_x, pos_y + margin_y)
