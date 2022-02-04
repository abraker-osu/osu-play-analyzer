import pyqtgraph
from pyqtgraph.Qt import QtCore, QtGui

import numpy as np
import threading

from osu_analysis import StdScoreData
from app.data_recording.data import RecData


class GraphTOffsetBPM(QtGui.QWidget):

    __calc_data_event = QtCore.pyqtSignal(object, object, object)

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.__avg_data_points = True

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Avg T-Offset vs Note interval')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=-10, xMax=5000, yMin=-200, yMax=200)
        self.__graph.setRange(xRange=[-10, 300], yRange=[-200, 200])
        self.__graph.setLabel('left', 'T-Offset', units='ms', unitPrefix='')
        self.__graph.setLabel('bottom', 'Note interval', units='ms', unitPrefix='')
        self.__graph.addLegend()

        self.__std_plot = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__std_plot)

        # Used to set text in legend item
        self.__label_style = pyqtgraph.PlotDataItem(pen=(0,0,0))
        self.__graph.getPlotItem().legend.addItem(self.__label_style, '')
        self.__text = self.__graph.getPlotItem().legend.getLabel(self.__label_style)
   
        # Put it all together
        self.__layout = QtGui.QHBoxLayout(self)
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
        nan_filter = ~np.isnan(play_data[:, RecData.DT_HITS])
        dt_notes_all = play_data[nan_filter, RecData.DT_NOTES]
        dt_hits_all  = play_data[nan_filter, RecData.DT_HITS]
        dt_hits_dev  = np.zeros((dt_hits_all.shape[0], ))

        if self.__avg_data_points:
            # Average overlapping data points
            dt_notes_unique = np.unique(dt_notes_all)

            dt_hits_dev = np.asarray([ np.std(dt_hits_all[dt_notes_all == dt_note]) for dt_note in dt_notes_unique ])
            dt_hits_all = np.asarray([ np.mean(dt_hits_all[dt_notes_all == dt_note]) for dt_note in dt_notes_unique ])
            dt_notes_all = dt_notes_unique

        data_x = dt_notes_all
        data_y = dt_hits_all

        self.__calc_data_event.emit(data_x, data_y, dt_hits_dev)


    def __display_data(self, data_x, data_y, data_dev):
        colors = pyqtgraph.mkBrush(color=[ 255, 0, 0, 150 ])
        self.__graph.plot(x=data_x, y=data_y, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=colors)

        # Automatically applies 2*data_dev to the error bars
        self.__std_plot.setData(x=data_x, y=data_y, top=data_dev, bottom=data_dev)