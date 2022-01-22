import pyqtgraph
from pyqtgraph.Qt import QtGui

import numpy as np

from osu_analysis import StdScoreData
from app.data_recording.data import RecData


class HitDistrGraph(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Hit distribution graph')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.setLabel('left', 'Freq', units='#', unitPrefix='')
        self.__graph.setLabel('bottom', 'Hit offset', units='ms', unitPrefix='')
        self.__graph.setLimits(xMin=-200, yMin=-1, xMax=200)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)

        self.__min_err_line = pyqtgraph.InfiniteLine(angle=90, pen=pyqtgraph.mkPen((255, 100, 0, 150), width=1))
        self.__graph.addItem(self.__min_err_line)

        self.__plot = self.__graph.plot()

        # Put it all together
        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)


    def plot_data(self, play_data):
        if play_data.shape[0] == 0:
            return

        # Determine what was the latest play
        data_filter = \
            (play_data[:, RecData.TIMESTAMP] == max(play_data[:, RecData.TIMESTAMP])) & \
            (play_data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_HITP)
        play_data = play_data[data_filter]

        if play_data.shape[0] == 0:
            return

        hit_offsets = play_data[:, RecData.T_OFFSETS]

        # Get a histogram for hit offsets
        step = (150 - 0)/(0.1*hit_offsets.shape[0])
        y, x = np.histogram(hit_offsets, bins=np.linspace(-150, 150, int(0.15*hit_offsets.shape[0])))
        
        if y.shape[0] == 0:
            return

        self.__plot.setData(x, y, stepMode="center", fillLevel=0, fillOutline=True, brush=(0,0,255,150))

        self.__min_err_line.setValue(x[:-1][y == np.max(y)][0] + step/2)
        print(f'Avg distr peak: {x[:-1][y == np.max(y)][0] + step/2} ms')

        y_max = np.max(y) * 1.1
        self.__graph.setLimits(yMin=-1, yMax=y_max)
        self.__graph.setRange(yRange=[ -1, y_max ])
        
