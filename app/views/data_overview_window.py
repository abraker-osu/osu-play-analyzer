"""
The data overview window manages and displays loaded data. The are 3 data displays present:
    - On the left side is a list of all loaded plays. Each play is distinguished by a 
        unique md5 and mod combination. When a play is selected, the md5 and mod combinations
        are sent to the timeline

    - On the bottom is the timeline which displays plays with respect to time they were set.
        The user is able to select a range of replays. This data gets sent to the composition
        viewer

    - The composition viewer displays map specific skill data such as angles, distances, .. with
        respect to other skills.
"""
import os
import PyQt5

import numpy as np
import pandas as pd

from app.misc.Logger import Logger
from app.widgets.play_list import PlayList
from app.widgets.plays_graph import PlaysGraph
from app.widgets.composition_viewer import CompositionViewer

from app.data_recording.score_npy import ScoreNpy
from app.data_recording.diff_npy import DiffNpy

from app.file_managers import AppConfig, NpyManager


class DataOverviewWindow(PyQt5.QtWidgets.QWidget):

    logger = Logger.get_logger(__name__)

    replay_open_event = PyQt5.QtCore.pyqtSignal(str)
    show_map_event = PyQt5.QtCore.pyqtSignal(object, object)
    region_changed = PyQt5.QtCore.pyqtSignal(object, object)

    __SCORE_TEMP_FILE = './data/temp_score.h5'
    __DIFF_TEMP_FILE  = './data/temp_diff.h5'

    def __init__(self, parent=None):
        self.logger.debug('__init__ enter')

        PyQt5.QtWidgets.QWidget.__init__(self, parent)

        self.setWindowTitle('Data overview')
        
        self.__map_list = PlayList()
        self.__composition_viewer = CompositionViewer()
        self.__play_graph = PlaysGraph()

        self.__show_map_btn = PyQt5.QtWidgets.QPushButton('Show map')
        self.__status_label = PyQt5.QtWidgets.QLabel('')
        self.__progress_bar = PyQt5.QtWidgets.QProgressBar()
        
        self.__overview = PyQt5.QtWidgets.QWidget()
        self.__overview_layout = PyQt5.QtWidgets.QVBoxLayout(self.__overview)
        self.__overview_layout.setContentsMargins(0, 0, 0, 0)
        self.__overview_layout.addWidget(self.__composition_viewer)
        self.__overview_layout.addWidget(self.__play_graph)
        self.__overview_layout.addWidget(self.__show_map_btn)
        self.__overview_layout.addWidget(self.__status_label)
        self.__overview_layout.addWidget(self.__progress_bar)

        self.__splitter = PyQt5.QtWidgets.QSplitter()
        self.__splitter.addWidget(self.__overview)
        self.__splitter.addWidget(self.__map_list)

        self.__file_menu = PyQt5.QtWidgets.QMenu("&File")

        self.__open_data_action = PyQt5.QtWidgets.QAction("&Load data file (*.h5)", triggered=lambda: self.__open_data_dialog())
        self.__file_menu.addAction(self.__open_data_action)

        self.__open_replay_action = PyQt5.QtWidgets.QAction("&Add replay (*.osr)", triggered=lambda: self.__open_replay_dialog())
        self.__file_menu.addAction(self.__open_replay_action)

        self.__recalc_difficulties_action = PyQt5.QtWidgets.QAction("&Recalculate difficulties", triggered=lambda: self.__recalc_difficulties())
        self.__file_menu.addAction(self.__recalc_difficulties_action)

        self.__menu_bar = PyQt5.QtWidgets.QMenuBar()
        self.__menu_bar.addMenu(self.__file_menu)

        self.__main_layout = PyQt5.QtWidgets.QHBoxLayout(self)
        self.__main_layout.setContentsMargins(0, 0, 0, 0)
        self.__main_layout.addWidget(self.__splitter)
        self.__main_layout.setMenuBar(self.__menu_bar)

        self.__progress_bar.hide()

        self.__connect_signals()

        # Load temporary score file
        try: 
            self.__loaded_score_data = NpyManager(DataOverviewWindow.__SCORE_TEMP_FILE)
            self.__loaded_score_data.drop()
        except NpyManager.CorruptionError:
            os.remove(DataOverviewWindow.__SCORE_TEMP_FILE)
            self.__loaded_score_data = NpyManager(DataOverviewWindow.__SCORE_TEMP_FILE)

        # Load temporary difficulty file
        try: 
            self.__loaded_diff_data = NpyManager(DataOverviewWindow.__DIFF_TEMP_FILE)
            self.__loaded_diff_data.drop()
        except NpyManager.CorruptionError:
            os.remove(DataOverviewWindow.__DIFF_TEMP_FILE)
            self.__loaded_diff_data = NpyManager(DataOverviewWindow.__DIFF_TEMP_FILE)            

        self.logger.debug('__init__ exit')


    def __connect_signals(self):
        self.__map_list.map_selected.connect(self.__map_select_event)

        self.__play_graph.region_changed.connect(self.__timestamp_region_changed_event)
        self.__composition_viewer.region_changed.connect(self.region_changed)
        self.__show_map_btn.clicked.connect(self.show_map)

        
    def append_to_data(self, beatmap, replay):
        # Append to existing data
        map_data, replay_data, score_data = ScoreNpy.compile_data(beatmap, replay)
        self.__loaded_score_data.append(score_data)

        diff_data = DiffNpy.get_data(score_data)
        self.__loaded_diff_data.append(diff_data)

        # Load new data into play listings
        self.__map_list.load_play(diff_data)

        # Update timeline
        score_data = self.__get_score_data([ replay.beatmap_hash ])

        # Update timeline and composition viewer
        self.__play_graph.plot_plays(np.unique(score_data.index.get_level_values(1)))
        self.__composition_viewer.set_composition_from_score_data(score_data, diff_data)


    def is_exist(self, md5, timestamps=None, mods=None):
        return self.__loaded_score_data.is_entry_exist(md5, timestamps, mods)


    def __get_score_data(self, md5s, timestamps=[], mods=[]):
        if len(md5s) == 0:
            return ScoreNpy.get_blank_data()

        data = [ 
            df for idx, df in self.__loaded_score_data.data().groupby([ 'MD5', 'TIMESTAMP', 'MODS' ]) if 
                (idx[0] in md5s) and 
                (True if (len(timestamps) == 0) else (idx[1] in timestamps)) and 
                (True if (len(mods) == 0) else (idx[2] in mods))
        ]

        if len(data) == 0:
            return ScoreNpy.get_blank_data()

        return pd.concat(data)


    def __get_diff_data(self, md5s, timestamps=[], mods=[]):
        if len(md5s) == 0:
            return DiffNpy.get_blank_data()

        data = [ 
            df for idx, df in self.__loaded_diff_data.data().groupby([ 'MD5', 'TIMESTAMP', 'MODS' ]) if 
                (idx[0] in md5s) and 
                (True if (len(timestamps) == 0) else (idx[1] in timestamps)) and 
                (True if (len(mods) == 0) else (idx[2] in mods))
        ]

        if len(data) == 0:
            return DiffNpy.get_blank_data()

        return pd.concat(data)


    def __map_select_event(self, map_md5_strs):
        self.logger.debug('__map_select_event')

        score_data = self.__get_score_data(map_md5_strs)
        diff_data  = self.__get_diff_data(map_md5_strs)

        timestamps = np.unique(score_data.index.get_level_values(1))

        self.__play_graph.plot_plays(timestamps)
        self.__composition_viewer.set_composition_from_score_data(score_data, diff_data)
    

    def __timestamp_region_changed_event(self, data):
        selected_maps = self.__map_list.get_selected()
        
        score_data = self.__get_score_data(selected_maps, timestamps=data['timestamps'])
        diff_data = self.__get_diff_data(selected_maps, timestamps=data['timestamps'])

        self.__composition_viewer.set_composition_from_score_data(score_data, diff_data)
        self.__composition_viewer.emit_master_selection()

        if len(data['timestamps']) == 1:
            # self.__composition_viewer.reset_roi_selections()
            # score_data = self.__composition_viewer.get_selected()

            self.show_map_event.emit(score_data, diff_data)


    def show_map(self):
        self.logger.debug('show_map')

        self.__composition_viewer.reset_roi_selections()
        score_data, diff_data = self.__composition_viewer.get_selected()

        if isinstance(score_data, type(None)) or isinstance(diff_data, type(None)):
            self.__status_label.setText('No data selected')
            return

        timestamps = np.unique(score_data.index.get_level_values(0))
        md5s = self.__map_list.get_selected()

        if (len(md5s) == 0) or (len(timestamps) == 0):
            self.__status_label.setText('A play must be selected to show the map')
            return

        if (len(md5s) > 1) or (len(timestamps) > 1):
            self.__status_label.setText('Only one play must be selected to show the map')
            return

        self.__status_label.setText('')
        self.show_map_event.emit(score_data, diff_data)


    def __open_data_dialog(self):
        self.logger.debug('__open_data_dialog')

        name_filter = 'h5 files (*.h5)'
        
        file_pathname = PyQt5.QtWidgets.QFileDialog.getOpenFileName(self, 'Open data file',  f'./data', name_filter)[0]
        if len(file_pathname) == 0:
            return

        self.__loaded_score_data.close()
        self.__loaded_diff_data.close()

        try: self.__loaded_score_data = NpyManager(file_pathname)
        except NpyManager.CorruptionError:
            self.logger.error(f'Error reading {file_pathname}')
            return

        self.__loaded_diff_data = NpyManager(f'{file_pathname.split(".")[0]}_diff.h5')

        # TODO: Implement difficulty algo outdate detection
        outdated = False
        if outdated:
            self.__recalc_difficulties()
        else:
            self.__map_list.reload_map_list(self.__loaded_diff_data.data())


    def __open_replay_dialog(self):
        self.logger.debug('__open_replay_dialog')

        name_filter = 'osu! replay files (*.osr)'

        self.__status_label.hide()
        self.__progress_bar.show()

        file_names = PyQt5.QtWidgets.QFileDialog.getOpenFileNames(self, 'Open replay',  f'{AppConfig.cfg["osu_dir"]}', name_filter)[0]
        if len(file_names) == 0:
            return

        num_files = len(file_names)

        for file_name, i in zip(file_names, range(num_files)):
            self.replay_open_event.emit(file_name)

            self.__progress_bar.setValue(100 * i / num_files)
            PyQt5.QtWidgets.QApplication.processEvents()

        self.__progress_bar.hide()
        self.__status_label.show()


    def __recalc_difficulties(self):
        self.logger.debug('__recalc_difficulties')

        self.__status_label.hide()
        self.__progress_bar.show()
        
        # Go through the list of maps
        self.__loaded_diff_data.drop()

        map_list = self.__loaded_score_data.data().groupby([ 'MD5', 'TIMESTAMP', 'MODS' ])
        num_maps = len(map_list)

        for i, (idx, df) in enumerate(map_list):
            self.__loaded_diff_data.append(DiffNpy.get_data(df))

            self.__progress_bar.setValue(100 * i / num_maps)
            PyQt5.QtWidgets.QApplication.processEvents()

        self.__progress_bar.hide()
        self.__status_label.show()

        self.__map_list.reload_map_list(self.__loaded_diff_data.data())
        self.__composition_viewer.update_diff_data()
