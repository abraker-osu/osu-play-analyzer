import PyQt5
import pyqtgraph

import numpy as np
import threading

from osu_analysis import StdScoreData
from app.data_recording.data import ScoreNpyData


class GraphTOffsetVelocity(PyQt5.QtWidgets.QWidget):

    __calc_data_event = PyQt5.QtCore.pyqtSignal(object, object, object)

    def __init__(self, parent=None):
        PyQt5.QtWidgets.QWidget.__init__(self, parent)

        self.__avg_data_points = True

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Avg T-Offset vs Velocity')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=-10, xMax=5000, yMin=-200, yMax=200)
        self.__graph.setRange(xRange=[-10, 300], yRange=[-200, 200])
        self.__graph.setLabel('left', 'T-Offset', units='ms', unitPrefix='')
        self.__graph.setLabel('bottom', 'Velocity', units='osu!px/ms', unitPrefix='')
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
        # Filter out holds and misses
        data_filter = \
            (play_data[:, ScoreNpyData.ACT_TYPE] != StdScoreData.ACTION_HOLD) & \
            (play_data[:, ScoreNpyData.HIT_TYPE] != StdScoreData.TYPE_MISS)

        # Apply filter
        play_data = play_data[data_filter]
        if play_data.shape[0] == 0:
            data_stub = np.asarray([])
            self.__calc_data_event.emit(data_stub, data_stub, data_stub)
            return

        # Calculate data
        pos_x = play_data[:, ScoreNpyData.X_POS]
        pos_y = play_data[:, ScoreNpyData.Y_POS]
        timing = play_data[:, ScoreNpyData.TIMINGS]

        distances = np.sqrt(np.square(pos_x[1:] - pos_x[:-1]) + np.square(pos_y[1:] - pos_y[:-1]))
        velocities = distances / (timing[1:] - timing[:-1])

        data_x   = 1000*velocities
        data_y   = play_data[1:, ScoreNpyData.T_OFFSETS]
        data_dev = np.zeros((data_x.shape[0], ))

        if self.__avg_data_points:
            # Average overlapping data points
            data_x_unique = np.unique(data_x)
            
            data_dev = np.asarray([ 
                np.std(data_y[data_x == x]) if data_y[data_x == x].shape[0] > 1 else 200
                for x in data_x_unique
            ])
            data_y = np.asarray([ np.mean(data_y[data_x == x]) for x in data_x_unique ])
            data_x = data_x_unique

        self.__calc_data_event.emit(data_x, data_y, data_dev)


    def __display_data(self, data_x, data_y, data_dev):
        colors = pyqtgraph.mkBrush(color=[ 255, 0, 0, 150 ])
        self.__graph.plot(x=data_x, y=data_y, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=colors)

        # Automatically applies 2*data_dev to the error bars
        #self.__std_plot.setData(x=data_x, y=data_y, top=data_dev, bottom=data_dev, pen=(150, 150, 150, 100))
