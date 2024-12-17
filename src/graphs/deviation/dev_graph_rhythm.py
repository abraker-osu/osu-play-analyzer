from PyQt5 import QtWidgets
import pyqtgraph

import numpy as np

from osu_analysis import StdScoreData
from misc.osu_utils import OsuUtils


class DevGraphRhythm(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Rhm dev-t')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLimits(xMin=-10, xMax=110, yMin=-10, yMax=200)
        self.__graph.setRange(xRange=[-10, 110], yRange=[-10, 150])
        self.__graph.setLabel('left', 'tap deviation', units='σ', unitPrefix='')
        self.__graph.setLabel('bottom', 'note rhythm', units='%', unitPrefix='')
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


    def __get_deviation_data(self, score_data, diff_data):
        '''
        x-axis: note rhythm
        y-axis: deviation or mean
        color:  bpm

        Meant to be used on single play and not multiple plays
        '''
        if 0 in [ score_data.shape[0], diff_data.shape[0] ]:
            return np.asarray([ ])


        # Clear plots for redraw
        self.__graph.clearPlots()
        self.__text.setText(f'')

        score_data = score_data.groupby(['MD5', 'TIMESTAMP'])
        diff_data  = diff_data.groupby(['MD5', 'TIMESTAMP'])

        '''
        [   rhm  dev  avg_bpm
            [ ..., ..., ... ],
            ...
        ]
        '''
        data = []

        # For each map and timestamp
        for i, ((idx_score, df_score), (idx_diff, df_diff)) in enumerate(zip(score_data, diff_data)):
            rhythm      = df_diff['DIFF_T_PRESS_RHM'].values
            hit_offsets = df_score['T_HIT'].values - df_score['T_MAP'].values
            t_map       = df_score['T_MAP'].values

            # BPM needs to be calculated before filtering out notes
            bpm = 30000/np.diff(t_map)

            press_select = (df_score['TYPE_MAP'] == StdScoreData.ACTION_PRESS)
            hit_select   = (df_score['TYPE_HIT'] == StdScoreData.TYPE_HITP)
            miss_select  = (df_score['TYPE_HIT'] == StdScoreData.TYPE_MISS)

            num_notes   = np.count_nonzero(press_select & hit_select)
            num_misses  = np.count_nonzero(press_select & miss_select)

            hit_offsets = hit_offsets[press_select & hit_select]
            bpm = bpm[press_select[1:] & hit_select[1:]]

            new_hit_offsets = np.zeros(hit_offsets.shape[0] + 2*num_misses)
            new_hit_offsets[:hit_offsets.shape[0]] = hit_offsets
            new_hit_offsets[hit_offsets.shape[0] : hit_offsets.shape[0] + num_misses] = 100
            new_hit_offsets[hit_offsets.shape[0] + num_misses:] = -100

            data.append([ rhythm, np.std(new_hit_offsets), np.mean(bpm) ])

        return np.asarray(data)


    def plot_data(self, score_data, diff_data):
        dev_data = self.__get_deviation_data(score_data, diff_data)

        # Clear plots for redraw
        self.__graph.clearPlots()
        self.__text.setText(f'')

        if dev_data.shape[0] == 0:
            return

        # Round to nearest BPM so that cases like [ 136.01, 136.02 ]
        # don't spawn extra descrete BPM selections
        dev_data[:, 2] = np.round(dev_data[:, 2], 0)

        # Colored gradient r->g->b multiple plots at different angles
        unique_bpms = np.unique(dev_data[:, 2])

        bpm_lut = pyqtgraph.ColorMap(
            np.linspace(min(unique_bpms), max(unique_bpms), 3),
            np.array(
                [
                    [  0, 100, 255, 200],
                    [100, 255, 100, 200],
                    [255, 100, 100, 200],
                ]
            )
        )

        # Adds a plot for every unique BPM recorded
        for bpm in unique_bpms:
            # Determine data selected by angle
            data_select = (dev_data[:, 2] == bpm)
            if not any(data_select):
                # Selected region has no data. Nothing else to do
                continue

            # Plot data
            data_x = dev_data[data_select, 0]*dev_data[data_select, 2] / 30000
            data_y = dev_data[data_select, 1]
            color  = bpm_lut.map(dev_data[data_select, 2], pyqtgraph.ColorMap.QCOLOR)

            self.__graph.plot(x=data_x, y=(1 - data_y), pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=color, name=f'{bpm:.2f} bpm')
