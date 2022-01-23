import pyqtgraph
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtCore

import math
import numpy as np

from osu_analysis import StdScoreData
from app.data_recording.data import RecData


class DevGraphVel(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

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
        self.__graph = pyqtgraph.PlotWidget(title='Aim dev-x (vel)')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLimits(xMin=0, xMax=5000, yMin=-10, yMax=200)
        self.__graph.setRange(xRange=[-10, 600], yRange=[-10, 20])
        self.__graph.setLabel('left', 'aim deviation', units='σ', unitPrefix='')
        self.__graph.setLabel('bottom', 'velocity', units='osu!px/s', unitPrefix='')
        self.__graph.addLegend()

        # Deviation marker indicating expected deviation according to set CS
        self.__dev_marker_95 = pyqtgraph.InfiniteLine(angle=0, movable=False, pen=pyqtgraph.mkPen(color=(255, 100, 0, 100), style=pyqtgraph.QtCore.Qt.DashLine))
        self.__graph.addItem(self.__dev_marker_95, ignoreBounds=True)

        self.__vel_marker = pyqtgraph.InfiniteLine(angle=90, movable=False, pen=pyqtgraph.mkPen(color=(200, 200, 0, 100), style=pyqtgraph.QtCore.Qt.DashLine))
        self.__graph.addItem(self.__vel_marker, ignoreBounds=True)

        self.__dx = None
        self.__bpm = None

        # Used to set text in legend item
        self.__label_style = pyqtgraph.PlotDataItem(pen=(0,0,0))
        self.__graph.getPlotItem().legend.addItem(self.__label_style, '')
        self.__text = self.__graph.getPlotItem().legend.getLabel(self.__label_style)
   
        # Put it all together
        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)


    def __get_deviation_data(self, play_data):
        '''
        x-axis: velocity
        y-axis: deviation or mean
        color:  angle

        Meant to be used on single play and not multiple plays
        '''
        # Filters to get just hitcircles with valid hits
        data_filter = np.ones(play_data.shape[0], dtype=bool)

        # Filter out sliders
        data_filter[:-1] = \
            (play_data[:-1, RecData.ACT_TYPE] == StdScoreData.ACTION_PRESS) & ~(
                (play_data[1:, RecData.ACT_TYPE] == StdScoreData.ACTION_HOLD) | \
                (play_data[1:, RecData.ACT_TYPE] == StdScoreData.ACTION_RELEASE)
            )

        # Select hit presses
        data_filter &= (play_data[:, RecData.HIT_TYPE] == StdScoreData.TYPE_HITP)

        # Apply filter
        play_data = play_data[data_filter]

        # Gather relevant data
        data_c = play_data[:, RecData.ANGLE]
        data_x = 1000*play_data[:, RecData.DS]/play_data[:, RecData.DT]

        if self.__dev_data_select == self.DEV_DATA_X:
            data_y = play_data[:, RecData.X_OFFSETS]
        elif self.__dev_data_select == self.DEV_DATA_Y:
            data_y = play_data[:, RecData.Y_OFFSETS]
        elif self.__dev_data_select == self.DEV_DATA_T:
            data_y = play_data[:, RecData.T_OFFSETS]

        #            MIN    MAX   MIN DELTA
        chunks_c = [   0,   180,   15  ]     # Angle,    12 bins max
        chunks_x = [   0,  2000,   10  ]     # Velocty,  60 bins max

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

        # Filter out ones that don't have enough data
        dev_data = dev_data[dev_data[:, 0] != 0]

        return dev_data


    def plot_data(self, play_data):
        dev_data = self.__get_deviation_data(play_data)

        # Clear plots for redraw
        self.__graph.clearPlots()
        self.__text.setText(f'')

        if dev_data.shape[0] == 0:
            return

        # Colored gradient r->g->b multiple plots at different angles
        unique_angs = np.unique(dev_data[:, 2])

        angle_lut = pyqtgraph.ColorMap(
            np.linspace(min(unique_angs), max(unique_angs), 3),
            np.array(
                [
                    [  0, 100, 255, 200],
                    [100, 255, 100, 200],
                    [255, 100, 100, 200],
                ]
            )
        )

        # Adds a plot for every unique BPM recorded
        for angle in unique_angs:
            # Determine data selected by angle
            data_select = (dev_data[:, 2] == angle)
            if not any(data_select):
                # Selected region has no data. Nothing else to do
                continue

            data_y = dev_data[data_select, 0]
            data_x = dev_data[data_select, 1]

            if self.__avg_data_points:
                # Use best N points for data display
                num_points = 10 # min(len(data_y), self.MAX_NUM_DATA_POINTS)

                # Average overlapping data points (those that fall on same velocity)
                data_y = np.asarray([ np.sort(data_y[data_x == x])[:num_points].mean() for x in np.unique(data_x) ])
                unique_data_x = np.unique(data_x)

                # Get sort mapping to make points on line graph connect in proper order
                idx_sort = np.argsort(unique_data_x)
                data_x = unique_data_x[idx_sort]
                data_y = data_y[idx_sort]

            # Plot color
            color = angle_lut.map(angle, 'qcolor')

            self.__graph.plot(x=data_x, y=data_y, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=color, name=f'∠={angle:.2f}')

            '''
            # Calc linear regression
            m, b = MathUtils.linear_regresion(vels, stdevs)
            if type(m) == type(None) or type(b) == type(None):
                self.__graph.plot(x=vels, y=stdevs, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=color)
                continue

            y_model = m*vels + b                # model: y = mx + b
            x_model = (stdevs - b)/m            # model: x = (y - b)/m

            m_dev_y = np.std(stdevs - y_model)  # deviation of y from model
            m_dev_x = np.std(vels - x_model)    # deviation of x from model

            x_mean = np.mean(vels)

            if m_dev_x == 0:
                self.__graph.plot(x=vels, y=stdevs, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=color, name=label)
                continue

            # Standard error of slope @ 95% confidence interval
            m_se_95 = (m_dev_y/m_dev_x)/math.sqrt(stdevs.shape[0] - 2)*1.96

            # Standard error of y-intercept @ 95% confidence interval
            b_se_95 = 2*m_se_95*x_mean

            label = f'∠={angle:.2f}  n={stdevs.shape[0]}  σ={m_dev_y:.2f}  m={m:.5f}±{m_se_95:.5f}  b={b:.2f}±{b_se_95:.2f}'
            print(label)

            if self.model_compensation:
                self.__graph.plot(x=vels, y=stdevs - y_model, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=color, name=label)
                self.__graph.plot(x=[0, max(vels)], y=[0, 0], pen=(100, 100, 0, 150))
            else:
                self.__graph.plot(x=vels, y=stdevs, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=color, name=label)
                self.__graph.plot(x=[0, max(vels)], y=[b, m*max(vels) + b], pen=(100, 100, 0, 150))
            '''


    def set_dev(self, dev):
        self.__dev_marker_95.setPos(dev/4)


    def update_vel(self, dx=None, bpm=None):
        if type(dx) != type(None):
            self.__dx = dx

        if type(bpm) != type(None):
            self.__bpm = bpm

        if type(self.__dx) != type(None) and type(self.__bpm) != type(None):
            self.__vel_marker.setPos(self.__dx*self.__bpm/60)
