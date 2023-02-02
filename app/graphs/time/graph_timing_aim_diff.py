import threading

import PyQt5
import pyqtgraph

import numpy as np

from osu_analysis import StdScoreData

from app.misc.osu_utils import OsuUtils
from app.misc.utils import Utils
from app.widgets.bar_plot import BarGraphItem



class GraphTimeAimDifficulty(PyQt5.QtWidgets.QWidget):

    time_changed_event = PyQt5.QtCore.pyqtSignal(object)

    __calc_data_event = PyQt5.QtCore.pyqtSignal(object, object, object)

    def __init__(self, parent=None):
        PyQt5.QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Time vs Aim difficulty graph')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(xMin=-10, xMax=5000, yMin=-200, yMax=200)
        self.__graph.setRange(xRange=[-10, 300], yRange=[-200, 200])
        self.__graph.setLabel('bottom', 'Time', units='ms', unitPrefix='')
        self.__graph.setLabel('left', 'Aim factor', units='', unitPrefix='')
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

        # Selects release points for short sliders. These kind of sliders
        # do not have any consequences for not aiming the slider end. As a
        # result, it is not a significant aiming challenge if they go very 
        # fast. Sliders are considered short when they have no hold scorepoints.
        short_slider_rel_select = np.zeros(score_data.shape[0], dtype=np.bool8)
        short_slider_rel_select[1:] = (
            (type_map[:-1] == StdScoreData.ACTION_PRESS) & 
            (type_map[1:] == StdScoreData.ACTION_RELEASE)
        )

        # For now selects press points for short sliders. Sliders are considered 
        # short when they have no hold scorepoints.
        #
        # Slider paths oriented in the direction of jump effectively have their 
        # CS artificially increased by at least 1.5x (due to follow circle size).
        # Can be a bit more if slider velocity and path is right.
        #
        # TODO: How to determine if slider path is oriented in the direction of jump?
        # TODO: What if slider path goes into opposite direction of jump?
        short_slider_prs_select = np.zeros(score_data.shape[0], dtype=np.bool8)
        short_slider_prs_select[:-1] = (
            (type_map[:-1] == StdScoreData.ACTION_PRESS) & 
            (type_map[1:] == StdScoreData.ACTION_RELEASE)
        )

        score_data = score_data[~short_slider_rel_select]
        diff_data  = diff_data[~short_slider_rel_select]

        short_slider_prs_select = short_slider_prs_select[~short_slider_rel_select]
        type_map = type_map[~short_slider_rel_select]

        cs_px = OsuUtils.cs_to_px(score_data['CS'].values[0])
        dists = diff_data['DIFF_XY_DIST'].values

        # Small distance do not require to reposition the cursor to aim the next
        # note. As a result patters like double taps can have very short timing
        # between them while being offset by some amount, resulting in high 
        # velocities. Distances are considered small if the scorepoints are less
        # than 75% the diameter of circle size apart.
        #
        # NOTE: This doesn't work for streams or large stacks as they have multiple 
        # successions of small distances, effectively requiring the player to move 
        # the cursor. Perhaps look into implementing a strategy that decides whether
        # velocity is too large for notes that are closely spaced.
        small_small_dist_select = (dists < cs_px*1.5)

        # Calculate data (x2 is considered current score point, x1 and x0 are previous score points)
        x_map  = score_data['X_MAP'].values
        y_map  = score_data['Y_MAP'].values
        t_map  = score_data['T_MAP'].values
        vels   = diff_data['DIFF_XY_LIN_VEL'].values
        angles = diff_data['DIFF_XY_ANGLE'].values

        is_miss = (
            (score_data['TYPE_HIT'].values == StdScoreData.TYPE_MISS) & (
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
                hit_type: {score_data['TYPE_HIT'].values[1:-1][detected_zeros]} {score_data['TYPE_HIT'].values[2:][detected_zeros]}
                action_type: {score_data['TYPE_MAP'].values[1:-1][detected_zeros]} {score_data['TYPE_MAP'].values[2:][detected_zeros]}
                """
            )

        angle_factor = (1 + 2.5*np.exp(-0.026*angles))/(1 + 2.5)
        cs_factor = np.full_like(angle_factor, OsuUtils.cs_to_px(4)/cs_px)
        cs_factor[short_slider_prs_select] = (OsuUtils.cs_to_px(4)/(1.5*cs_px))

        data_y = (cs_factor*vels*angle_factor*4)
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
