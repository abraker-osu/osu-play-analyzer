import pyqtgraph

from PyQt5 import QtCore
from PyQt5 import QtWidgets

import numpy as np
import pandas as pd

from osu_interfaces import Gamemode, Mod
from beatmap_reader import BeatmapIO
from replay_reader import ReplayIO
from osu_analysis import StdMapData, StdReplayData

from misc.Logger import Logger
from misc.utils import Utils


class MapMouseGraph(QtWidgets.QTabWidget):

    logger = Logger.get_logger(__name__)

    MAP_T = 0
    MAP_X = 1
    MAP_Y = 2
    MAP_P = 3  # Press type
    MAP_O = 4  # Object type

    REPLAY_T = 0
    REPLAY_X = 1
    REPLAY_Y = 2
    REPLAY_K = 3

    def __init__(self, parent=None):
        QtWidgets.QTabWidget.__init__(self, parent)

        self.replay_data = None
        self.map_data    = None

        self.map_md5 = None

        self.__layout = QtWidgets.QVBoxLayout(self)

        self.__graph_pos = QtWidgets.QWidget()
        self.__layout_pos = QtWidgets.QVBoxLayout(self.__graph_pos)
        self.addTab(self.__graph_pos, 'Position')

        self.__graph_vel = QtWidgets.QWidget()
        self.__layout_vel = QtWidgets.QVBoxLayout(self.__graph_vel)
        self.addTab(self.__graph_vel, 'Velocity')

        self.__graph_acc = QtWidgets.QWidget()
        self.__layout_acc = QtWidgets.QVBoxLayout(self.__graph_acc)
        self.addTab(self.__graph_acc, 'Acceleration')

        self.__graph_pos_algn = pyqtgraph.PlotWidget(title='Cursor path displacement, aligned orientation')
        self.__graph_pos_algn.setLabel('left', 'Displacement from initial note', units='osu!px', unitPrefix='')

        self.__graph_pos_orth = pyqtgraph.PlotWidget(title='Cursor path displacement, orthogonal orientation')
        self.__graph_pos_orth.setLabel('left', 'Displacement from initial note', units='osu!px', unitPrefix='')

        self.__graph_vel_algn = pyqtgraph.PlotWidget(title='Cursor path velocity, aligned orientation')
        self.__graph_vel_algn.setLabel('left', 'Velocity', units='osu!px / ms', unitPrefix='')

        self.__graph_vel_orth = pyqtgraph.PlotWidget(title='Cursor path velocity, orthogonal orientation')
        self.__graph_vel_orth.setLabel('left', 'Velocity', units='osu!px / ms', unitPrefix='')

        self.__graph_acc_algn = pyqtgraph.PlotWidget(title='Cursor path acceleration, aligned orientation')
        self.__graph_acc_algn.setLabel('left', 'Acceleration', units='osu!px / ms^2', unitPrefix='')

        self.__graph_acc_orth = pyqtgraph.PlotWidget(title='Cursor path acceleration, orthogonal orientation')
        self.__graph_acc_orth.setLabel('left', 'Acceleration', units='osu!px / ms^2', unitPrefix='')

        for graph in [
            self.__graph_pos_algn, self.__graph_pos_orth,
            self.__graph_vel_algn, self.__graph_vel_orth,
            self.__graph_acc_algn, self.__graph_acc_orth
        ]:
            plot_item = graph.getPlotItem()
            assert plot_item is not None

            plot_item.getAxis('left').enableAutoSIPrefix(False)
            plot_item.getAxis('bottom').enableAutoSIPrefix(False)
            graph.enableAutoRange(axis='x', enable=False)
            graph.enableAutoRange(axis='y', enable=False)
            graph.setRange(xRange=[-10, 550], yRange=[-410, 10])
            graph.setLabel('bottom', 'Normalized time', units='ms (map) / ms (replay)', unitPrefix='')

        self.__status_label = QtWidgets.QLabel()

        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(0)

        # Put it all together
        for graph in [
            ( self.__layout_pos, self.__graph_pos_algn, self.__graph_pos_orth, ),
            ( self.__layout_vel, self.__graph_vel_algn, self.__graph_vel_orth, ),
            ( self.__layout_acc, self.__graph_acc_algn, self.__graph_acc_orth )
        ]:
            layout, x_graph, y_graph = graph

            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            layout.addWidget(x_graph)
            layout.addWidget(y_graph)


    def set_replay_from_replay_data(self, replay_data: pd.DataFrame):
        if isinstance(replay_data, type(None)):
            return

        self.replay_data = np.zeros((len(replay_data['time']), 7))
        self.replay_data[:, self.REPLAY_T] =  np.asarray(replay_data['time'])
        self.replay_data[:, self.REPLAY_X] =  np.asarray(replay_data['x'])
        self.replay_data[:, self.REPLAY_Y] = -np.asarray(replay_data['y'])
        self.replay_data[:, self.REPLAY_K] =  np.asarray(
            ( replay_data['k1'] == StdReplayData.PRESS ) +
            ( replay_data['k2'] == StdReplayData.PRESS ) +
            ( replay_data['m1'] == StdReplayData.PRESS ) +
            ( replay_data['m2'] == StdReplayData.PRESS )
        )
        self.__draw_data()


    def open_replay_from_file_name(self, file_name: str):
        try: replay = ReplayIO.open_replay(file_name)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error opening replay'))
            return

        try: replay_data = StdReplayData.get_replay_data(replay)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error reading replay'))
            return

        self.set_replay_from_replay_data(replay_data)


    def open_map_from_osu_data(self, osu_data: str):
        try: beatmap = BeatmapIO.load_beatmap(osu_data)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error opening map'))
            return

        if beatmap.gamemode != Gamemode.OSU:
            print(f'{beatmap.gamemode} gamemode is not supported')
            return

        try: map_data = StdMapData.get_map_data(beatmap)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error reading map'))
            return

        map_data['y'] = -map_data['y']

        # self.map_text = beatmap.metadata.name
        # viewing_text  = self.map_text + ' ' + self.replay_text
        # self.status_label.setText(f'Viewing: {viewing_text}')

        self.set_map_from_map_data(map_data)


    def open_map_from_file_name(self, file_name: str, mods: int | Mod = 0):
        try: beatmap = BeatmapIO.open_beatmap(file_name)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error opening map'))
            raise

        if beatmap.gamemode != Gamemode.OSU:
            print(f'{beatmap.gamemode} gamemode is not supported')
            raise Exception

        try: map_data = StdMapData.get_map_data(beatmap)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error reading map'))
            raise

        if isinstance(mods, int):
            mods = Mod(mods)

        cs = beatmap.difficulty.cs or beatmap.difficulty.od or 0
        if mods.has_mod(Mod.HardRock): cs *= 1.3
        if mods.has_mod(Mod.Easy):     cs *= 0.5

        cs = min(cs, 10)
        if mods.has_mod(Mod.DoubleTime) or mods.has_mod(Mod.Nightcore):
            map_data['time'] *= 0.75

        if mods.has_mod(Mod.HalfTime):
            map_data['time'] *= 1.5

        map_data['y'] = -map_data['y']

        # self.map_text = beatmap.metadata.name
        # viewing_text = self.map_text + ' ' + self.replay_text
        # self.__status_label.setText(f'Viewing: {viewing_text}')

        self.set_map_from_map_data(map_data)


    def set_map_from_map_data(self, map_data: pd.DataFrame):
        if isinstance(map_data, type(None)):
            return

        self.map_data = np.zeros((len(map_data['time']), 5))
        self.map_data[:, self.MAP_T]  = np.asarray(map_data['time'])
        self.map_data[:, self.MAP_X]  = np.asarray(map_data['x'])
        self.map_data[:, self.MAP_Y]  = np.asarray(map_data['y'])
        self.map_data[:, self.MAP_P]  = np.asarray(map_data['type'])
        self.map_data[:, self.MAP_O]  = np.asarray(map_data['object'])

        self.__draw_data()


    def __draw_data(self):
        if isinstance(self.replay_data, type(None)):
            return

        if isinstance(self.map_data, type(None)):
            return

        # Do initial filtering
        #  - Only circles and sliders
        #  - Seperate presses and releases
        sel_obj = (
            ( self.map_data[:, self.MAP_O] == StdMapData.TYPE_CIRCLE ) |
            ( self.map_data[:, self.MAP_O] == StdMapData.TYPE_SLIDER )
        )
        sel_prs = self.map_data[:, self.MAP_P] == StdMapData.TYPE_PRESS
        sel_rel = self.map_data[:, self.MAP_P] == StdMapData.TYPE_RELEASE

        data_prs = self.map_data[sel_obj & sel_prs, :]
        data_rel = self.map_data[sel_obj & sel_rel, :]

        # Get time intervals between notes
        diffs_note_time = data_prs[1:, self.MAP_T] - data_rel[:-1, self.MAP_T]

        # Get note orientations
        thetas = np.pi - np.arctan2(
            data_rel[1:, self.MAP_Y] - data_prs[:-1, self.MAP_Y],
            data_rel[1:, self.MAP_X] - data_prs[:-1, self.MAP_X]
        )

        # For each time interval, get replay data associated with the time interval
        replay_data: list[np.ndarray] = []
        for i in range(len(diffs_note_time) - 1):
            # Extract replay data in time interval
            sel_time = (
                ( self.replay_data[:, self.REPLAY_T] >= data_rel[i,     self.MAP_T]) &
                ( self.replay_data[:, self.REPLAY_T]  < data_prs[i + 1, self.MAP_T])
            )
            data = self.replay_data[sel_time]
            if data.shape[0] < 3:
                continue

            # Align start of replay section to start of note
            data[:, self.REPLAY_T] -= data_rel[i, self.MAP_T]

            # Normalize time span
            data[:, self.REPLAY_T] /= diffs_note_time[i]

            # Rotate and and display replay x and y positions to match note direction and starting note position
            data[:, self.REPLAY_X] = \
                ( data[:, self.REPLAY_X] - data_prs[i, self.MAP_X] ) * np.cos(thetas[i]) - \
                ( data[:, self.REPLAY_Y] - data_prs[i, self.MAP_Y] ) * np.sin(thetas[i])

            # TODO: Fix - This is splitting into negative and positive parts when patterns are vertical
            data[:, self.REPLAY_Y] = \
                ( data[:, self.REPLAY_X] - data_prs[i, self.MAP_X] ) * np.sin(thetas[i]) + \
                ( data[:, self.REPLAY_Y] - data_prs[i, self.MAP_Y] ) * np.cos(thetas[i])

            # TODO: It might be possible to clean up the replay data via interpolation. At the very least reduce the number of
            #   spikes it has.

            # When the player aims that aim is not perfectly timed relative to the notes. As a result the
            # curves would appear smeared across time ( https://abraker.s-ul.eu/7Hz8qZ9F ). To fix this
            # they are shifted to fixate points with highest velocity at 0.
            #
            # This creates a more pronounced visualization ( https://abraker.s-ul.eu/XVjMttXM )
            dist = ((data[1:, self.REPLAY_X] - data[:-1, self.REPLAY_X])**2 + (data[1:, self.REPLAY_Y] - data[:-1, self.REPLAY_Y])**2)**0.5
            vel = np.zeros(data.shape[0])
            vel[1:] = dist / np.diff(data[:, self.REPLAY_T])

            # Determine 95% percentile to filter out spikes in replays
            vel[vel >= np.percentile(vel, 95)] = 0

            vel_t = data[np.argmax(vel), self.REPLAY_T]
            data[:, self.REPLAY_T] -= vel_t

            replay_data.append(data)

        # Determine and set graph view
        for graphs in [
            ( self.__graph_pos_algn, self.__graph_pos_orth ),
            ( self.__graph_vel_algn, self.__graph_vel_orth ),
            ( self.__graph_acc_algn, self.__graph_acc_orth )
        ]:
            graph_x, graph_y = graphs

            min_x = int(min([ np.min(data[:, self.REPLAY_X]) for data in replay_data ], default=-500))
            max_x = int(max([ np.max(data[:, self.REPLAY_X]) for data in replay_data ], default= 500))
            min_y = int(min([ np.min(data[:, self.REPLAY_Y]) for data in replay_data ], default=-500))
            max_y = int(max([ np.max(data[:, self.REPLAY_Y]) for data in replay_data ], default= 500))
            min_t = int(min([ np.min(data[:, self.REPLAY_T]) for data in replay_data ], default=   0))
            max_t = int(max([ np.max(data[:, self.REPLAY_T]) for data in replay_data ], default=   1))

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

            graph_x.clear()
            graph_y.clear()

            for i, data in enumerate(replay_data):
                # TODO: Colorize based on distance
                plot_item = graph_x.plotItem
                assert plot_item is not None
                plot_x = plot_item.plot(pen=pyqtgraph.mkPen(color=(255, 0, 0, 150)), symbol='o', symbolPen=None, symbolSize=2, symbolBrush='y')

                plot_item = graph_y.plotItem
                assert plot_item is not None
                plot_y = plot_item.plot(pen=pyqtgraph.mkPen(color=(255, 0, 0, 150)), symbol='o', symbolPen=None, symbolSize=2, symbolBrush='y')

                plot_x.setData(data[:, self.REPLAY_T], data[:, self.REPLAY_X])
                plot_y.setData(data[:, self.REPLAY_T], data[:, self.REPLAY_Y])

                # Avoid div-by-zero
                zero_filter = np.zeros(data.shape[0], dtype=bool)
                zero_filter[:-1] = ~( data[:-1, self.REPLAY_T] == data[1:, self.REPLAY_T] )
                data = data[zero_filter, :]

                replay_data[i] = np.zeros((data.shape[0] - 1, 3))
                replay_data[i][:, self.REPLAY_X] = np.diff(data[:, self.REPLAY_X]) / np.diff(data[:, self.REPLAY_T])
                replay_data[i][:, self.REPLAY_Y] = np.diff(data[:, self.REPLAY_Y]) / np.diff(data[:, self.REPLAY_T])
                replay_data[i][:, self.REPLAY_T] = data[1:, self.REPLAY_T]
