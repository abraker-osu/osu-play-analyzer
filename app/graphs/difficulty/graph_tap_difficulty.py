import numpy as np
import threading
import math

import pyqtgraph
from pyqtgraph.functions import mkPen
from pyqtgraph.Qt import QtGui, QtCore

from osu_analysis import StdScoreData

from app.data_recording.data import RecData


class GraphTapDifficulty(QtGui.QWidget):

    __calc_data_event = QtCore.pyqtSignal(object, object, object)

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Tap difficulty graph')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLimits(yMin=-1, yMax=5)
        self.__graph.setRange(xRange=[-0.1, 1.1], yRange=[-1, 5])
        self.__graph.setLabel('left', 'Tap factor', units='', unitPrefix='')
        self.__graph.setLabel('bottom', 'Factors', units='%', unitPrefix='')
        self.__graph.addLegend()

        self.__diff_plot_hit = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__diff_plot_hit)

        self.__diff_plot_miss = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__diff_plot_miss)

        self.__diff_plot_perf = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__diff_plot_perf)

        self.__diff_plot_good = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__diff_plot_good)

        self.__diff_plot_bad = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__diff_plot_bad)

        # Stats
        self.hit_metrics = pyqtgraph.TextItem('', anchor=(0, 0), )
        self.__graph.addItem(self.hit_metrics)

        # Put it all together
        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)

        # Connect signals
        self.__calc_data_event.connect(self.__display_data)
        self.__graph.sigRangeChanged.connect(self.__on_view_range_changed)
        self.__on_view_range_changed()


    def plot_data(self, play_data):
        if play_data.shape[0] == 0:
            return

        thread = threading.Thread(target=self.__plot_aim_factors, args=(play_data, ))
        thread.start()


    def __plot_aim_factors(self, play_data):
        # Determine what was the latest play
        data_filter = \
            (play_data[:, RecData.TIMESTAMP] == max(play_data[:, RecData.TIMESTAMP]))
        play_data = play_data[data_filter]

        # Filter out sliders holds and releases
        data_filter = (
            (play_data[:, RecData.ACT_TYPE] != StdScoreData.ACTION_HOLD) & \
            (play_data[:, RecData.ACT_TYPE] != StdScoreData.ACTION_RELEASE)
        )
        play_data = play_data[data_filter]

        # Check if there is any data to operate on
        if play_data.shape[0] < 3:
            data_stub = np.asarray([])
            self.__calc_data_event.emit(data_stub, data_stub, data_stub)
            return

        # Calculate data
        toffsets = play_data[:, RecData.T_OFFSETS]
        timings = play_data[:, RecData.TIMINGS]
        is_miss = (play_data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_MISS)
        bpm_inc = play_data[:, RecData.DT_DEC]
        bpm_dec = play_data[:, RecData.DT_INC]

        score_mask = np.zeros((timings.shape[0] - 2, 4), dtype=np.bool)
        score_mask[:, 0] = is_miss[2:]
        score_mask[:, 1] = np.abs(toffsets[2:] <= 16)
        score_mask[:, 2] = np.abs(toffsets[2:] <= 32) & np.abs(toffsets[2:] > 16)
        score_mask[:, 3] = np.abs(toffsets[2:] > 32) & ~is_miss[2:]

        rates = 1000/(timings[2:] - timings[:-2])

        stamina = np.zeros(rates.shape[0])
        stamina_select = (bpm_dec[2:] > bpm_inc[2:])
        stamina[stamina_select] = 0.1*(np.log(bpm_inc[2:][stamina_select]/1000 + 1) + 1)
        
        data_x = np.linspace(0, 1, rates.shape[0])
        data_y = np.sort(rates*stamina)

        self.__calc_data_event.emit(data_x, data_y, score_mask)


    def __display_data(self, data_x, data_y, score_mask):
        xMin = -0.1
        xMax = 1.1

        data_x_miss = data_x[score_mask[:, 0]]
        data_y_miss = data_y[score_mask[:, 0]]

        data_x_perf = data_x[score_mask[:, 1]]
        data_y_perf = data_y[score_mask[:, 1]]

        data_x_good = data_x[score_mask[:, 2]]
        data_y_good = data_y[score_mask[:, 2]]

        data_x_bad = data_x[score_mask[:, 3]]
        data_y_bad = data_y[score_mask[:, 3]]

        # Set plot data
        self.__diff_plot_miss.setData(x=data_x_miss, y=data_y_miss/2, top=data_y_miss/2, bottom=data_y_miss/2, pen=mkPen((200, 0, 0, 200), width=2))
        self.__diff_plot_perf.setData(x=data_x_perf, y=data_y_perf/2, top=data_y_perf/2, bottom=data_y_perf/2, pen=mkPen((0, 72, 255, 150), width=2))
        self.__diff_plot_good.setData(x=data_x_good, y=data_y_good/2, top=data_y_good/2, bottom=data_y_good/2, pen=mkPen((9, 138, 0, 100), width=2))
        self.__diff_plot_bad.setData(x=data_x_bad, y=data_y_bad/2, top=data_y_bad/2, bottom=data_y_bad/2, pen=mkPen((224, 224, 0, 100), width=2))

        self.__graph.setLimits(xMin=xMin, xMax=xMax)
        self.__graph.setRange(xRange=[ xMin, xMax ])


    def __on_view_range_changed(self, _=None):
        view = self.__graph.viewRect()
        pos_x = view.left()
        pos_y = view.bottom()

        margin_x = 0.001*(view.right() - view.left())
        margin_y = 0.001*(view.top() - view.bottom())

        self.hit_metrics.setPos(pos_x + margin_x, pos_y + margin_y)
