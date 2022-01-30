import numpy as np

import pyqtgraph
from pyqtgraph.Qt import QtGui
from pyqtgraph.functions import mkPen

from osu_analysis import StdScoreData

from app.misc.utils import MathUtils
from app.data_recording.data import RecData



class ReplayTOffsetMultimap(QtGui.QWidget):

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

        self.__std_plot = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__std_plot)

        self.__miss_plot = pyqtgraph.ErrorBarItem(beam=0)
        self.__graph.addItem(self.__miss_plot)

        self.__graph.addLine(x=None, y=0, pen=pyqtgraph.mkPen((0, 150, 0, 255), width=1))

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


    def __plot_hit_offsets(self, play_data):
        # Determine what was the latest play
        data_filter = \
            (play_data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_HITP)
        data = play_data[data_filter]

        # Extract timings and hit_offsets
        hit_timings = data[:, RecData.TIMINGS]
        hit_offsets = data[:, RecData.T_OFFSETS]

        # Process overlapping data points along x-axis
        hit_offsets_avg = np.asarray([ np.mean(hit_offsets[hit_timings == hit_timing]) for hit_timing in np.unique(hit_timings) ])
        hit_offsets_std = np.asarray([ np.std(hit_offsets[hit_timings == hit_timing]) for hit_timing in np.unique(hit_timings) ])
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
        # Determine what was the latest play
        data_filter = \
            (play_data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_MISS)
        data = play_data[data_filter]

        if data.shape[0] == 0:
            self.__miss_plot.setData(x=[], y=[], top=[], bottom=[], pen=mkPen((200, 0, 0, 50), width=5))
            return

        # Extract data and plot
        hit_timings = data[:, RecData.TIMINGS]
        
        # Process overlapping data points along x-axis
        miss_count = np.asarray([ hit_timings[hit_timings == hit_timing].shape[0] for hit_timing in np.unique(hit_timings) ])
        hit_timings = np.unique(hit_timings)

        max_miss_count = np.max(miss_count)

        x = hit_timings
        y = 50*(miss_count/max_miss_count if max_miss_count > 0 else miss_count)

        self.__miss_plot.setData(x=x, y=y/2, top=y/2, bottom=y/2, pen=mkPen((200, 0, 0, 50), width=5))


    def __on_view_range_changed(self, _=None):
        view = self.__graph.viewRect()
        pos_x = view.left()
        pos_y = view.bottom()

        margin_x = 0.001*(view.right() - view.left())
        margin_y = 0.001*(view.top() - view.bottom())

        self.hit_metrics.setPos(pos_x + margin_x, pos_y + margin_y)
