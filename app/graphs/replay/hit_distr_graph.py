import PyQt5
import pyqtgraph

import numpy as np
import scipy
import math

from osu_analysis import StdScoreData
from app.data_recording.data import PlayNpyData


class HitDistrGraph(PyQt5.QtWidgets.QWidget):

    def __init__(self, parent=None):
        PyQt5.QtWidgets.QWidget.__init__(self, parent)

        # Main graph
        self.__graph = pyqtgraph.PlotWidget(title='Hit distribution graph')
        self.__graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        self.__graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
        self.__graph.enableAutoRange(axis='x', enable=False)
        self.__graph.enableAutoRange(axis='y', enable=False)
        self.__graph.setLabel('left', 'Freq', units='#', unitPrefix='')
        self.__graph.setLabel('bottom', 'Hit offset', units='ms', unitPrefix='')
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
        self.__layout = PyQt5.QtWidgets.QHBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(2)
        self.__layout.addWidget(self.__graph)

        self.__graph.sigRangeChanged.connect(self.__on_view_range_changed)
        self.__on_view_range_changed()


    def plot_data(self, play_data):
        if play_data.shape[0] == 0:
            return

        # Determine what was the latest play
        #data_filter = \
        #    (play_data[:, PlayNpyData.TIMESTAMP] == max(play_data[:, PlayNpyData.TIMESTAMP]))

        #play_data = play_data[data_filter]
            
        slider_select = np.zeros(play_data.shape[0], dtype=bool)
        slider_select[:-1] = \
            (play_data['TYPE_MAP'].values[:-1] == StdScoreData.ACTION_PRESS) & (
                (play_data['TYPE_MAP'].values[1:] == StdScoreData.ACTION_HOLD) | \
                (play_data['TYPE_MAP'].values[1:] == StdScoreData.ACTION_RELEASE)
            )

        num_sliders = np.sum(slider_select)
            
        data_filter = \
            (play_data['TYPE_MAP'] == StdScoreData.ACTION_PRESS)

        play_data = play_data[data_filter]
        slider_select = slider_select[data_filter]

        # Record total number of score presses
        num_scores = play_data.shape[0]

        data_filter = \
            (play_data['TYPE_HIT'] == StdScoreData.TYPE_HITP)
            
        play_data = play_data[data_filter]
        slider_select = slider_select[data_filter]

        if play_data.shape[0] == 0:
            return

        hit_offsets = play_data['T_HIT'].values - play_data['T_MAP'].values

        # Get a histogram for hit offsets
        step = (150 - 0)/(0.1*hit_offsets.shape[0])
        y, x = np.histogram(hit_offsets, bins=np.linspace(-150, 150, int(0.3*hit_offsets.shape[0])))
        
        if y.shape[0] == 0:
            return

        self.__plot.setData(x, y, stepMode="center", fillLevel=0, fillOutline=True, brush=(0,0,255,150))

        self.__min_err_line.setValue(x[:-1][y == np.max(y)][0] + step/2)
        print(f'Avg distr peak: {x[:-1][y == np.max(y)][0] + step/2} ms')

        y_max = np.max(y) * 1.1
        self.__graph.setLimits(yMin=-1, yMax=y_max)
        self.__graph.setRange(yRange=[ -1, y_max ])

        """
        offset_OD4 = 55.5
        offset_OD5 = 49.5
        offset_OD6 = 43.5
        offset_OD7 = 37.5

        # osu! doesn't process slider hit accuracy the same way for hitcircles
        # So special handling for sliders is needed
        num_hits_300_OD4 = np.sum(np.abs(hit_offsets[~slider_select]) <= offset_OD4) #+ np.sum(np.abs(hit_offsets[slider_select]) <= 4*offset_OD4)
        num_hits_300_OD5 = np.sum(np.abs(hit_offsets[~slider_select]) <= offset_OD5) #+ np.sum(np.abs(hit_offsets[slider_select]) <= 4*offset_OD5)
        num_hits_300_OD6 = np.sum(np.abs(hit_offsets[~slider_select]) <= offset_OD6) #+ np.sum(np.abs(hit_offsets[slider_select]) <= 4*offset_OD6)
        num_hits_300_OD7 = np.sum(np.abs(hit_offsets[~slider_select]) <= offset_OD7) #+ np.sum(np.abs(hit_offsets[slider_select]) <= 4*offset_OD7)

        # Calculate needed 300s for 99% accuracy
        num_50s_99  = 0
        num_100s_99 = num_scores*0.01  # 1% of score presses
        needed_num_300s_99 = math.ceil(.99*num_scores - (300*num_sliders + 100*num_50s_99 + 50*num_100s_99)/300)

        # Calculate needed 300s for 97% accuracy
        num_50s_97  = 0
        num_100s_97 = num_scores*0.04  # 4% of score presses
        needed_num_300s_97 = math.ceil(.97*num_scores - (300*num_sliders + 100*num_50s_97 + 50*num_100s_97)/300)

        num_scores -= num_sliders

        mean_offset = np.mean(hit_offsets[~slider_select])
        dev_offset  = np.std(hit_offsets[~slider_select])
        dev_uncertainty = dev_offset/math.sqrt(2*num_scores - 2)

        # scipy cdf can't handle 0 stdev (div by 0)
        if dev_offset == 0:
            prob_300_OD4 = 1.0 if -offset_OD4 <= mean_offset <= offset_OD4 else 0.0
            prob_300_OD5 = 1.0 if -offset_OD5 <= mean_offset <= offset_OD5 else 0.0
            prob_300_OD6 = 1.0 if -offset_OD6 <= mean_offset <= offset_OD6 else 0.0
            prob_300_OD7 = 1.0 if -offset_OD7 <= mean_offset <= offset_OD7 else 0.0
        else:
            prob_greater_than_neg = scipy.stats.norm.cdf(-offset_OD4, loc=mean_offset, scale=(dev_offset + dev_uncertainty))
            prob_less_than_pos    = scipy.stats.norm.cdf(offset_OD4, loc=mean_offset, scale=(dev_offset + dev_uncertainty))
            prob_300_OD4 = prob_less_than_pos - prob_greater_than_neg

            prob_greater_than_neg = scipy.stats.norm.cdf(-offset_OD5, loc=mean_offset, scale=(dev_offset + dev_uncertainty))
            prob_less_than_pos    = scipy.stats.norm.cdf(offset_OD5, loc=mean_offset, scale=(dev_offset + dev_uncertainty))
            prob_300_OD5 = prob_less_than_pos - prob_greater_than_neg
            
            prob_greater_than_neg = scipy.stats.norm.cdf(-offset_OD6, loc=mean_offset, scale=(dev_offset + dev_uncertainty))
            prob_less_than_pos    = scipy.stats.norm.cdf(offset_OD6, loc=mean_offset, scale=(dev_offset + dev_uncertainty))
            prob_300_OD6 = prob_less_than_pos - prob_greater_than_neg

            prob_greater_than_neg = scipy.stats.norm.cdf(-offset_OD7, loc=mean_offset, scale=(dev_offset + dev_uncertainty))
            prob_less_than_pos    = scipy.stats.norm.cdf(offset_OD7, loc=mean_offset, scale=(dev_offset + dev_uncertainty))
            prob_300_OD7 = prob_less_than_pos - prob_greater_than_neg

        self.score_metrics.setText(
            f'''
            Mean: {mean_offset:.2f} ms   Dev: {dev_offset:.2f}±{dev_uncertainty:.2f} ms
            Num hit circles: {num_scores} ({num_sliders} sliders excluded)   
            99% needed 300s: {needed_num_300s_99}      97% needed 300s: {needed_num_300s_97}

            OD4 | Num hits 300: {num_hits_300_OD4}   prob 99% acc: {100*math.pow(prob_300_OD4, needed_num_300s_99):.4f}%   prob 97% acc: {100*math.pow(prob_300_OD4, needed_num_300s_97):.4f}%
            OD5 | Num hits 300: {num_hits_300_OD5}   prob 99% acc: {100*math.pow(prob_300_OD5, needed_num_300s_99):.4f}%   prob 97% acc: {100*math.pow(prob_300_OD5, needed_num_300s_97):.4f}%
            OD6 | Num hits 300: {num_hits_300_OD6}   prob 99% acc: {100*math.pow(prob_300_OD6, needed_num_300s_99):.4f}%   prob 97% acc: {100*math.pow(prob_300_OD6, needed_num_300s_97):.4f}%
            OD7 | Num hits 300: {num_hits_300_OD7}   prob 99% acc: {100*math.pow(prob_300_OD7, needed_num_300s_99):.4f}%   prob 97% acc: {100*math.pow(prob_300_OD7, needed_num_300s_97):.4f}%
            '''
        )
        """
        

    def __on_view_range_changed(self, _=None):
        view = self.__graph.viewRect()
        pos_x = view.left()
        pos_y = view.bottom()

        margin_x = 0.001*(view.right() - view.left())
        margin_y = 0.001*(view.top() - view.bottom())

        self.score_metrics.setPos(pos_x + margin_x, pos_y + margin_y)
