import pyqtgraph
from pyqtgraph.Qt import QtGui

import numpy as np

from osu_analysis import StdScoreData
from app.data_recording.data import RecData


class GraphTOffsetBPM(QtGui.QWidget):
    """
    NOTE: Filtering distances and bpms in the overivew window probably breaks this
    since that would remove notes that would other be operated on. This will need to
    be a metric in the scoring data in the future.
    """

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

        nan_filter = ~np.isnan(play_data[:, RecData.DT_HITS])
        dt_notes_all = play_data[nan_filter, RecData.DT_NOTES]
        dt_hits_all  = play_data[nan_filter, RecData.DT_HITS]
        
        if self.__avg_data_points:
            # Average overlapping data points (those that have same x-axis within +/- 3)
            dt_hits_all = np.asarray([ np.sort(dt_hits_all[np.abs(dt_notes_all - dt_note) < 3]).mean() for dt_note in np.unique(dt_notes_all) ])
            dt_notes_all = np.unique(dt_notes_all)

            data_x = dt_notes_all
            data_y = dt_hits_all

            # Get sort mapping to make points on line graph connect in proper order
            #idx_sort = np.argsort(dt_notes)
            #data_x = dt_notes[idx_sort]
            #data_y = t_offsets[idx_sort]
        else:
            data_x = dt_notes_all
            data_y = dt_hits_all

        colors = pyqtgraph.mkBrush(color=[ 255, 0, 0, 150 ])
        self.__graph.plot(x=data_x, y=data_y, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=colors)
