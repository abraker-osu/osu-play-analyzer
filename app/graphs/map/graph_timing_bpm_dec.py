import pyqtgraph
from pyqtgraph.Qt import QtGui

import numpy as np

from osu_analysis import StdScoreData
from app.data_recording.data import ScoreNpyData


class GraphTimingBPMDec(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Time vs Time since BPM Decrease')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=-10, xMax=5000, yMin=-200, yMax=200)
        self.__graph.setRange(xRange=[-10, 300], yRange=[-200, 200])
        self.__graph.setLabel('left', 'Time', units='ms', unitPrefix='')
        self.__graph.setLabel('bottom', 'Time since last BPM Decrease', units='ms', unitPrefix='')
        self.__graph.addLegend()

        # Used to set text in legend item
        self.__label_style = pyqtgraph.PlotDataItem(pen=(0,0,0))
        self.__graph.getPlotItem().legend.addItem(self.__label_style, '')
        self.__text = self.__graph.getPlotItem().legend.getLabel(self.__label_style)
   
        # Put it all together
        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)
        

    def plot_data(self, play_data):
        if play_data.shape[0] == 0:
            return

        # Clear plots for redraw
        self.__graph.clearPlots()
        self.__text.setText(f'')

        x_data_all = np.asarray([])
        y_data_all = np.asarray([])

        unique_timestamps = np.unique(play_data[:, ScoreNpyData.TIMESTAMP])
        for timestamp in unique_timestamps:
            data_select = \
                (play_data[:, ScoreNpyData.TIMESTAMP] == timestamp) & \
                (play_data[:, ScoreNpyData.TYPE_MAP] == StdScoreData.ACTION_PRESS)
            data = play_data[data_select]
            
            x_data_all = np.insert(x_data_all, 0, data[:, ScoreNpyData.T_MAP])
            y_data_all = np.insert(y_data_all, 0, data[:, ScoreNpyData.DT_INC])

        colors = pyqtgraph.mkBrush(color=[ 255, 0, 0, 150 ])
        self.__graph.plot(x=x_data_all, y=y_data_all, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=colors)
