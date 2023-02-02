import numpy as np
import threading
import math

import PyQt5
import pyqtgraph
from pyqtgraph.functions import mkPen

from osu_analysis import StdScoreData
from app.misc.utils import Utils


class GraphTapDifficulty(PyQt5.QtWidgets.QWidget):

    __calc_data_event = PyQt5.QtCore.pyqtSignal(object, object, object)

    def __init__(self, parent=None):
        PyQt5.QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Tap difficulty graph')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLimits(yMin=-1, yMax=12)
        self.__graph.setRange(xRange=[-0.1, 1.1], yRange=[-1, 5])
        self.__graph.setLabel('left', 'Tap factor', units='', unitPrefix='')
        self.__graph.setLabel('bottom', 'Factors', units='%', unitPrefix='')
        self.__graph.addLegend()

        self.__diff_plot_miss = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__diff_plot_miss)

        self.__diff_plot_perf = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__diff_plot_perf)

        self.__diff_plot_bad = pyqtgraph.ErrorBarItem()
        self.__graph.addItem(self.__diff_plot_bad)

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

        thread = threading.Thread(target=self.__plot_tap_factors, args=(score_data, diff_data))
        thread.start()


    @Utils.benchmark(f'[ Threaded ] {__name__}')
    def __plot_tap_factors(self, score_data, diff_data):
        # Determine what was the latest play
        #data_filter = \
        #    (score_data[:, ScoreNpyData.TIMESTAMP] == max(score_data[:, ScoreNpyData.TIMESTAMP]))
        #score_data = score_data[data_filter]

        # Filter out sliders holds and releases
        data_filter = (
            (score_data['TYPE_MAP'].values != StdScoreData.ACTION_HOLD) & \
            (score_data['TYPE_MAP'].values != StdScoreData.ACTION_RELEASE)
        )

        score_data = score_data[data_filter]
        diff_data  = diff_data[data_filter]

        # Check if there is any data to operate on
        if score_data.shape[0] < 3:
            data_stub = np.asarray([])
            self.__calc_data_event.emit(data_stub, data_stub, data_stub)
            return

        # Calculate data
        timings = score_data['T_MAP'].values
        toffsets = score_data['T_HIT'].values - timings
        bpm_inc = diff_data['DIFF_T_PRESS_DEC'].values
        bpm_dec = diff_data['DIFF_T_PRESS_INC'].values
        rhym = diff_data['DIFF_T_PRESS_RHM'].values

        is_miss = (
            (score_data['TYPE_HIT'].values == StdScoreData.TYPE_MISS) & (
                (score_data['TYPE_MAP'].values == StdScoreData.ACTION_PRESS)
            )
        )
        score_mask = np.zeros((timings.shape[0] - 2, 3), dtype=np.bool8)
        score_mask[:, 0] = is_miss[2:]
        score_mask[:, 1] = np.abs(toffsets[2:] <= 32)
        score_mask[:, 2] = np.abs(toffsets[2:] > 32) & ~is_miss[2:]

        rates = 1000/(timings[2:] - timings[:-2])

        stamina = np.zeros(rates.shape[0])
        stamina_select = (bpm_dec[2:] > bpm_inc[2:])
        stamina[stamina_select]  = 0.1*(np.log(bpm_inc[2:][stamina_select]/1000 + 1) + 1)
        stamina[~stamina_select] = 0.1

        #vec_rhym_cplx_func = np.vectorize(self.__rhym_cplx_func)
        #rhyhm_cplx = vec_rhym_cplx_func(rhym/100)
        #print(rhym/100)
        #print(rhyhm_cplx)
        
        data_x = np.linspace(0, 1, rates.shape[0])
        data_y = rates*stamina*3

        sort_idx = np.argsort(data_y)
        data_y = data_y[sort_idx]
        score_mask[:, 0] = score_mask[sort_idx, 0]
        score_mask[:, 1] = score_mask[sort_idx, 1]
        score_mask[:, 2] = score_mask[sort_idx, 2]

        self.__calc_data_event.emit(data_x, data_y, score_mask)


    def __display_data(self, data_x, data_y, score_mask):
        xMin = -0.1
        xMax = 1.1

        data_x_miss = data_x[score_mask[:, 0]]
        data_y_miss = data_y[score_mask[:, 0]]

        data_x_perf = data_x[score_mask[:, 1]]
        data_y_perf = data_y[score_mask[:, 1]]

        data_x_bad = data_x[score_mask[:, 2]]
        data_y_bad = data_y[score_mask[:, 2]]

        # Set plot data
        self.__diff_plot_miss.setData(x=data_x_miss, y=data_y_miss/2, top=data_y_miss/2, bottom=data_y_miss/2, pen=mkPen((200, 0, 0, 200), width=2))
        self.__diff_plot_perf.setData(x=data_x_perf, y=data_y_perf/2, top=data_y_perf/2, bottom=data_y_perf/2, pen=mkPen((0, 72, 255, 150), width=2))
        self.__diff_plot_bad.setData(x=data_x_bad, y=data_y_bad/2, top=data_y_bad/2, bottom=data_y_bad/2, pen=mkPen((224, 224, 0, 100), width=2))

        self.__graph.setLimits(xMin=xMin, xMax=xMax)
        self.__graph.setRange(xRange=[ xMin, xMax ])

        play_percent = 1 - (data_y_miss.shape[0] + 0.25*data_y_bad.shape[0])/data_y.shape[0]

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


    def __rhym_cplx_func(self, x):
        n = np.arange(1, 8)
        return np.sum(np.abs(np.sin(2*(2**n)*math.pi*x)))
