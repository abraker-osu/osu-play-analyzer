import time
import os

import numpy as np

from PyQt5 import QtCore, QtWidgets

from osu_analysis import BeatmapIO, ReplayIO, Gamemode
from app.misc.utils import Utils
from app.misc.Logger import Logger

from app.data_recording.score_npy import ScoreNpy
from app.data_recording.diff_npy import DiffNpy
from app.data_recording.monitor import Monitor

from app.file_managers import AppConfig, MapsDB, score_data_obj


class _OsuRecorder(QtCore.QObject):

    logger = Logger.get_logger(__name__)

    new_replay_event = QtCore.pyqtSignal(tuple, bool)
    handle_new_replay = QtCore.pyqtSignal(str, bool, bool)

    def __init__(self):
        self.logger.debug('__init__ enter')

        QtCore.QObject.__init__(self)

        if not os.path.isdir(AppConfig.cfg['osu_dir']):
            return

        self.monitor = Monitor(AppConfig.cfg['osu_dir'])
        self.monitor.create_replay_monitor('Replay Grapher', lambda replay_file_name: self.handle_new_replay.emit(replay_file_name, True, False))
        self.handle_new_replay.connect(self.__handle_new_replay)

        self.logger.debug('__init__ exit')


    def start_monitor(self):
        self.monitor.start()


    def __handle_new_replay(self, replay_file_name, wait=True, is_import=False):
        if wait:
            # Needed sleep to wait for osu! to finish writing the replay file
            time.sleep(2)

        self.logger.info(f'Processing replay: {replay_file_name}')

        try: replay = ReplayIO.open_replay(replay_file_name)
        except Exception as e:
            self.logger.error(Utils.get_traceback(e, 'Error opening replay'))
            return

        QtWidgets.QApplication.processEvents()

        if score_data_obj.is_entry_exist(replay.beatmap_hash):
            self.logger.info(f'Replay already exists in data: {replay.beatmap_hash}')
            return

        if replay.game_mode != Gamemode.OSU:
            self.logger.info(f'{replay.game_mode} gamemode is not supported')
            return

        self.logger.debug('Determining beatmap...')
        map_file_name, is_gen = MapsDB.get_map_file_name(replay.beatmap_hash)
        if map_file_name == None:
            self.logger.info(f'Warning: file_name is None. Unable to open map for replay with beatmap hash {replay.beatmap_hash}')
            return

        try:
            beatmap = BeatmapIO.open_beatmap(map_file_name)
            if is_gen and (AppConfig.cfg['delete_gen'] == True):
                os.remove(map_file_name)
        except FileNotFoundError:
            self.logger.info(f'Warning: Map {map_file_name} not longer exists!')
            return
            
        QtWidgets.QApplication.processEvents()

        map_data, replay_data, score_data = ScoreNpy.compile_data(beatmap, replay)
        QtWidgets.QApplication.processEvents()

        # Save data and emit to notify other components that there is a new replay
        diff_data = DiffNpy.get_data(score_data)
        score_data = score_data.join(diff_data, on='IDXS')
        score_data_obj.append(replay.beatmap_hash, score_data)

        self.new_replay_event.emit(
            (
                map_data,
                replay_data,
                score_data,
                #beatmap.difficulty.cs, 
                #beatmap.difficulty.ar, 
                #replay.mods.value,
                beatmap.metadata.name + ' ' + replay.get_name(),
                replay.beatmap_hash,
            ), 
            is_import
        )


OsuRecorder = _OsuRecorder()
