import PyQt6
import pyqtgraph

import numpy as np

from osu_analysis import StdScoreData
from misc.utils import Utils


class DoffsetsDistrGraph(PyQt6.QtWidgets.QWidget):

    def __init__(self, parent=None):
        PyQt6.QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Doffsets distribution graph')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLabel('left', 'Freq', units='#', unitPrefix='')
        self.__graph.setLabel('bottom', 'Doffset', units='ms', unitPrefix='')
        self.__graph.setLimits(xMin=-200, yMin=-1, xMax=200)
        self.__graph.setXRange(-110, 110)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)

        self.__min_err_line = pyqtgraph.InfiniteLine(angle=90, pen=pyqtgraph.mkPen((255, 100, 0, 150), width=1))
        self.__graph.addItem(self.__min_err_line)

        self.__plot = self.__graph.plot()

        # Score stats
        self.score_metrics = pyqtgraph.TextItem('', anchor=(0, 0), )
        self.__graph.addItem(self.score_metrics)

        # Put it all together
        self.__layout = PyQt6.QtWidgets.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)

        self.__graph.sigRangeChanged.connect(self.__on_view_range_changed)
        self.__on_view_range_changed()


    @Utils.benchmark(__name__)
    def plot_data(self, play_data):
        if play_data.shape[0] == 0:
            return

        data_filter = (
            (play_data['TYPE_MAP'] == StdScoreData.ACTION_PRESS) &
            (play_data['TYPE_HIT'] == StdScoreData.TYPE_HITP)
        )

        play_data = play_data[data_filter]
        if play_data.shape[0] == 0:
            return

        hit_timings = play_data['T_MAP'].values
        hit_offsets = play_data['T_HIT'].values - hit_timings

        doffsets = hit_offsets[2:] - hit_offsets[1:-1]     # x[1] - x[0]

        # Get a histogram for hit offsets
        step = (150 - 0)/(0.5*doffsets.shape[0])
        y, x = np.histogram(doffsets, bins=np.linspace(-150, 150, int(0.5*doffsets.shape[0])))

        if y.shape[0] == 0:
            return

        self.__plot.setData(x, y, stepMode="center", fillLevel=0, fillOutline=True, brush=(0,0,255,150))

        self.__min_err_line.setValue(x[:-1][y == np.max(y)][0] + step/2)
        print(f'Avg distr peak: {x[:-1][y == np.max(y)][0] + step/2} ms')

        y_max = np.max(y) * 1.1
        self.__graph.setLimits(yMin=-1, yMax=y_max)
        self.__graph.setRange(yRange=[ -1, y_max ])


    def __on_view_range_changed(self, _=None):
        view = self.__graph.viewRect()
        pos_x = view.left()
        pos_y = view.bottom()

        margin_x = 0.001*(view.right() - view.left())
        margin_y = 0.001*(view.top() - view.bottom())

        self.score_metrics.setPos(pos_x + margin_x, pos_y + margin_y)
