import numpy as np
import threading
import math

import pyqtgraph
from pyqtgraph.functions import mkPen
from pyqtgraph.Qt import QtGui, QtCore

from osu_analysis import StdScoreData

from app.misc.utils import MathUtils
from app.data_recording.data import RecData


class GraphAimDifficulty(QtGui.QWidget):

    __calc_data_event = QtCore.pyqtSignal(object, object, object)

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Aim difficulty graph')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLimits(yMin=-1, yMax=12)
        self.__graph.setRange(xRange=[-0.1, 1.1], yRange=[-1, 5])
        self.__graph.setLabel('left', 'Aim factor', units='', unitPrefix='')
        self.__graph.setLabel('bottom', 'Factors', units='%', unitPrefix='')
        self.__graph.addLegend()

        self.__diff_plot_hit = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__diff_plot_hit)

        self.__diff_plot_miss = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__diff_plot_miss)

        # Stats
        self.__graph_text = pyqtgraph.TextItem('', anchor=(0, 0), )
        self.__graph.addItem(self.__graph_text)

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

        # Filter out holds
        data_filter = \
            (play_data[:, RecData.ACT_TYPE] != StdScoreData.ACTION_HOLD)
        play_data = play_data[data_filter]

        # Check if there is any data to operate on
        if play_data.shape[0] == 0:
            data_stub = np.asarray([])
            self.__calc_data_event.emit(data_stub, data_stub, data_stub)
            return

        # Calculate data
        pos_x = play_data[:, RecData.X_POS]
        pos_y = play_data[:, RecData.Y_POS]
        timing = play_data[:, RecData.TIMINGS]
        is_miss = (play_data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_MISS)
        
        dx0 = pos_x[1:-1] - pos_x[:-2]   # x1 - x0
        dx1 = pos_x[2:] - pos_x[1:-1]    # x2 - x1

        dy0 = pos_y[1:-1] - pos_y[:-2]   # y1 - y0
        dy1 = pos_y[2:] - pos_y[1:-1]    # y2 - y1
        
        theta_d0 = np.arctan2(dy0, dx0)*(180/math.pi)
        theta_d1 = np.arctan2(dy1, dx1)*(180/math.pi)

        angles = np.abs(theta_d1 - theta_d0)
        angles[angles > 180] = 360 - angles[angles > 180]
        angles = np.round(angles)

        is_miss = is_miss[2:]
        distances = np.sqrt(np.square(pos_x[2:] - pos_x[1:-1]) + np.square(pos_y[2:] - pos_y[1:-1]))
        velocities = distances / (timing[2:] - timing[1:-1])
        angle_factor = np.exp(-(180 - angles)/90)

        data_y = velocities*angle_factor*3
        #data_y = MathUtils.max_rolling(data_y, 3)
        #is_miss = MathUtils.max_rolling(is_miss, 3)

        data_x = np.linspace(0, 1, data_y.shape[0])

        sort_idx = np.argsort(data_y)
        data_y  = data_y[sort_idx]
        is_miss = is_miss[sort_idx]

        self.__calc_data_event.emit(data_x, data_y, is_miss)


    def __display_data(self, data_x, data_y, is_miss):
        xMin = -0.1
        xMax = 1.1

        data_x_hit = data_x[~is_miss]
        data_y_hit = data_y[~is_miss]

        data_x_miss = data_x[is_miss]
        data_y_miss = data_y[is_miss]

        # Set plot data
        self.__diff_plot_hit.setData(x=data_x_hit, y=data_y_hit/2, top=data_y_hit/2, bottom=data_y_hit/2, pen=mkPen((200, 200, 200, 100), width=2))
        self.__diff_plot_miss.setData(x=data_x_miss, y=data_y_miss/2, top=data_y_miss/2, bottom=data_y_miss/2, pen=mkPen((200, 0, 0, 100), width=2))

        self.__graph.setLimits(xMin=xMin, xMax=xMax)
        self.__graph.setRange(xRange=[ xMin, xMax ])

        play_percent = 1 - data_y_miss.shape[0]/data_y.shape[0]

        self.__graph_text.setText(
            f"""
            Peak difficulty:     {data_y[-1]:.2f}
            Majority difficulty: {data_y[int(data_y.shape[0]*0.95)]:.2f}
            Average difficulty:  {data_y.mean():.2f}

            Play percentage:     {play_percent:.2f}
            Play diff estimate:  {data_y[int(play_percent*data_y.shape[0])]:.2f}
            """
        )


    def __on_view_range_changed(self, _=None):
        view = self.__graph.viewRect()
        pos_x = view.left()
        pos_y = view.bottom()

        margin_x = 0.001*(view.right() - view.left())
        margin_y = 0.001*(view.top() - view.bottom())

        self.__graph_text.setPos(pos_x + margin_x, pos_y + margin_y)
