from PyQt6 import QtCore
from PyQt6 import QtWidgets
import pyqtgraph

import math
import numpy as np

from osu_analysis import StdScoreData
from misc.osu_utils import OsuUtils
from misc.utils import MathUtils


class DevXYGraphAR(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='AR dev-xy')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=0, xMax=5000, yMin=-10, yMax=200)
        self.__graph.setRange(xRange=[-10, 600], yRange=[-10, 20])
        self.__graph.setLabel('left', 'Aim deviation', units='1σ px', unitPrefix='')
        self.__graph.setLabel('bottom', 'Density', units='# note visible', unitPrefix='')
        self.__graph.addLegend()

        # Deviation marker indicating expected deviation according to set CS
        self.__dev_marker_95 = pyqtgraph.InfiniteLine(angle=0, movable=False, pen=pyqtgraph.mkPen(color=(255, 100, 0, 100), style=QtCore.Qt.PenStyle.DashLine))
        self.__graph.addItem(self.__dev_marker_95, ignoreBounds=True)

        self.__vel_marker = pyqtgraph.InfiniteLine(angle=90, movable=False, pen=pyqtgraph.mkPen(color=(200, 200, 0, 100), style=QtCore.Qt.PenStyle.DashLine))
        self.__graph.addItem(self.__vel_marker, ignoreBounds=True)

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
        x-axis: ar_ms
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
        [   ar_ms  dev  avg_bpm
            [ ..., ..., ... ],
            ...
        ]
        '''
        data = []

        # For each map and timestamp
        for i, ((idx_score, df_score), (idx_diff, df_diff)) in enumerate(zip(score_data, diff_data)):
            ar_ms       = OsuUtils.ar_to_ms(df_score['AR'].values[0])
            #ar_ms = df_diff['DIFF_VIS_VISIBLE'].values[0]

            hit_offsets = df_score['X_HIT'].values - df_score['X_MAP'].values
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
            new_hit_offsets[hit_offsets.shape[0] : hit_offsets.shape[0] + num_misses] = 2*OsuUtils.cs_to_px(df_score['CS'].values[0])
            new_hit_offsets[hit_offsets.shape[0] + num_misses:] = -2*OsuUtils.cs_to_px(df_score['CS'].values[0])

            data.append([ ar_ms, np.std(new_hit_offsets), np.mean(bpm) ])

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

            data_x = dev_data[data_select, 0]*dev_data[data_select, 2] / 30000
            data_y = dev_data[data_select, 1]
            color  = bpm_lut.map(dev_data[data_select, 2], 'qcolor')

            self.__graph.plot(x=data_x, y=data_y, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=color, name=f'{bpm:.2f} bpm')

            # Calc exponential regression
            try:
                a, b, c = MathUtils.exp_regression(data_x, data_y)
                if isinstance(type(None), ( type(a), type(b), type(c) )):
                     continue
            except np.linalg.LinAlgError:
                continue

            # The curve behaves as 1/x, so invert it
            # to perform a linear regression. The resultant
            # regresion will then be inverted back to match
            # the data
            data_y = 1/data_y

            # Calc linear regression
            m, b = MathUtils.linear_regresion(data_x, data_y)
            if type(m) == type(None) or type(b) == type(None):
                continue

            # y_model = m*data_x + b              # model: y = mx + b
            # x_model = (data_y - b)/m            # model: x = (y - b)/m

            # m_dev_x = np.std(data_x - x_model)  # deviation of x from model
            # m_dev_y = np.std(data_y - y_model)  # deviation of y from model

            # x_mean  = np.mean(data_x)

            # # Standard error of slope @ 95% confidence interval
            # m_se_95 = (m_dev_y/m_dev_x)/math.sqrt(data_x.shape[0] - 2)*1.96

            # # Standard error of y-intercept @ 95% confidence interval
            # b_se_95 = 2*m_se_95*x_mean

            # label = f'bpm={bpm:.2f}  n={data_x.shape[0]}  σ={m_dev_y:.2f}  m={m:.5f}±{m_se_95:.5f}  b={b:.2f}±{b_se_95:.2f}'
            # print(label)

            data_x = np.linspace(0, max(data_x), 20)
            data_y = 1/(m*data_x + b)  # Invert the regression back
            #data_y = a + b*np.exp(c * data_x)

            color  = bpm_lut.map(bpm, 'qcolor')

            self.__graph.plot(x=data_x, y=data_y, pen=pyqtgraph.mkPen(width=4, color=color), name=f'{bpm:.2f} bpm')

        #self.__text.setText(label)


    def set_dev(self, dev):
        self.__dev_marker_95.setPos(dev/4)


    def update_vel(self, dx=None, bpm=None):
        if type(dx) != type(None):
            self.__dx = dx

        if type(bpm) != type(None):
            self.__bpm = bpm

        if type(self.__dx) != type(None) and type(self.__bpm) != type(None):
            self.__vel_marker.setPos(self.__dx*self.__bpm/60)
