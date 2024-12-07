"""
Widget that allows to view beatmaps and replays.

The user can load beatmaps and replays via menubar on top.
Maps being made in the map_architect_window are also displayed here
"""
import numpy as np
import pandas as pd

from PyQt5 import QtWidgets
from PyQt5 import QtCore
import pyqtgraph

from osu_analysis import BeatmapIO, ReplayIO, StdMapData, StdReplayData, StdScoreData, Gamemode, Mod
from osu_db import MapsDB

from app.misc.Logger import Logger
from app.misc.utils import Utils
from app.data_recording.score_npy import ScoreNpy
from app.misc.osu_utils import OsuUtils
from app.widgets.hitobject_plot import HitobjectPlot
from app.widgets.timing_plot import TimingPlot

from app.file_managers import AppConfig


class MapDisplay(QtWidgets.QWidget):

    __logger = Logger.get_logger(__name__)

    data_loaded = QtCore.pyqtSignal()
    time_changed_event = QtCore.pyqtSignal(object)

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
        QtWidgets.QWidget.__init__(self, parent)

        MapDisplay.__logger.debug('MapDisplay.__init__ enter')

        self.__maps_db = MapsDB(AppConfig.cfg['osu_dir'])

        self.timing_data = np.asarray([])
        self.map_data    = {}
        self.replay_data = np.empty(shape=(0, 7))

        self.map_md5 = None
        self.ar_ms = None
        self.cs_px = None

        self.map_text = ''
        self.replay_text = ''

        self.__init_gui()
        self.__build_layout()

        MapDisplay.__logger.debug('MapDisplay.__init__ exit')


    def __init_gui(self):
        self.menu_bar  = QtWidgets.QMenuBar()
        self.file_menu = QtWidgets.QMenu("&File")

        self.open_map_action    = QtWidgets.QAction("&Open *.osu", self.file_menu, triggered=lambda: self.__open_map_dialog())
        self.open_replay_action = QtWidgets.QAction("&Open *.osr", self.file_menu, triggered=lambda: self.__open_replay_dialog())

        self.__layout = QtWidgets.QVBoxLayout(self)

        # Pattern Visualization
        self.visual = pyqtgraph.PlotWidget(title='Pattern visualization')
        self.plot_notes    = HitobjectPlot()
        self.plot_cursor   = self.visual.plot(pen=None, symbol='+', symbolPen=(0, 166, 31, 255), symbolBrush=None, symbolSize=6, pxMode=True)
        self.plot_approach = self.visual.plot(pen=None, symbol='o', symbolPen=(100, 100, 255, 200), symbolBrush=None, symbolSize=100, pxMode=False)

        # Timing visualization
        self.timeline = pyqtgraph.PlotWidget()
        self.timeline_marker = pyqtgraph.InfiniteLine(angle=90, movable=True)
        self.hitobject_plot = HitobjectPlot()
        self.k1_timing_plot = TimingPlot()
        self.k2_timing_plot = TimingPlot()
        self.m1_timing_plot = TimingPlot()
        self.m2_timing_plot = TimingPlot()

        self.status_label = QtWidgets.QLabel()


    def __build_layout(self):
        self.visual.plotItem.hideButtons()
        self.timeline.plotItem.hideButtons()

        self.menu_bar.addMenu(self.file_menu)
        self.file_menu.addAction(self.open_map_action)
        self.file_menu.addAction(self.open_replay_action)

        self.__layout.addWidget(self.menu_bar)
        self.__layout.addWidget(self.visual)
        self.__layout.addWidget(self.timeline)
        self.__layout.addWidget(self.status_label)

        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(0)

        self.visual.addItem(self.plot_notes)
        self.visual.showGrid(True, True)
        self.visual.setXRange(0, 540)
        self.visual.setYRange(-410, 0)
        self.visual.getViewBox().setMouseEnabled(x=False, y=False)
        self.visual.enableAutoRange(axis='x', enable=False)
        self.visual.enableAutoRange(axis='y', enable=False)

        self.timeline.setFixedHeight(64)
        self.timeline.getViewBox().setMouseEnabled(y=False)
        self.timeline.hideAxis('left')
        self.timeline.setXRange(-1, 4)
        self.timeline.setYRange(-5, 5)

        self.timeline_marker.setBounds((-10000, None))
        self.timeline_marker.sigPositionChanged.connect(self.__time_changed_event)
        self.timeline_marker.sigPositionChanged.connect(lambda obj: self.time_changed_event.emit(obj.value()))

        self.timeline.addItem(self.hitobject_plot)
        self.timeline.addItem(self.k1_timing_plot)
        self.timeline.addItem(self.k2_timing_plot)
        self.timeline.addItem(self.m1_timing_plot)
        self.timeline.addItem(self.m2_timing_plot)
        self.timeline.addItem(self.timeline_marker, ignoreBounds=True)
        self.__time_changed_event()


    def set_time(self, time):
        self.timeline_marker.blockSignals(True)
        self.timeline_marker.setValue(time)
        self.__time_changed_event()
        self.timeline_marker.blockSignals(False)


    def set_map_reduced(self, data_x, data_y, data_t, cs, ar, md5=None):
        if isinstance(data_x, type(None)): return
        if isinstance(data_y, type(None)): return
        if isinstance(data_t, type(None)): return

        if isinstance(ar, type(None)): return
        if isinstance(cs, type(None)): return

        map_data = [
            pd.DataFrame(
            [
                [ t + 0, x, -y, StdMapData.TYPE_PRESS,   StdMapData.TYPE_CIRCLE ],
                [ t + 1, x, -y, StdMapData.TYPE_RELEASE, StdMapData.TYPE_CIRCLE ],
            ],
            columns=['time', 'x', 'y', 'type', 'object'])
            for t, x, y in zip(data_t, data_x, data_y)
        ]
        self.map_data = pd.concat(map_data, axis=0, keys=range(len(map_data)), names=[ 'hitobject', 'aimpoint' ])

        self.cs_px = OsuUtils.cs_to_px(cs)
        self.ar_ms = OsuUtils.ar_to_ms(ar)#/1000
        self.map_md5 = md5

        self.__draw_map_data()

        # Draw note in timeline
        self.hitobject_plot.set_map_timeline(self.map_data)
        self.timeline.update()


    def set_map_full(self, map_data, cs, ar, md5=None):
        if isinstance(map_data, type(None)): return
        if isinstance(cs, type(None)): return
        if isinstance(ar, type(None)): return

        self.map_data = map_data
        self.cs_px = OsuUtils.cs_to_px(cs)
        self.ar_ms = OsuUtils.ar_to_ms(ar)#/1000
        self.map_md5 = md5

        self.__draw_map_data()

        # Draw note in timeline
        self.hitobject_plot.set_map_timeline(self.map_data)
        self.timeline.update()


    def set_replay_from_replay_data(self, replay_data):
        if isinstance(replay_data, type(None)):
            return

        self.replay_data = np.zeros((len(replay_data['time']), 7))
        self.replay_data[:, self.REPLAY_T]  = np.asarray(replay_data['time'])#/1000
        self.replay_data[:, self.REPLAY_X]  = np.asarray(replay_data['x'])
        self.replay_data[:, self.REPLAY_Y]  = -np.asarray(replay_data['y'])
        self.replay_data[:, self.REPLAY_K1] = np.asarray(replay_data['k1'])
        self.replay_data[:, self.REPLAY_K2] = np.asarray(replay_data['k2'])
        self.replay_data[:, self.REPLAY_M1] = np.asarray(replay_data['m1'])
        self.replay_data[:, self.REPLAY_M2] = np.asarray(replay_data['m2'])

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
        self.replay_data[::2, self.REPLAY_K1]  = StdReplayData.PRESS

        # Release timings
        self.replay_data[1::2, self.REPLAY_T]  = score_data['T_HIT'] + 50
        self.replay_data[1::2, self.REPLAY_X]  = score_data['X_HIT']
        self.replay_data[1::2, self.REPLAY_Y]  = -score_data['Y_HIT']
        self.replay_data[1::2, self.REPLAY_K1] = StdReplayData.RELEASE

        self.__draw_replay_data()


    def new_replay_event(self, map_data, replay_data, cs, ar, mods, name):
        map_data = map_data.copy()
        #map_data['time'] /= 1000
        map_data['y'] = -map_data['y']

        mods = Mod(int(mods))

        if mods.has_mod(Mod.HardRock):
            cs *= 1.3
            ar *= 1.4

        if mods.has_mod(Mod.Easy):
            cs *= 0.5
            ar *= 0.5

        cs = min(cs, 10)
        ar = min(ar, 10)

        self.set_map_full(map_data, cs, ar)
        self.set_replay_from_replay_data(replay_data)

        # Draw note in timeline
        self.hitobject_plot.set_map_timeline(self.map_data)
        self.timeline.update()

        self.status_label.setText(f'Viewing: {name}')


    def set_from_score_data(self, score_data):
        num_entries = ScoreNpy.get_num_entries(score_data)
        if num_entries == 0:
            print('Error: No maps are selected')
            return

        num_maps = ScoreNpy.get_num_maps(score_data)
        if num_maps > 1:
            print('Warning: multiple maps are selected. Taking just the first one...')

        score_data = ScoreNpy.get_first_entry(score_data)
        md5 = ScoreNpy.get_first_entry_md5(score_data)

        self.set_replay_from_play_data(score_data)

        # In the event multiple md5 strings were passed, take just the first one
        map_file_name = self.__maps_db.get_map_file_name(md5)
        if map_file_name:
            try:
                self.__open_map_from_file_name(map_file_name, score_data.index.get_level_values(2)[0])

                # Draw notes in timeline
                self.hitobject_plot.set_map_timeline(self.map_data)
                self.timeline.update()
                return
            except:
                self.status_label.setText(f'Error: Unable to display map\n{map_file_name}.')
                return

        # Failed to find associated map; display from score data
        data_x = score_data['X_MAP'].values
        data_y = score_data['Y_MAP'].values
        data_t = score_data['T_MAP'].values
        cs = score_data['CS'][0]
        ar = score_data['AR'][0]

        self.set_map_reduced(data_x, data_y, data_t, cs, ar, md5=None)
        self.status_label.setText('Warning: viewing play data, which contains only the basic scoring information.')


    def __draw_map_data(self):
        if isinstance(self.map_data, type(None)):
            return

        if isinstance(self.ar_ms, type(None)): return
        if isinstance(self.cs_px, type(None)): return

        # Draw approach circles
        presses = StdMapData.get_presses(self.map_data)
        ar_select = (self.t <= presses['time']) & (presses['time'] <= (self.t + self.ar_ms))

        if ar_select.sum() == 0:
            # Nothing to draw
            self.plot_approach.setData([], [], symbolSize=[])
        else:
            approach_x =  presses['x'][ar_select].values
            approach_y =  presses['y'][ar_select].values
            press_times = presses['time'][ar_select].values

            sizes = OsuUtils.approach_circle_to_radius(self.cs_px, self.ar_ms, press_times - self.t)
            self.plot_approach.setData(approach_x, approach_y, symbolSize=sizes)

        # Draw notes
        self.plot_notes.set_map_display(self.t, self.map_data, self.ar_ms, self.cs_px)


    def __draw_replay_data(self):
        if isinstance(self.replay_data, type(None)):
            return

        replay_data_t = self.replay_data[:, self.REPLAY_T]

        select_time = (replay_data_t >= self.t - 50) & (replay_data_t <= self.t)
        replay_data_x = self.replay_data[select_time, self.REPLAY_X]
        replay_data_y = self.replay_data[select_time, self.REPLAY_Y]

        self.plot_cursor.setData(replay_data_x, replay_data_y)
        self.visual.update()

        k1_press_select = self.replay_data[:, self.REPLAY_K1] == StdReplayData.PRESS
        k2_press_select = self.replay_data[:, self.REPLAY_K2] == StdReplayData.PRESS
        m1_press_select = self.replay_data[:, self.REPLAY_M1] == StdReplayData.PRESS
        m2_press_select = self.replay_data[:, self.REPLAY_M2] == StdReplayData.PRESS

        k1_release_select = self.replay_data[:, self.REPLAY_K1] == StdReplayData.RELEASE
        k2_release_select = self.replay_data[:, self.REPLAY_K2] == StdReplayData.RELEASE
        m1_release_select = self.replay_data[:, self.REPLAY_M1] == StdReplayData.RELEASE
        m2_release_select = self.replay_data[:, self.REPLAY_M2] == StdReplayData.RELEASE

        self.timeline.removeItem(self.k1_timing_plot)
        self.k1_timing_plot = TimingPlot()
        self.k1_timing_plot.setTimings(
            self.replay_data[k1_press_select, self.REPLAY_T],
            self.replay_data[k1_release_select, self.REPLAY_T],
            y_pos=-4, color=(255, 100, 100, 150)
        )
        self.timeline.addItem(self.k1_timing_plot)

        self.timeline.removeItem(self.m1_timing_plot)
        self.m1_timing_plot = TimingPlot()
        self.m1_timing_plot.setTimings(
            self.replay_data[m1_press_select, self.REPLAY_T],
            self.replay_data[m1_release_select, self.REPLAY_T],
            y_pos=-2, color=(255, 100, 255, 150)
        )
        self.timeline.addItem(self.m1_timing_plot)

        self.timeline.removeItem(self.k2_timing_plot)
        self.k2_timing_plot = TimingPlot()
        self.k2_timing_plot.setTimings(
            self.replay_data[k2_press_select, self.REPLAY_T],
            self.replay_data[k2_release_select, self.REPLAY_T],
            y_pos=2, color=(71, 185, 255, 150)
        )
        self.timeline.addItem(self.k2_timing_plot)

        self.timeline.removeItem(self.m2_timing_plot)
        self.m2_timing_plot = TimingPlot()
        self.m2_timing_plot.setTimings(
            self.replay_data[m2_press_select, self.REPLAY_T],
            self.replay_data[m2_release_select, self.REPLAY_T],
            y_pos=4, color=(100, 255, 100, 150)
        )
        self.timeline.addItem(self.m2_timing_plot)

        self.timeline.update()


    def __time_changed_event(self):
        self.t = self.timeline_marker.getPos()[0]
        self.__draw_map_data()
        self.__draw_replay_data()


    def __open_map_dialog(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file',  f'{AppConfig.cfg["osu_dir"]}/Songs', 'osu! map files (*.osu)')
        file_name = file_name[0]

        if len(file_name) == 0:
            return

        self.__open_map_from_file_name(file_name)


    def open_map_from_osu_data(self, osu_data):
        try: beatmap = BeatmapIO.load_beatmap(osu_data)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error opening map'))
            return

        if beatmap.gamemode != Gamemode.OSU:
            print(f'{Gamemode(beatmap.gamemode)} gamemode is not supported')
            return

        try: map_data = StdMapData.get_map_data(beatmap)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error reading map'))
            return

        #map_data['time'] /= 1000
        map_data['y'] = -map_data['y']

        self.set_map_full(
            map_data,
            beatmap.difficulty.cs,
            beatmap.difficulty.ar,
            beatmap.metadata.beatmap_md5
        )

        self.map_text = beatmap.metadata.name
        viewing_text  = self.map_text + ' ' + self.replay_text
        self.status_label.setText(f'Viewing: {viewing_text}')


    def __open_map_from_file_name(self, file_name, mods=0):
        try: beatmap = BeatmapIO.open_beatmap(file_name)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error opening map'))
            raise

        if beatmap.gamemode != Gamemode.OSU:
            print(f'{Gamemode(beatmap.gamemode)} gamemode is not supported')
            raise Exception

        try: map_data = StdMapData.get_map_data(beatmap)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error reading map'))
            raise

        mods = Mod(int(mods))
        cs = beatmap.difficulty.cs
        ar = beatmap.difficulty.ar

        if mods.has_mod(Mod.HardRock):
            cs *= 1.3
            ar *= 1.4

        if mods.has_mod(Mod.Easy):
            cs *= 0.5
            ar *= 0.5

        cs = min(cs, 10)
        ar = min(ar, 10)

        if mods.has_mod(Mod.DoubleTime) or mods.has_mod(Mod.Nightcore):
            map_data['time'] *= 0.75

        if mods.has_mod(Mod.HalfTime):
            map_data['time'] *= 1.5

        #map_data['time'] /= 1000
        map_data['y'] = -map_data['y']

        self.set_map_full(map_data, cs, ar, beatmap.metadata.beatmap_md5)

        self.map_text = beatmap.metadata.name
        viewing_text = self.map_text + ' ' + self.replay_text
        self.status_label.setText(f'Viewing: {viewing_text}')


    def __open_replay_dialog(self):
        name_filter = 'osu! replay files (*.osr)' if self.map_md5 == None else f'osu! replay files ({self.map_md5}-*.osr)\nosu! replay files (*.osr)'

        file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Open replay',  f'{AppConfig.cfg["osu_dir"]}/Data/r', name_filter)
        file_name = file_name[0]

        if len(file_name) == 0:
            return

        self.__open_replay_from_file_name(file_name)


    def __open_replay_from_file_name(self, file_name):
        try: replay = ReplayIO.open_replay(file_name)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error opening replay'))
            return

        try: replay_data = StdReplayData.get_replay_data(replay)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error reading replay'))
            return

        self.set_replay_from_replay_data(replay_data)

        self.replay_text = replay.get_name()
        viewing_text = self.map_text + ' ' + self.replay_text
        self.status_label.setText(f'Viewing: {viewing_text}')

