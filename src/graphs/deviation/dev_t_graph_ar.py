from PyQt6 import QtCore
from PyQt6 import QtWidgets
import pyqtgraph

import numpy as np
from scipy.optimize import curve_fit

from osu_analysis import StdScoreData
from misc.osu_utils import OsuUtils
from misc.utils import MathUtils


class DevTGraphAR(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        # Make sure StdScoreData.Settings valid range window is set to [100, 100] for this to be accurate
        self.__VALID_RANGE_WIN = 200  # ms

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='AR dev-t')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=0, xMax=5000, yMin=-10, yMax=200)
        self.__graph.setRange(xRange=[-0.1, 20], yRange=[-0.1, 1.1])
        self.__graph.setLabel('left', 'Tap deviation', units='2σ ms % of 200ms', unitPrefix='')
        self.__graph.setLabel('bottom', 'Density', units='# note visible', unitPrefix='')
        self.__graph.addLegend()

        # Stats
        self.__graph_text = pyqtgraph.TextItem('', anchor=(0, 0), )
        self.__graph.addItem(self.__graph_text)

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

            data.append([ ar_ms, np.std(new_hit_offsets), np.mean(bpm) ])

        return np.asarray(data)


    def plot_data(self, score_data, diff_data):
        dev_data = self.__get_deviation_data(score_data, diff_data)

        # Clear plots for redraw
        self.__graph.clearPlots()
        self.__text.setText(f'')
        self.__graph_text.setText('')

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
            data_y = 2*dev_data[data_select, 1] / self.__VALID_RANGE_WIN
            color  = bpm_lut.map(dev_data[data_select, 2], pyqtgraph.ColorMap.QCOLOR)

            self.__graph.plot(x=data_x, y=(1 - data_y), pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=color, name=f'{bpm:.2f} bpm')

            if data_x.shape[0] < 4:
                # Filter out incomplete data
                continue

        # Plot model
        data_x = dev_data[:, 0]*dev_data[:, 2] / 30000
        data_y = 2*dev_data[:, 1] / self.__VALID_RANGE_WIN

        idx_sort = np.argsort(data_x)
        data_x = data_x[idx_sort]
        data_y = data_y[idx_sort]

        data_x = np.append(data_x, np.asarray([15, 16, 17, 18, 19, 20]).repeat(10))
        data_y = np.append(data_y, np.asarray([ 1,  1,  1,  1,  1,  1]).repeat(10))

        self.__graph.plot(x=data_x, y=(1 - data_y), pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=pyqtgraph.mkColor(255, 255, 0), name=f'test')

        try: fit_params, _ = curve_fit(MathUtils.sigmoid, data_x, data_y, method='dogbox', maxfev=5000)
        except RuntimeError as e:
            return

        s_x, s_y, o_x, o_y = fit_params

        fit_x = np.linspace(0, 20, 100)
        fit_y = MathUtils.sigmoid(fit_x, s_x, s_y, o_x, o_y)

        self.__graph.plot(x=fit_x, y=(1 - fit_y), pen=pyqtgraph.mkPen(width=2, color=pyqtgraph.mkColor(255, 255, 0)), name=f'model')
        self.__graph_text.setText(self.__graph_text.textItem.toPlainText() + f'g_sx: {s_x:.4f}  |  g_sy: {s_y:.4f}  |  g_ox: {o_x:.2f} notes  |  g_oy: {1 - o_y:.2f}\n')

        #self.__text.setText()


    def set_dev(self, dev):
        self.__dev_marker_95.setPos(dev/4)


    def update_vel(self, dx=None, bpm=None):
        if type(dx) != type(None):
            self.__dx = dx

        if type(bpm) != type(None):
            self.__bpm = bpm

        if type(self.__dx) != type(None) and type(self.__bpm) != type(None):
            self.__vel_marker.setPos(self.__dx*self.__bpm/60)
