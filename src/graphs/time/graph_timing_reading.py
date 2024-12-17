import threading

import PyQt5
import pyqtgraph

import numpy as np

from osu_analysis import StdScoreData

from misc.osu_utils import OsuUtils
from misc.utils import Utils
from widgets.bar_plot import BarGraphItem



class GraphTimeReadingDifficulty(PyQt5.QtWidgets.QWidget):

    time_changed_event = PyQt5.QtCore.pyqtSignal(object)

    __calc_data_event = PyQt5.QtCore.pyqtSignal(object, object, object)

    def __init__(self, parent=None):
        PyQt5.QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Time vs Reading difficulty graph')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=-10, xMax=5000, yMin=-200, yMax=200)
        self.__graph.setRange(xRange=[-10, 300], yRange=[-200, 200])
        self.__graph.setLabel('bottom', 'Time', units='ms', unitPrefix='')
        self.__graph.setLabel('left', 'Reading factor', units='', unitPrefix='')
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
        self.__layout = PyQt5.QtWidgets.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)

        self.__calc_data_event.connect(self.__display_data)


    def set_time(self, time):
        self.timeline_marker.blockSignals(True)
        self.timeline_marker.setValue(time)
        self.timeline_marker.blockSignals(False)


    def plot_data(self, score_data, diff_data):
        if 0 in [ score_data.shape[0], diff_data.shape[0] ]:
            return

        thread = threading.Thread(target=self.__calc_aim_factors, args=(score_data, diff_data))
        thread.start()


    @Utils.benchmark(f'[ Threaded ] {__name__}')
    def __calc_aim_factors(self, score_data, diff_data):
        # Check if there is any data to operate on
        if score_data.shape[0] < 3:
            data_stub = np.asarray([])
            self.__calc_data_event.emit(data_stub, data_stub, data_stub)
            return

        type_map = score_data['TYPE_MAP'].values
        type_hit = score_data['TYPE_HIT'].values

        # Calculate data (x2 is considered current score point, x1 and x0 are previous score points)
        x_map  = score_data['X_MAP'].values
        y_map  = score_data['Y_MAP'].values
        t_map  = score_data['T_MAP'].values

        num_visible = diff_data['DIFF_VIS_VISIBLE'].values
        bpm         = 15000/diff_data['DIFF_T_PRESS_DIFF'].values

        is_miss = (
            (type_hit == StdScoreData.TYPE_MISS) & (
                (type_map == StdScoreData.ACTION_HOLD) |
                (type_map == StdScoreData.ACTION_PRESS)
            )
        )

        detected_zeros = t_map[2:] == t_map[1:-1]
        if np.count_nonzero(detected_zeros) > 0:
            print(
                f"""
                Warning: Detected zeros in timing data:
                pos_x: {x_map[1:-1][detected_zeros]} {x_map[2:][detected_zeros]}
                pos_y: {y_map[1:-1][detected_zeros]} {y_map[2:][detected_zeros]}
                timing: {t_map[1:-1][detected_zeros]} {t_map[2:][detected_zeros]}
                hit_type: {type_hit[1:-1][detected_zeros]} {type_hit[2:][detected_zeros]}
                action_type: {type_map[1:-1][detected_zeros]} {type_map[2:][detected_zeros]}
                """
            )

        data_y = num_visible*bpm
        inv_filter = ~np.isnan(data_y)

        data_y = data_y[inv_filter]
        data_x = t_map[inv_filter]
        is_miss = is_miss[inv_filter]

        #print(f'velocity spike: {velocities[timing[2:] == 31126]}')
        #print(f'velocity end: {velocities[timing[2:] == 88531]}')

        #print(f'angle spike: {angles[timing[2:] == 31126]}')
        #print(f'angle end: {angles[timing[2:] == 88531]}')

        #print(f'angle factor spike: {angle_factor[timing[2:] == 31126]}')
        #print(f'angle factor end: {angle_factor[timing[2:] == 88531]}')

        self.__calc_data_event.emit(data_x, data_y, is_miss)


    def __display_data(self, data_x, data_y, is_miss):
        colors = list([
            [ 200, 0, 0, 100 ] if miss else [ 200, 200, 200, 100 ]
            for miss in is_miss
        ])

        width = np.zeros(data_x.shape)
        width[:-1] = np.diff(data_x)*0.99
        width[-1] = width[-2]

        self.__plot.setData(x=data_x, y=data_y, width=width, brush=colors)
        self.__graph.setRange(xRange=[ np.min(data_x), np.max(data_x) ])
