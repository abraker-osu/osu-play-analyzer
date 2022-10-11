import PyQt5
import pyqtgraph

import numpy as np
import threading

from osu_analysis import StdScoreData
from app.data_recording.data import PlayNpyData


class GraphTOffsetBPM(PyQt5.QtWidgets.QWidget):

    __calc_data_event = PyQt5.QtCore.pyqtSignal(object, object, object)

    def __init__(self, parent=None):
        PyQt5.QtWidgets.QWidget.__init__(self, parent)

        self.__avg_data_points = True

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Tap interval vs Note interval')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=-10, xMax=5000, yMin=-200, yMax=200)
        self.__graph.setRange(xRange=[-10, 300], yRange=[-200, 200])
        self.__graph.setLabel('left', 'Tap interval', units='ms', unitPrefix='')
        self.__graph.setLabel('bottom', 'Note interval', units='ms', unitPrefix='')
        self.__graph.addLegend()

        self.__std_plot = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__std_plot)

        # Used to set text in legend item
        self.__label_style = pyqtgraph.PlotDataItem(pen=(0,0,0))
        self.__graph.getPlotItem().legend.addItem(self.__label_style, '')
        self.__text = self.__graph.getPlotItem().legend.getLabel(self.__label_style)
   
        # Put it all together
        self.__layout = PyQt5.QtWidgets.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)
                       
        # Connect signals
        self.__calc_data_event.connect(self.__display_data)
        

    def plot_data(self, play_data):
        # Clear plots for redraw
        self.__graph.clearPlots()
        self.__text.setText(f'')

        if play_data.shape[0] == 0:
            return

        thread = threading.Thread(target=self.__proc_data, args=(play_data, ))
        thread.start()

    def __proc_data(self, play_data):
        data = play_data[['DIFF_T_PRESS_RATE', 'T_HIT', 'T_MAP']].values
        data = data[~(np.isnan(data).any(axis=1))]

        x_data = data[:, 0]
        y_data = data[:, 1] - data[:, 2]

        if self.__avg_data_points:
            # Average overlapping data points
            x_data_uniques = np.unique(x_data)

            y_data_dev = np.asarray([ np.std(x_data[x_data == x]) for x in x_data_uniques ])
            y_data_avg = np.asarray([ np.mean(y_data[x_data == x]) for x in x_data_uniques ])
            
            x_data = x_data_uniques
            y_data = y_data_avg

        self.__calc_data_event.emit(x_data, y_data, y_data_dev)


    def __display_data(self, data_x, data_y, data_dev):
        colors = pyqtgraph.mkBrush(color=[ 255, 0, 0, 150 ])
        self.__graph.plot(x=data_x, y=data_y, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=colors)

        # Automatically applies 2*data_dev to the error bars
        self.__std_plot.setData(x=data_x, y=data_y, top=data_dev, bottom=data_dev, pen=(150, 150, 150, 100))
