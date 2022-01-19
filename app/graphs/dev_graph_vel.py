import pyqtgraph
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtCore

import math
import numpy as np


class DevGraphVel(QtGui.QWidget):

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
        self.__graph = pyqtgraph.PlotWidget(title='Aim dev-x (vel)')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLimits(xMin=0, xMax=5000, yMin=-10, yMax=200)
        self.__graph.setRange(xRange=[-10, 600], yRange=[-10, 20])
        self.__graph.setLabel('left', 'deviation', units='σ', unitPrefix='')
        self.__graph.setLabel('bottom', 'velocity', units='osu!px/ms', unitPrefix='')
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
        

    def plot_data(self, data):
        if data.shape[0] == 0:
            return

        # Clear plots for redraw
        self.__graph.clearPlots()
        self.__text.setText(f'')

        # Colored gradient r->g->b multiple plots at different angles
        unique_angs = np.unique(data[:, self.ANGLE])

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
            data_select = (data[:, self.ANGLE] == angle)
            if not any(data_select):
                # Selected region has no data. Nothing else to do
                continue

            # Extract relavent data
            if self.__dev_select == self.DEV_X:
                self.__graph.setTitle('Aim dev-x (vel)')
                stdevs = data[data_select, self.DEV_X]
            elif self.__dev_select == self.DEV_Y:
                self.__graph.setTitle('Aim dev-y (vel)')
                stdevs = data[data_select, self.DEV_Y]
            elif self.__dev_select == self.DEV_T:
                self.__graph.setTitle('Aim dev-t (vel)')
                stdevs = data[data_select, self.DEV_T]
            elif self.__dev_select == self.AVG_X:
                self.__graph.setTitle('Aim avg-x (bpm)')
                stdevs = data[data_select, self.AVG_X]
            elif self.__dev_select == self.AVG_Y:
                self.__graph.setTitle('Aim avg-y (bpm)')
                stdevs = data[data_select, self.AVG_Y]
            elif self.__dev_select == self.AVG_T:
                self.__graph.setTitle('Aim avg-t (bpm)')
                stdevs = data[data_select, self.AVG_T]

            pxs = data[data_select, self.DS]
            dt = data[data_select, self.DT]

            # Velocity
            vels = pxs/dt

            # Plot color
            color = angle_lut.map(angle, 'qcolor')

            self.__graph.plot(x=vels, y=stdevs, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=color, name=f'∠={angle:.2f}')

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
