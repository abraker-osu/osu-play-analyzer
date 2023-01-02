from PyQt5 import QtWidgets
import pyqtgraph

import math
import numpy as np

from osu_analysis import StdScoreData
from app.misc.osu_utils import OsuUtils
from app.misc.utils import MathUtils


class DevGraphAR(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='AR dev-t (vel)')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLimits(xMin=0, xMax=5000, yMin=-10, yMax=200)
        self.__graph.setRange(xRange=[-10, 600], yRange=[-10, 20])
        self.__graph.setLabel('left', 'tap deviation', units='σ', unitPrefix='')
        self.__graph.setLabel('bottom', 'AR', units='ms', unitPrefix='')
        self.__graph.addLegend()

        # Deviation marker indicating expected deviation according to set CS
        self.__dev_marker_95 = pyqtgraph.InfiniteLine(angle=0, movable=False, pen=pyqtgraph.mkPen(color=(255, 100, 0, 100), style=pyqtgraph.QtCore.Qt.DashLine))
        self.__graph.addItem(self.__dev_marker_95, ignoreBounds=True)

        self.__vel_marker = pyqtgraph.InfiniteLine(angle=90, movable=False, pen=pyqtgraph.mkPen(color=(200, 200, 0, 100), style=pyqtgraph.QtCore.Qt.DashLine))
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
            return

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

            hit_offsets = df_score['T_HIT'].values - df_score['T_MAP'].values
            t_map       = df_score['T_MAP'].values

            # BPM needs to be calculated before filtering out notes
            bpm = 30000/np.diff(t_map)

            press_select = (df_score['TYPE_MAP'] == StdScoreData.ACTION_PRESS)
            hit_select   = (df_score['TYPE_HIT'] == StdScoreData.TYPE_HITP)
            
            num_notes   = np.count_nonzero(press_select & hit_select)
            hit_offsets = hit_offsets[press_select & hit_select]
            bpm = bpm[press_select[1:] & hit_select[1:]]

            data.append([ ar_ms, np.std(hit_offsets), np.mean(bpm) ])

        return np.asarray(data)


    def plot_data(self, score_data, diff_data):
        dev_data = self.__get_deviation_data(score_data, diff_data)

        # Clear plots for redraw
        self.__graph.clearPlots()
        self.__text.setText(f'')

        if dev_data.shape[0] == 0:
            return

        # # Colored gradient r->g->b multiple plots at different angles
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

            data_x = dev_data[data_select, 0]
            data_y = dev_data[data_select, 1]
            color = bpm_lut.map(bpm, 'qcolor')

            self.__graph.plot(x=data_x, y=data_y, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=color, name=f'{bpm:.2f} bpm')

            # Calc linear regression
            m, b = MathUtils.linear_regresion(data_x, data_y)
            if type(m) == type(None) or type(b) == type(None):
                continue

            y_model = m*data_x + b              # model: y = mx + b
            x_model = (data_y - b)/m            # model: x = (y - b)/m

            m_dev_x = np.std(data_x - x_model)  # deviation of x from model
            m_dev_y = np.std(data_y - y_model)  # deviation of y from model

            x_mean = np.mean(data_x)

            # Standard error of slope @ 95% confidence interval
            m_se_95 = (m_dev_y/m_dev_x)/math.sqrt(data_x.shape[0] - 2)*1.96

            # Standard error of y-intercept @ 95% confidence interval
            b_se_95 = 2*m_se_95*x_mean

            label = f'bpm={bpm:.2f}  n={data_x.shape[0]}  σ={m_dev_y:.2f}  m={m:.5f}±{m_se_95:.5f}  b={b:.2f}±{b_se_95:.2f}'
            print(label)

            self.__graph.plot(x=[0, max(data_x)], y=[b, m*max(data_x) + b], pen=pyqtgraph.mkPen(width=4, color=color), name=f'{bpm:.2f} bpm')

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
