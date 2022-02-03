import numpy as np

import pyqtgraph
from pyqtgraph.Qt import QtGui
from pyqtgraph.functions import mkPen

from osu_analysis import StdScoreData

from app.misc.utils import MathUtils
from app.data_recording.data import RecData
from app.widgets.miss_plot import MissPlotItem


class ReplayHitDOffsetGraph(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Hit d-offset graph')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLimits(yMin=-250, yMax=250)
        self.__graph.setRange(xRange=[-10, 10000], yRange=[-250, 250])
        self.__graph.setLabel('left', 't-offset', units='ms', unitPrefix='')
        self.__graph.setLabel('bottom', 'time', units='ms', unitPrefix='')
        self.__graph.addLegend()

        self.__plot_delta = pyqtgraph.ErrorBarItem(beam=0)
        self.__graph.addItem(self.__plot_delta)

        self.__plot_range = pyqtgraph.ErrorBarItem(beam=0)
        self.__graph.addItem(self.__plot_range)

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

        self.__plot_hit_doffsets(play_data)


    def __plot_hit_doffsets(self, play_data):
        # Determine what was the latest play
        data_filter = \
            (play_data[:, RecData.TIMESTAMP] == max(play_data[:, RecData.TIMESTAMP])) & \
            (play_data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_HITP)
        data = play_data[data_filter]

        # Extract timings and hit_offsets
        hit_timings = data[:, RecData.TIMINGS]
        hit_offsets = data[:, RecData.T_OFFSETS]

        doffset1 = hit_offsets[1:-1] - hit_offsets[:-2]     # x[1] - x[0]
        doffset2 = hit_offsets[2:] - hit_offsets[1:-1]      # x[2] - x[1]

        avg_doffset = 0.5*(doffset1 + doffset2)
        var_doffset = np.abs(doffset1 - doffset2)

        # Calculate view
        xMin = min(hit_timings) - 100
        xMax = max(hit_timings) + 100

        x = hit_timings[2:]
        y_avg = avg_doffset

        y_range = var_doffset

        # Set plot data
        self.__plot_delta.setData(x=x, y=y_avg/2, top=y_avg/2, bottom=y_avg/2, pen=mkPen((200, 200, 200, 200), width=5))
        self.__plot_range.setData(x=x, y=y_avg, top=y_range/2, bottom=y_range/2, pen=mkPen((50, 100, 50, 150), width=2))
        
        self.__graph.setLimits(xMin=xMin - 100, xMax=xMax + 100)
        self.__graph.setRange(xRange=[ xMin - 100, xMax + 100 ])

        self.hit_metrics.setText(
            f'''
            UR: {10*np.std(hit_offsets):.2f}
            avg offset delta: {np.mean(np.abs(avg_doffset)):.2f} ms
            avg offset range: {np.mean(var_doffset):.2f} ms
            '''
        )


    def __on_view_range_changed(self, _=None):
        view = self.__graph.viewRect()
        pos_x = view.left()
        pos_y = view.bottom()

        margin_x = 0.001*(view.right() - view.left())
        margin_y = 0.001*(view.top() - view.bottom())

        self.hit_metrics.setPos(pos_x + margin_x, pos_y + margin_y)
