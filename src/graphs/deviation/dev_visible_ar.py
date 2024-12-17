'''
The purpose of this graph is
'''
import PyQt5
import pyqtgraph

import numpy as np

from osu_analysis import StdScoreData
from misc.osu_utils import OsuUtils


class DevVisibleAR(PyQt5.QtWidgets.QWidget):

    def __init__(self, parent=None):
        PyQt5.QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='# Notes visible vs # misses')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=-10, xMax=5000, yMin=-200, yMax=200)
        self.__graph.setRange(xRange=[-10, 300], yRange=[-200, 200])
        self.__graph.setLabel('left', 'Notes missed', units='%', unitPrefix='')
        self.__graph.setLabel('bottom', 'Density', units='# notes visible', unitPrefix='')
        self.__graph.addLegend()

        # Used to set text in legend item
        self.__label_style = pyqtgraph.PlotDataItem(pen=(0,0,0))
        self.__graph.getPlotItem().legend.addItem(self.__label_style, '')
        self.__text = self.__graph.getPlotItem().legend.getLabel(self.__label_style)

        # Put it all together
        self.__layout = PyQt5.QtWidgets.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)


    def plot_data(self, score_data, diff_data):
        if 0 in [ score_data.shape[0], diff_data.shape[0] ]:
            return

        # Clear plots for redraw
        self.__graph.clearPlots()
        self.__text.setText(f'')

        colors = pyqtgraph.mkBrush(color=[ 255, 0, 0, 150 ])

        score_data = score_data.groupby(['MD5', 'TIMESTAMP'])
        diff_data  = diff_data.groupby(['MD5', 'TIMESTAMP'])

        # Data format:
        #    {
        #         ...,
        #         num_visible : [ num_misses, num_total ],
        #         ...
        #    }
        data = {}

        # For each map and timestamp
        for i, ((idx_score, df_score), (idx_diff, df_diff)) in enumerate(zip(score_data, diff_data)):
            ar_ms       = OsuUtils.ar_to_ms(df_score['AR'].values[0])

            hit_offsets = df_score['T_HIT'].values - df_score['T_MAP'].values
            t_map       = df_score['T_MAP'].values

            press_select = (df_score['TYPE_MAP'] == StdScoreData.ACTION_PRESS)
            miss_select = (df_score['TYPE_HIT'] == StdScoreData.TYPE_MISS)

            num_notes   = np.count_nonzero(press_select)
            hit_offsets = hit_offsets[press_select]
            t_map       = t_map[press_select]
            miss_select = miss_select[press_select]

            for i in range(num_notes):
                t = t_map[i]
                num_visible = hit_offsets[((t - ar_ms) <= t_map) & (t_map <= t)].shape[0]

                if num_visible not in data:
                    data[num_visible] = [ 0, 0 ]
                data[num_visible][0] += miss_select[i]
                data[num_visible][1] += 1

        for key in data.keys():
            # Calc % misses (= misses / total)
            data[key] = data[key][0] / data[key][1]

        x_data = np.asarray(list(data.keys()))
        y_data = np.asarray(list(data.values()))
        idx_sort = np.argsort(x_data)

        self.__graph.plot(x_data[idx_sort], y_data[idx_sort], fillLevel=0, fillOutline=True, brush=(0, 0, 255, 150))
