from PyQt5 import QtCore
from PyQt5 import QtWidgets

import pyqtgraph

import numpy as np
import threading


class MapToffsetRhyGraph(QtWidgets.QWidget):

    __calc_data_event = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.__avg_data_points = True

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Avg T-offset vs Note Rhythm')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=-10, xMax=5000, yMin=-200, yMax=200)
        self.__graph.setRange(xRange=[-10, 300], yRange=[-200, 200])
        self.__graph.setLabel('left', 'Avg T-offset', units='ms', unitPrefix='')
        self.__graph.setLabel('bottom', 'Note Rhythm', units='%', unitPrefix='')
        self.__graph.addLegend()

        # Used to set text in legend item
        self.__label_style = pyqtgraph.PlotDataItem(pen=(0,0,0))
        self.__graph.getPlotItem().legend.addItem(self.__label_style, '')
        self.__text = self.__graph.getPlotItem().legend.getLabel(self.__label_style)

        # Put it all together
        self.__layout = QtWidgets.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)

        # Connect signals
        self.__calc_data_event.connect(self.__display_data)


    def plot_data(self, score_data, diff_data):
        # Clear plots for redraw
        self.__graph.clearPlots()
        self.__text.setText(f'')

        if 0 in [ score_data.shape[0], diff_data.shape[0] ]:
            return

        thread = threading.Thread(target=self.__proc_data, args=(score_data, diff_data))
        thread.start()



    def __proc_data(self, score_data, diff_data):
        score_data = score_data.groupby(['MD5', 'TIMESTAMP'])
        diff_data  = diff_data.groupby(['MD5', 'TIMESTAMP'])

        '''
        [     rhm  dev  avg_bpm
            [ ..., ..., ... ],
            ...
        ]
        '''
        data = []

        # For each map and timestamp
        for i, ((idx_score, df_score), (idx_diff, df_diff)) in enumerate(zip(score_data, diff_data)):
            nan_filter = ~np.isnan(df_diff['DIFF_T_PRESS_RHM'].values)
            t_offsets = np.diff((df_score['T_HIT'].values - df_score['T_MAP']).values[nan_filter])
            rhythms   = df_diff['DIFF_T_PRESS_RHM'].values[nan_filter][1:]

            # Operate on overlapping data points (those that have same x-axis within +/- 5%)
            rounded_rhythms = np.unique(rhythms // 5 * 5)

            # Get average offsets for collected rhythms
            t_avgs = 2 * np.asarray([ np.mean(t_offsets[(0 <= (rhythms - r)) & ((rhythms - r) < 5)]) for r in rounded_rhythms ])

            for rhythm, t_dev in zip(rounded_rhythms, t_avgs):
                data.append([ rhythm, t_dev ])

        self.__calc_data_event.emit(np.asarray(data))


    def __display_data(self, data):
        colors = pyqtgraph.mkBrush(color=[ 255, 0, 0, 150 ])
        self.__graph.plot(x=data[:, 0], y=data[:, 1], pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=colors)
