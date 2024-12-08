import pyqtgraph

from PyQt5 import QtCore
from PyQt5 import QtWidgets

import numpy as np

from osu_analysis import ReplayIO, StdReplayData, StdScoreData

from app.misc.Logger import Logger
from app.misc.utils import Utils


class MouseGraph(QtWidgets.QTabWidget):

    logger = Logger.get_logger(__name__)

    MAP_T = 0
    MAP_X = 1
    MAP_Y = 2

    REPLAY_T = 0
    REPLAY_X = 1
    REPLAY_Y = 2
    REPLAY_K1 = 3
    REPLAY_K2 = 4
    REPLAY_M1 = 5
    REPLAY_M2 = 6

    def __init__(self, parent=None):
        QtWidgets.QTabWidget.__init__(self, parent)

        self.__graph_pos = QtWidgets.QWidget()
        self.__layout_pos = QtWidgets.QVBoxLayout(self.__graph_pos)
        self.addTab(self.__graph_pos, 'Position')

        self.__graph_vel = QtWidgets.QWidget()
        self.__layout_vel = QtWidgets.QVBoxLayout(self.__graph_vel)
        self.addTab(self.__graph_vel, 'Velocity')

        self.__graph_acc = QtWidgets.QWidget()
        self.__layout_acc = QtWidgets.QVBoxLayout(self.__graph_acc)
        self.addTab(self.__graph_acc, 'Acceleration')

        # X position graph
        self.__graph_xpos = pyqtgraph.PlotWidget(title='Cursor x-position')
        self.__graph_xpos.setLabel('left', 'position', units='osu!px', unitPrefix='')
        self.__plot_xpos = self.__graph_xpos.plotItem.plot(pen=pyqtgraph.mkPen(color=(255, 0, 0, 150)), symbol='o', symbolPen=None, symbolSize=2, symbolBrush='y')

        # Y position graph
        self.__graph_ypos = pyqtgraph.PlotWidget(title='Cursor y-position')
        self.__graph_ypos.setLabel('left', 'position', units='osu!px', unitPrefix='')
        self.__plot_ypos = self.__graph_ypos.plotItem.plot(pen=pyqtgraph.mkPen(color=(255, 0, 0, 150)), symbol='o', symbolPen=None, symbolSize=2, symbolBrush='y')

        # X velocity graph
        self.__graph_xvel = pyqtgraph.PlotWidget(title='Cursor x-velocity')
        self.__graph_xvel.setLabel('left', 'velocity', units='osu!px/ms', unitPrefix='')
        self.__plot_xvel = self.__graph_xvel.plotItem.plot(pen=pyqtgraph.mkPen(color=(255, 0, 0, 150)), symbol='o', symbolPen=None, symbolSize=2, symbolBrush='y')

        # Y velocity graph
        self.__graph_yvel = pyqtgraph.PlotWidget(title='Cursor y-velocity')
        self.__graph_yvel.setLabel('left', 'velocity', units='osu!px/ms', unitPrefix='')
        self.__plot_yvel = self.__graph_yvel.plotItem.plot(pen=pyqtgraph.mkPen(color=(255, 0, 0, 150)), symbol='o', symbolPen=None, symbolSize=2, symbolBrush='y')

        # X acceleration graph
        self.__graph_xacc = pyqtgraph.PlotWidget(title='Cursor x-acceleration')
        self.__graph_xacc.setLabel('left', 'acceleration', units='osu!px/ms^2', unitPrefix='')
        self.__plot_xacc = self.__graph_xacc.plotItem.plot(pen=pyqtgraph.mkPen(color=(255, 0, 0, 150)), symbol='o', symbolPen=None, symbolSize=2, symbolBrush='y')

        # Y acceleration graph
        self.__graph_yacc = pyqtgraph.PlotWidget(title='Cursor y-acceleration')
        self.__graph_yacc.setLabel('left', 'acceleration', units='osu!px/ms^2', unitPrefix='')
        self.__plot_yacc = self.__graph_yacc.plotItem.plot(pen=pyqtgraph.mkPen(color=(255, 0, 0, 150)), symbol='o', symbolPen=None, symbolSize=2, symbolBrush='y')

        for graph in [
            self.__graph_xpos, self.__graph_ypos,
            self.__graph_xvel, self.__graph_yvel,
            self.__graph_xacc, self.__graph_yacc
        ]:
            graph.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
            graph.getPlotItem().getAxis('bottom').enableAutoSIPrefix(False)
            graph.enableAutoRange(axis='x', enable=False)
            graph.enableAutoRange(axis='y', enable=False)
            graph.setRange(xRange=[-10, 550], yRange=[-410, 10])
            graph.setLabel('bottom', 'time', units='ms', unitPrefix='')

        # Put it all together
        for graph in [
            ( self.__layout_pos, self.__graph_xpos, self.__graph_ypos ),
            ( self.__layout_vel, self.__graph_xvel, self.__graph_yvel ),
            ( self.__layout_acc, self.__graph_xacc, self.__graph_yacc )
        ]:
            layout, x_graph, y_graph = graph

            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            layout.addWidget(x_graph)
            layout.addWidget(y_graph)


    def set_replay_from_replay_data(self, replay_data):
        if isinstance(replay_data, type(None)):
            return

        self.replay_data = np.zeros((len(replay_data['time']), 7))
        self.replay_data[:, self.REPLAY_T]  = np.asarray(replay_data['time'])
        self.replay_data[:, self.REPLAY_X]  = np.asarray(replay_data['x'])
        self.replay_data[:, self.REPLAY_Y]  = -np.asarray(replay_data['y'])
        self.__draw_replay_data()


    def set_replay_from_play_data(self, score_data):
        # Assumes play data pertianing to only one replay is passed
        #
        # Play data only has score info, so at best only score points are recoverable
        # Basically how old osu! 2007 - 2009 era replays looked like
        # Press timings are easy to recover, however matching cursor positions to map data is not
        #   because note/aimpoint positions are not saved in play data
        data_filter = (score_data['TYPE_HIT'] == StdScoreData.TYPE_HITP)
        score_data = score_data[data_filter]

        self.replay_data = np.zeros((score_data.shape[0]*2, 7))

        # Press timings
        self.replay_data[::2, self.REPLAY_T]   = score_data['T_HIT']
        self.replay_data[::2, self.REPLAY_X]   = score_data['X_HIT']
        self.replay_data[::2, self.REPLAY_Y]   = -score_data['Y_HIT']

        # Release timings
        self.replay_data[1::2, self.REPLAY_T]  = score_data['T_HIT'] + 50
        self.replay_data[1::2, self.REPLAY_X]  = score_data['X_HIT']
        self.replay_data[1::2, self.REPLAY_Y]  = -score_data['Y_HIT']

        self.__draw_replay_data()


    def open_replay_from_file_name(self, file_name):
        try: replay = ReplayIO.open_replay(file_name)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error opening replay'))
            return

        try: replay_data = StdReplayData.get_replay_data(replay)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error reading replay'))
            return

        self.set_replay_from_replay_data(replay_data)


    def __draw_replay_data(self):
        if isinstance(self.replay_data, type(None)):
            return

        replay_data_t = self.replay_data[:, self.REPLAY_T]
        replay_data_x = self.replay_data[:, self.REPLAY_X]
        replay_data_y = self.replay_data[:, self.REPLAY_Y]

        for data in [
            ( self.__graph_xpos, self.__plot_xpos, self.__graph_ypos, self.__plot_ypos ),
            ( self.__graph_xvel, self.__plot_xvel, self.__graph_yvel, self.__plot_yvel ),
            ( self.__graph_xacc, self.__plot_xacc, self.__graph_yacc, self.__plot_yacc )
        ]:
            graph_x, plot_x, graph_y, plot_y = data

            plot_x.setData(replay_data_t, replay_data_x)
            plot_y.setData(replay_data_t, replay_data_y)

            min_x = int(min(replay_data_x)); max_x = int(max(replay_data_x))
            min_y = int(min(replay_data_y)); max_y = int(max(replay_data_y))
            min_t = int(min(replay_data_t)); max_t = int(max(replay_data_t))

            graph_x.setRange(
                QtCore.QRect(
                    QtCore.QPoint(min_t, min_x),
                    QtCore.QPoint(max_t, max_x)
                )
            )
            graph_y.setRange(
                QtCore.QRect(
                    QtCore.QPoint(min_t, min_y),
                    QtCore.QPoint(max_t, max_y)
                )
            )

            # Avoid div-by-zero
            zero_filter = np.zeros_like(replay_data_t, dtype=bool)
            zero_filter[:-1] = ~( replay_data_t[:-1] == replay_data_t[1:] )

            replay_data_x = replay_data_x[zero_filter]
            replay_data_y = replay_data_y[zero_filter]
            replay_data_t = replay_data_t[zero_filter]

            replay_data_x = np.diff(replay_data_x) / np.diff(replay_data_t)
            replay_data_y = np.diff(replay_data_y) / np.diff(replay_data_t)
            replay_data_t = replay_data_t[1:]
