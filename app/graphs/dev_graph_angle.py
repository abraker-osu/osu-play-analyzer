import pyqtgraph
from pyqtgraph.Qt import QtGui
import numpy as np


class DevGraphAngle(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.CS     = 0
        self.AR     = 1
        self.DT     = 2
        self.DT_INC = 3
        self.DT_DEC = 4
        self.DS     = 5
        self.ANGLE  = 6
        self.DEV_X  = 7
        self.DEV_Y  = 8
        self.DEV_T  = 9
        self.AVG_X  = 10
        self.AVG_Y  = 11
        self.AVG_T  = 12

        self.__dev_select = self.DEV_X
        self.__avg_data_points = True

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Aim dev-x (angle)')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLimits(xMin=-10, xMax=190, yMin=-10, yMax=200)
        self.__graph.setRange(xRange=[-10, 190], yRange=[-10, 20])
        self.__graph.setLabel('left', 'deviation', units='σ', unitPrefix='')
        self.__graph.setLabel('bottom', 'angle', units='deg', unitPrefix='')
        self.__graph.addLegend()

        # Deviation marker indicating expected deviation according to set CS
        self.__dev_marker_95 = pyqtgraph.InfiniteLine(angle=0, movable=False, pen=pyqtgraph.mkPen(color=(255, 100, 0, 100), style=pyqtgraph.QtCore.Qt.DashLine))
        self.__graph.addItem(self.__dev_marker_95, ignoreBounds=True)

        # Used to set text in legend item
        self.__label_style = pyqtgraph.PlotDataItem(pen=(0,0,0))
        self.__graph.getPlotItem().legend.addItem(self.__label_style, '')
        self.__text = self.__graph.getPlotItem().legend.getLabel(self.__label_style)

        # Put it all together
        self.__layout = QtGui.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)


    def plot_data(self, data):
        if data.shape[0] == 0:
            return

        # Clear plots for redraw
        self.__graph.clearPlots()

        bpm_data = 4*6000/data[:, self.DT]
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
            bpm_select = bpm_data == bpm
            angles = data[bpm_select, self.ANGLE]

            # Determine data selected by osu!px
            if self.__dev_select == self.DEV_X:
                self.__graph.setTitle('Aim dev-x (angle)')
                data_y = data[bpm_select, self.DEV_X]
            elif self.__dev_select == self.DEV_Y:
                self.__graph.setTitle('Aim dev-y (angle)')
                data_y = data[bpm_select, self.DEV_Y]
            elif self.__dev_select == self.DEV_T:
                self.__graph.setTitle('Aim dev-t (angle)')
                data_y = data[bpm_select, self.DEV_T]
            elif self.__dev_select == self.AVG_X:
                self.__graph.setTitle('Aim avg-x (bpm)')
                data_y = data[bpm_select, self.AVG_X]
            elif self.__dev_select == self.AVG_Y:
                self.__graph.setTitle('Aim avg-y (bpm)')
                data_y = data[bpm_select, self.AVG_Y]
            elif self.__dev_select == self.AVG_T:
                self.__graph.setTitle('Aim avg-t (bpm)')
                data_y = data[bpm_select, self.AVG_T]
                
            if self.__avg_data_points:
                # Use best N points for data display
                num_points = 10 # min(len(stdevs), self.MAX_NUM_DATA_POINTS)

                # Average overlapping data points (those that fall on same angle)
                data_y = np.asarray([ np.sort(data_y[angles == angle])[:num_points].mean() for angle in np.unique(angles) ])
                angles = np.unique(angles)

                # Get sort mapping to make points on line graph connect in proper order
                idx_sort = np.argsort(angles)
                data_x = angles[idx_sort]
                data_y = data_y[idx_sort]
            else:
                data_x = angles

            # Draw plot
            color = bpm_lut.map(bpm, 'qcolor')

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

            self.__graph.plot(x=data_x, y=data_y, symbol='o', symbolPen=None, symbolSize=5, pen=None, symbolBrush=color, name=f'{bpm:.2f} bpm')


    def set_dev(self, dev):
        self.__dev_marker_95.setPos(dev/4)
