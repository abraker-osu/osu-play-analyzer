import PyQt6
import pyqtgraph

import numpy as np

from widgets.bar_plot import BarGraphItem
from misc.utils import Utils


class GraphTimingVisibleAR(PyQt6.QtWidgets.QWidget):

    time_changed_event = PyQt6.QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        PyQt6.QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Time vs Number objects visible per AR period')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=-10, xMax=5000, yMin=-200, yMax=200)
        self.__graph.setRange(xRange=[-1, 10], yRange=[-200, 200])
        self.__graph.setLabel('bottom', 'Time', units='ms', unitPrefix='')
        self.__graph.setLabel('left', 'Number objects visible per AR period', units='s', unitPrefix='')
        self.__graph.addLegend()

        # Used to set text in legend item
        self.__label_style = pyqtgraph.PlotDataItem(pen=(0,0,0))
        self.__graph.getPlotItem().legend.addItem(self.__label_style, '')
        self.__text = self.__graph.getPlotItem().legend.getLabel(self.__label_style)

        # Add bar graph item
        self.__plot = BarGraphItem()
        self.__graph.getPlotItem().addItem(self.__plot, '')

        # Add timeline marker
        self.timeline_marker = pyqtgraph.InfiniteLine(angle=90, movable=True)
        self.timeline_marker.setBounds((-10000, None))
        self.timeline_marker.sigPositionChanged.connect(lambda obj: self.time_changed_event.emit(obj.value()))
        self.__graph.getPlotItem().addItem(self.timeline_marker, ignoreBounds=True)

        # Put it all together
        self.__layout = PyQt6.QtWidgets.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)


    def set_time(self, time):
        self.timeline_marker.blockSignals(True)
        self.timeline_marker.setValue(time)
        self.timeline_marker.blockSignals(False)


    @Utils.benchmark(f'{__name__}')
    def plot_data(self, score_data, diff_data):
        unique_md5s = np.unique(diff_data.index.get_level_values(0))
        if unique_md5s.shape[0] == 0:
            print('Error: No maps are selected')
            return

        if np.unique(diff_data.index.get_level_values(1)).shape[0] > 1:
            print('Warning: multiple maps are selected. Taking just the first one...')

        score_data = list(score_data.groupby(['MD5', 'TIMESTAMP', 'MODS']))[0][1]
        diff_data  = list(diff_data.groupby(['MD5', 'TIMESTAMP', 'MODS']))[0][1]

        x_data = np.asarray(score_data['T_MAP'])
        y_data = np.asarray(diff_data['DIFF_VIS_VISIBLE_AR'])

        # Clear plots for redraw
        #self.__graph.clearPlots()
        self.__text.setText(f'')

        colors = [ [ 255, 0, 0, 150 ] ]

        width = np.zeros(x_data.shape)
        width[:-1] = np.diff(x_data)*0.99
        width[-1] = width[-2]

        self.__plot.setData(x=x_data, y=y_data, width=width, brush=colors)
