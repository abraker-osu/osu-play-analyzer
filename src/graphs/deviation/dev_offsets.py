'''
The purpose of this graph is
'''
import PyQt6
import pyqtgraph

import numpy as np

from osu_analysis import StdScoreData


class DevOffsets(PyQt6.QtWidgets.QWidget):

    def __init__(self, parent=None):
        PyQt6.QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Avg BPM vs offset deviation')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=-10, xMax=5000, yMin=-200, yMax=200)
        self.__graph.setRange(xRange=[-10, 300], yRange=[-200, 200])
        self.__graph.setLabel('left', 'offset deviation', units='ms', unitPrefix='')
        self.__graph.setLabel('bottom', 'Avg BPM', units='BPM', unitPrefix='')
        self.__graph.addLegend()

        # Used to set text in legend item
        self.__label_style = pyqtgraph.PlotDataItem(pen=(0,0,0))
        self.__graph.getPlotItem().legend.addItem(self.__label_style, '')
        self.__text = self.__graph.getPlotItem().legend.getLabel(self.__label_style)

        # Put it all together
        self.__layout = PyQt6.QtWidgets.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)


    def plot_data(self, score_data, diff_data):
        if 0 in [ score_data.shape[0], diff_data.shape[0] ]:
            return

        score_data = score_data.groupby(['MD5', 'TIMESTAMP'])
        diff_data  = diff_data.groupby(['MD5', 'TIMESTAMP'])

        data_x = np.zeros(len(score_data))
        data_y = np.zeros(len(score_data))

        # For each map and timestamp
        for i, ((idx_score, df_score), (idx_diff, df_diff)) in enumerate(zip(score_data, diff_data)):
            bpms = 15000/df_diff['DIFF_T_PRESS_DIFF'].values
            bpms = bpms[~np.isnan(bpms)]

            # Keep just the press taps
            df_score = df_score[df_score['TYPE_MAP'] == StdScoreData.ACTION_PRESS]

            hit_offsets  = df_score['T_HIT'].values - df_score['T_MAP'].values

            # Keep just the notes that have not been missed
            hit_offsets = hit_offsets[
                (df_score['TYPE_HIT'].values == StdScoreData.TYPE_HITP)
            ]

            data_x[i] = np.mean(bpms)
            data_y[i] = np.std(hit_offsets)

        # Average along similiar x-axis value
        if True:
            data_y = np.asarray([ np.sort(data_y[data_x == x]).mean() for x in np.unique(data_x) ])
            unique_data_x = np.unique(data_x)

            # Get sort mapping to make points on line graph connect in proper order
            idx_sort = np.argsort(unique_data_x)
            data_x = unique_data_x[idx_sort]
            data_y = data_y[idx_sort]

        # Clear plots for redraw
        self.__graph.clearPlots()
        self.__text.setText(f'')

        colors = pyqtgraph.mkBrush(color=[ 255, 0, 0, 150 ])
        self.__graph.plot(x=data_x, y=data_y, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=colors)
