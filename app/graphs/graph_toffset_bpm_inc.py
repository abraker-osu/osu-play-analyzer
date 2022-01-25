import pyqtgraph
from pyqtgraph.Qt import QtGui

import numpy as np

from osu_analysis import StdScoreData
from app.data_recording.data import RecData


class GraphTOffsetBPMInc(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.__avg_data_points = True

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Avg T-Offset vs BPM Increase')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=-10, xMax=5000, yMin=-200, yMax=200)
        self.__graph.setRange(xRange=[-10, 300], yRange=[-200, 200])
        self.__graph.setLabel('left', 'T-Offset', units='ms', unitPrefix='')
        self.__graph.setLabel('bottom', 'Time since last BPM Increase', units='ms', unitPrefix='')
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

        hit_timings_all = np.asarray([])
        time_bpm_all  = np.asarray([])

        unique_timestamps = np.unique(play_data[:, RecData.TIMESTAMP])
        for timestamp in unique_timestamps:
            data_select = \
                (play_data[:, RecData.TIMESTAMP] == timestamp) & \
                (play_data[:, RecData.ACT_TYPE] == StdScoreData.ACTION_PRESS)
            data = play_data[data_select]
            
            hit_timings  = data[:, RecData.T_OFFSETS]
            time_bpm_inc = data[:, RecData.DT_DEC]

            data_filter = data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_HITP

            hit_timings  = hit_timings[data_filter]
            time_bpm_inc = time_bpm_inc[data_filter]

            hit_timings_all = np.insert(hit_timings_all, 0, hit_timings)
            time_bpm_all    = np.insert(time_bpm_all,    0, time_bpm_inc)

        if self.__avg_data_points:
            # Average overlapping data points (those that fall on same velocity)
            hit_timings_all = np.asarray([ np.sort(hit_timings_all[np.abs(time_bpm_all - time_bpm) < 3]).mean() for time_bpm in np.unique(time_bpm_all) ])
            time_bpm_all = np.unique(time_bpm_all)

            data_x = time_bpm_all
            data_y = hit_timings_all

            # Get sort mapping to make points on line graph connect in proper order
            #idx_sort = np.argsort(dt_notes)
            #data_x = dt_notes[idx_sort]
            #data_y = t_offsets[idx_sort]
        else:
            data_x = time_bpm_all
            data_y = hit_timings_all

        colors = pyqtgraph.mkBrush(color=[ 255, 0, 0, 150 ])
        self.__graph.plot(x=data_x, y=data_y, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=colors)
