import time

from PyQt5 import QtCore, QtWidgets 
import numpy as np
from app.data_recording.data import RecData

from osu_analysis import BeatmapIO, ReplayIO, Gamemode
from osu_analysis import StdScoreData

from app.data_recording.data_processing import DataProcessing
from app.data_recording.monitor import Monitor

from app.file_managers import AppConfig, MapsDB, PlayData


class _OsuRecorder(QtCore.QObject):

    new_replay_event = QtCore.pyqtSignal(tuple)

    SAVE_FILE = 'data/osu_performance_recording_v1.npy'

    def __init__(self):
        QtCore.QObject.__init__(self)

        self.monitor = Monitor(AppConfig.cfg['osu_dir'])
        self.monitor.create_replay_monitor('Replay Grapher', self.handle_new_replay)


    def __del__(self):
        PlayData.data_file.close()


    def handle_new_replay(self, replay_file_name, wait=True):
        if wait:
            # Needed sleep to wait for osu! to finish writing the replay file
            time.sleep(2)

        print('Processing replay:', replay_file_name)

        try: replay = ReplayIO.open_replay(replay_file_name)
        except Exception as e:
            print(f'Error opening replay: {e}')
            return

        QtWidgets.QApplication.processEvents()

        # Check if replay already exists in data
        unique_timestamps = np.unique(PlayData.data[:, RecData.TIMESTAMP])
        if replay.timestamp.timestamp() in unique_timestamps:
            print(f'Replay already exists in data: {replay.timestamp}')
            return

        if replay.game_mode != Gamemode.OSU:
            print(f'{replay.game_mode} gamemode is not supported')
            return

        print('Determining beatmap...')
        map_file_name = MapsDB.get_map_file_name(replay.beatmap_hash, md5h=False, reprocess_if_missing=wait)
        if len(map_file_name) == 0:
            return

        print('Processing beatmap:', map_file_name)
        beatmap = BeatmapIO.open_beatmap(map_file_name)
        QtWidgets.QApplication.processEvents()

        map_data = DataProcessing.get_map_data_from_object(beatmap)
        replay_data = DataProcessing.get_replay_data_from_object(replay)
        DataProcessing.process_mods(map_data, replay_data, replay)

        # Get data
        score_data = StdScoreData.get_score_data(replay_data, map_data)
        data = DataProcessing.get_data(score_data, replay.timestamp.timestamp(), beatmap.metadata.beatmap_md5, replay.mods.value, beatmap.difficulty.cs, beatmap.difficulty.ar)

        QtWidgets.QApplication.processEvents()

        # Save data and emit to notify other components that there is a new replay
        PlayData.save_data(data)
        self.new_replay_event.emit((map_data, replay_data, beatmap.difficulty.cs, beatmap.difficulty.ar, beatmap.metadata.name + ' ' + replay.get_name()))


    def __process_mods(self, map_data, replay_data, replay):
        mods = 0

        if replay.mods.has_mod('DT') or replay.mods.has_mod('NC'):
            mods |= (1 << 0)

        if replay.mods.has_mod('HT'):
            mods |= (1 << 1)

        if replay.mods.has_mod('MR'):
            num_keys = ManiaActionData.num_keys(map_data)
            map_data[:, ManiaActionData.IDX_COL] = (num_keys - 1) - map_data[:, ManiaActionData.IDX_COL]

        return mods


OsuRecorder = _OsuRecorder()