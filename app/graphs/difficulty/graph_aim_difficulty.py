import numpy as np
import threading
import math

import PyQt5
import pyqtgraph
from pyqtgraph.functions import mkPen

from osu_analysis import StdScoreData

from app.misc.osu_utils import OsuUtils
from app.misc.utils import Utils


class GraphAimDifficulty(PyQt5.QtWidgets.QWidget):

    __calc_data_event = PyQt5.QtCore.pyqtSignal(object, object, object)

    def __init__(self, parent=None):
        PyQt5.QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Aim difficulty graph')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        #self.__graph.setLimits(yMin=-1, yMax=12)
        self.__graph.setRange(xRange=[-0.1, 1.1], yRange=[-1, 5])
        self.__graph.setLabel('left', 'Aim factor', units='', unitPrefix='')
        self.__graph.setLabel('bottom', 'Factors', units='%', unitPrefix='')
        self.__graph.addLegend()

        self.__diff_plot_hit = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__diff_plot_hit)

        self.__diff_plot_miss = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__diff_plot_miss)

        # Stats
        self.__graph_text = pyqtgraph.TextItem('', anchor=(0, 0), )
        self.__graph.addItem(self.__graph_text)

        # Put it all together
        self.__layout = PyQt5.QtWidgets.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)

        # Connect signals
        self.__calc_data_event.connect(self.__display_data)
        self.__graph.sigRangeChanged.connect(self.__on_view_range_changed)
        self.__on_view_range_changed()


    def plot_data(self, score_data, diff_data):
        if 0 in [ score_data.shape[0], diff_data.shape[0] ]:
            return

        thread = threading.Thread(target=self.__plot_aim_factors, args=(score_data, diff_data))
        thread.start()


    @Utils.benchmark(f'[ Threaded ] {__name__}')
    def __plot_aim_factors(self, score_data, diff_data):
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
        is_miss = is_miss[inv_filter]

        #print(f'velocity spike: {velocities[timing[2:] == 31126]}')
        #print(f'velocity end: {velocities[timing[2:] == 88531]}')

        #print(f'angle spike: {angles[timing[2:] == 31126]}')
        #print(f'angle end: {angles[timing[2:] == 88531]}')

        #print(f'angle factor spike: {angle_factor[timing[2:] == 31126]}')
        #print(f'angle factor end: {angle_factor[timing[2:] == 88531]}')
        
        if True:
            data_x = np.linspace(0, 1, data_y.shape[0])

            sort_idx = np.argsort(data_y)
            data_y  = data_y[sort_idx]
            is_miss = is_miss[sort_idx]
        else:
            # Debug
            data_x = t_map[inv_filter]
        
        self.__calc_data_event.emit(data_x, data_y, is_miss)


    def __display_data(self, data_x, data_y, is_miss):
        xMin = -0.1
        xMax = 1.1

        data_x_hit = data_x[~is_miss]
        data_y_hit = data_y[~is_miss]

        data_x_miss = data_x[is_miss]
        data_y_miss = data_y[is_miss]

        # Set plot data
        self.__diff_plot_hit.setData(x=data_x_hit, y=data_y_hit/2, top=data_y_hit/2, bottom=data_y_hit/2, pen=mkPen((200, 200, 200, 100), width=2))
        self.__diff_plot_miss.setData(x=data_x_miss, y=data_y_miss/2, top=data_y_miss/2, bottom=data_y_miss/2, pen=mkPen((200, 0, 0, 100), width=2))

        #self.__graph.setLimits(xMin=xMin, xMax=xMax)
        self.__graph.setRange(xRange=[ xMin, xMax ])

        play_percent = 1 - data_y_miss.shape[0]/data_y.shape[0]

        self.__graph_text.setText(
            f"""
            Peak difficulty:     {data_y[-1]:.2f}
            Majority difficulty: {data_y[int(data_y.shape[0]*0.95)]:.2f}
            Average difficulty:  {data_y.mean():.2f}

            Play percentage:     {play_percent:.2f}
            Play diff estimate:  {data_y[int(play_percent*(data_y.shape[0] - 1))]:.2f}
            """
        )


    def __on_view_range_changed(self, _=None):
        view = self.__graph.viewRect()
        pos_x = view.left()
        pos_y = view.bottom()

        margin_x = 0.001*(view.right() - view.left())
        margin_y = 0.001*(view.top() - view.bottom())

        self.__graph_text.setPos(pos_x + margin_x, pos_y + margin_y)
