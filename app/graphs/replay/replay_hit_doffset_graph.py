import numpy as np

import PyQt5
import pyqtgraph
from pyqtgraph.functions import mkPen

from osu_analysis import StdScoreData

from app.misc.utils import Utils


class ReplayHitDOffsetGraph(PyQt5.QtWidgets.QWidget):
    '''
    Hit delta-offset graph

    This graph shows the average and absolute difference between two delta-offsets throughout the replay.
    Delta-offsets consist of 3 offsets, reduced to a difference pair: (x[1] - x[0], x[2] - x[1]).
    
    Displayed as a gray bar is the average between the two d-offsets. 
        When it's positive, the offset is increasing. When it's negative, the offset is decreasing.

    Displayed as a green line, is the absolute difference between the two d-offsets.
        The larger it is, the greater the increase or decrease in hit offset is. It is centered at 
        the average between the two d-offsets. Its displayed span is 2x the actual range.

    This graph is useful for examining the instability within the player's hit timing.
    '''

    def __init__(self, parent=None):
        PyQt5.QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Hit d-offset graph')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLimits(yMin=-250, yMax=250)
        self.__graph.setRange(xRange=[-10, 10000], yRange=[-250, 250])
        self.__graph.setLabel('left', 't-offset', units='ms', unitPrefix='')
        self.__graph.setLabel('bottom', 'time', units='ms', unitPrefix='')
        self.__graph.addLegend()

        self.__plot_delta = pyqtgraph.ErrorBarItem(beam=0)
        self.__graph.addItem(self.__plot_delta)

        self.__plot_range = pyqtgraph.ErrorBarItem(beam=0)
        self.__graph.addItem(self.__plot_range)

        # Hit stats
        self.hit_metrics = pyqtgraph.TextItem('', anchor=(0, 0), )
        self.__graph.addItem(self.hit_metrics)

        # Put it all together
        self.__layout = PyQt5.QtWidgets.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)

        self.__graph.sigRangeChanged.connect(self.__on_view_range_changed)
        self.__on_view_range_changed()


    @Utils.benchmark(__name__)
    def plot_data(self, play_data):
        if play_data.shape[0] == 0:
            return

        # Determine what was the latest play
        data_filter = \
            (play_data['TYPE_HIT'] == StdScoreData.TYPE_HITP)
            # (play_data[:, PlayNpyData.TIMESTAMP] == play_data[-1, PlayNpyData.TIMESTAMP]) & \
        play_data = play_data[data_filter]

        self.__plot_hit_doffsets(play_data)


    def __plot_hit_doffsets(self, data):
        # Extract timings and hit_offsets
        hit_timings = data['T_MAP'].values
        hit_offsets = data['T_HIT'].values - hit_timings

        doffset1 = hit_offsets[1:-1] - hit_offsets[:-2]     # x[1] - x[0]
        doffset2 = hit_offsets[2:] - hit_offsets[1:-1]      # x[2] - x[1]

        avg_doffset = 0.5*(doffset1 + doffset2)
        rng_doffset = np.abs(doffset1 - doffset2)

        # Calculate view
        xMin = min(hit_timings) - 100
        xMax = max(hit_timings) + 100

        x = hit_timings[2:]
        y_avg = avg_doffset

        y_range = rng_doffset

        # Set plot data
        self.__plot_delta.setData(x=x, y=y_avg/2, top=y_avg/2, bottom=y_avg/2, pen=mkPen((200, 200, 200, 200), width=5))
        self.__plot_range.setData(x=x, y=y_avg, top=y_range/2, bottom=y_range/2, pen=mkPen((50, 100, 50, 150), width=2))
        
        self.__graph.setLimits(xMin=xMin - 100, xMax=xMax + 100)
        self.__graph.setRange(xRange=[ xMin - 100, xMax + 100 ])

        self.hit_metrics.setText(
            f'''
            UR: {10*np.std(hit_offsets):.2f}
            avg offset delta: {np.mean(np.abs(avg_doffset)):.2f} ms
            avg offset range: {np.mean(rng_doffset):.2f} ms
            '''
        )


    def __on_view_range_changed(self, _=None):
        view = self.__graph.viewRect()
        pos_x = view.left()
        pos_y = view.bottom()

        margin_x = 0.001*(view.right() - view.left())
        margin_y = 0.001*(view.top() - view.bottom())

        self.hit_metrics.setPos(pos_x + margin_x, pos_y + margin_y)
