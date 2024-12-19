from PyQt6 import QtCore
from PyQt6 import QtWidgets

import pyqtgraph
import numpy as np

from osu_analysis import StdScoreData
from data_recording.data import ScoreNpyData



class DevGraphAngle(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.DEV_DATA_X = 0
        self.DEV_DATA_Y = 1
        self.DEV_DATA_T = 2

        self.DEV_TYPE_AVG = 0
        self.DEV_TYPE_DEV = 1

        self.NEEDED_NUM_DATA_POINTS = 30

        self.__dev_data_select = self.DEV_DATA_X
        self.__dev_type_select = self.DEV_TYPE_DEV
        self.__avg_data_points = True

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Aim dev-x (angle)')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLimits(xMin=-10, xMax=190, yMin=-10, yMax=200)
        self.__graph.setRange(xRange=[-10, 190], yRange=[-10, 20])
        self.__graph.setLabel('left', 'deviation (averaged)', units='σ', unitPrefix='')
        self.__graph.setLabel('bottom', 'angle', units='deg', unitPrefix='')
        self.__graph.addLegend()

        # Deviation marker indicating expected deviation according to set CS
        self.__dev_marker_95 = pyqtgraph.InfiniteLine(angle=0, movable=False, pen=pyqtgraph.mkPen(color=(255, 100, 0, 100), style=QtCore.Qt.PenStyle.DashLine))
        self.__graph.addItem(self.__dev_marker_95, ignoreBounds=True)

        # Used to set text in legend item
        self.__label_style = pyqtgraph.PlotDataItem(pen=(0,0,0))
        self.__graph.getPlotItem().legend.addItem(self.__label_style, '')
        self.__text = self.__graph.getPlotItem().legend.getLabel(self.__label_style)

        # Put it all together
        self.__layout = QtWidgets.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)


    def __get_deviation_data(self, play_data):
        '''
        x-axis: angles
        y-axis: deviation or mean
        color:  bpm

        Meant to be used on single play and not multiple plays
        '''
        # Filters to get just hitcircles with valid hits
        data_filter = np.ones(play_data.shape[0], dtype=np.bool8)

        # Filter out sliders
        data_filter[:-1] = \
            (play_data[:-1, ScoreNpyData.ACT_TYPE] == StdScoreData.ACTION_PRESS) & ~(
                (play_data[1:, ScoreNpyData.ACT_TYPE] == StdScoreData.ACTION_HOLD) | \
                (play_data[1:, ScoreNpyData.ACT_TYPE] == StdScoreData.ACTION_RELEASE)
            )

        # Select hit presses
        data_filter &= (play_data[:, ScoreNpyData.HIT_TYPE] == StdScoreData.TYPE_HITP)

        # Apply filter
        play_data = play_data[data_filter]

        # Gather relevant data
        data_c = 15000/play_data[:, ScoreNpyData.DT]
        data_x = play_data[:, ScoreNpyData.ANGLE]

        if self.__dev_data_select == self.DEV_DATA_X:
            data_y = play_data[:, ScoreNpyData.X_OFFSETS]
        elif self.__dev_data_select == self.DEV_DATA_Y:
            data_y = play_data[:, ScoreNpyData.Y_OFFSETS]
        elif self.__dev_data_select == self.DEV_DATA_T:
            data_y = play_data[:, ScoreNpyData.T_OFFSETS]

        #            MIN    MAX   MIN DELTA
        chunks_c = [   0,   400,   20  ]      # BPM,    20 bins max
        chunks_x = [   0,   180,   3   ]      # Angle,  60 bins max

        # Filter out data outside the range
        range_filter = \
            (chunks_c[0] <= data_c) & (data_c <= chunks_c[1]) & \
            (chunks_x[0] <= data_x) & (data_x <= chunks_x[1])

        data_c = data_c[range_filter]
        data_x = data_x[range_filter]
        data_y = data_y[range_filter]

        # Reduce data to bins
        num_bins_c = (chunks_c[1] - chunks_c[0])//chunks_c[2]
        num_bins_x = (chunks_x[1] - chunks_x[0])//chunks_x[2]

        dev_data_c = np.linspace(chunks_c[0], chunks_c[1], num_bins_c)
        dev_data_x = np.linspace(chunks_x[0], chunks_x[1], num_bins_x)

        idx_data_c = np.digitize(data_c, dev_data_c) - 1
        idx_data_x = np.digitize(data_x, dev_data_x) - 1

        c_unique_idxs = np.unique(idx_data_c)
        x_unique_idxs = np.unique(idx_data_x)

        dev_data = np.zeros((c_unique_idxs.shape[0]*x_unique_idxs.shape[0], 3), dtype=float)

        for c_idx in range(c_unique_idxs.shape[0]):
            for x_idx in range(x_unique_idxs.shape[0]):
                data_select = (idx_data_c == c_unique_idxs[c_idx]) & (idx_data_x == x_unique_idxs[x_idx])
                if np.sum(data_select) < self.NEEDED_NUM_DATA_POINTS:
                    continue

                if self.__dev_type_select == self.DEV_TYPE_AVG:
                    dev_data_y = np.mean(data_y[data_select])
                elif self.__dev_type_select == self.DEV_TYPE_DEV:
                    dev_data_y = np.std(data_y[data_select])
                else:
                    print('Unknown deviation type')
                    return

                idx_dev_data = c_idx*x_unique_idxs.shape[0] + x_idx
                dev_data[idx_dev_data, 0] = dev_data_y
                dev_data[idx_dev_data, 1] = dev_data_x[x_unique_idxs[x_idx]]
                dev_data[idx_dev_data, 2] = dev_data_c[c_unique_idxs[c_idx]]

        return dev_data


    def plot_data(self, play_data):
        dev_data = self.__get_deviation_data(play_data)

        # Clear plots for redraw
        self.__graph.clearPlots()

        if dev_data.shape[0] == 0:
            return

        bpm_data = dev_data[:, 2]
        unique_bpms = np.unique(bpm_data)

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

        # Main plot - deviation vs osu!px
        # Adds a plot for every unique BPM recorded
        for bpm in unique_bpms:
            data_select = (bpm_data == bpm)
            if not any(data_select):
                # Selected region has no data. Nothing else to do
                continue

            data_y = dev_data[data_select, 0]
            data_x = dev_data[data_select, 1]

            if self.__avg_data_points:
                # Average overlapping data points (those that fall on same angle)
                data_y = np.asarray([ np.sort(data_y[data_x == x]).mean() for x in np.unique(data_x) ])
                unique_data_x = np.unique(data_x)

                # Get sort mapping to make points on line graph connect in proper order
                idx_sort = np.argsort(unique_data_x)
                data_x = unique_data_x[idx_sort]
                data_y = data_y[idx_sort]

            # Plot color
            color = bpm_lut.map(bpm, 'qcolor')

            self.__graph.plot(x=data_x, y=data_y, symbol='o', symbolPen=None, symbolSize=5, pen=None, symbolBrush=color, name=f'{bpm:.2f} bpm')

            '''
            m, b = MathUtils.linear_regresion(angles, stdevs)
            if type(m) == type(None) or type(b) == type(None):
                self.__graph.plot(x=angles, y=stdevs, symbol='o', symbolPen=None, symbolSize=5, pen=None, symbolBrush=color, name=f'{bpm} bpm')
                continue

            if self.model_compensation:
                y_model = m*angles + b
                self.__graph.plot(x=angles, y=stdevs - y_model, symbol='o', symbolPen=None, symbolSize=5, pen=None, symbolBrush=color, name=f'{bpm} bpm   σ = {np.std(stdevs - y_model):.2f}  m={m:.5f}  b={b:.2f}')
            else:
                self.__graph.plot(x=angles, y=stdevs, symbol='o', symbolPen=None, symbolSize=5, pen=None, symbolBrush=color, name=f'{bpm:.0f} bpm')
            '''


    def set_dev(self, dev):
        self.__dev_marker_95.setPos(dev/4)
