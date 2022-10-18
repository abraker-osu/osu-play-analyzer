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
        
        self.map_list = PlayList()
        self.composition_viewer = CompositionViewer()
        self.play_graph = PlaysGraph()

        self.show_map_btn = PyQt5.QtWidgets.QPushButton('Show map')
        self.status_label = PyQt5.QtWidgets.QLabel('')
        self.progress_bar = PyQt5.QtWidgets.QProgressBar()
        
        self.overview = PyQt5.QtWidgets.QWidget()
        self.overview_layout = PyQt5.QtWidgets.QVBoxLayout(self.overview)
        self.overview_layout.setContentsMargins(0, 0, 0, 0)
        self.overview_layout.addWidget(self.composition_viewer)
        self.overview_layout.addWidget(self.play_graph)
        self.overview_layout.addWidget(self.show_map_btn)
        self.overview_layout.addWidget(self.status_label)
        self.overview_layout.addWidget(self.progress_bar)

        self.splitter = PyQt5.QtWidgets.QSplitter()
        self.splitter.addWidget(self.overview)
        self.splitter.addWidget(self.map_list)

        self.file_menu = PyQt5.QtWidgets.QMenu("&File")

        self.open_data_action = PyQt5.QtWidgets.QAction("&Load data file (*.h5)", triggered=lambda: self.__open_data_dialog())
        self.file_menu.addAction(self.open_data_action)

        self.open_replay_action = PyQt5.QtWidgets.QAction("&Add replay (*.osr)", triggered=lambda: self.__open_replay_dialog())
        self.file_menu.addAction(self.open_replay_action)

        self.recalc_difficulties = PyQt5.QtWidgets.QAction("&Recalculate difficulties", triggered=lambda: self.__recalc_difficulties())
        self.file_menu.addAction(self.recalc_difficulties)

        self.menu_bar = PyQt5.QtWidgets.QMenuBar()
        self.menu_bar.addMenu(self.file_menu)

        self.main_layout = PyQt5.QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.splitter)
        self.main_layout.setMenuBar(self.menu_bar)

        self.progress_bar.hide()

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
        self.map_list.map_selected.connect(self.__map_select_event)

        self.play_graph.region_changed.connect(self.__timestamp_region_changed_event)
        self.composition_viewer.region_changed.connect(self.region_changed)
        self.show_map_btn.clicked.connect(self.__show_map_event)

        
    def append_to_data(self, beatmap, replay):
        # Append to existing data
        map_data, replay_data, score_data = ScoreNpy.compile_data(beatmap, replay)
        self.__loaded_score_data.append(score_data)

        diff_data = DiffNpy.get_data(score_data)
        self.__loaded_diff_data.append(diff_data)

        # Load new data into play listings
        self.map_list.load_play(diff_data)

        # Update timeline
        score_data = self.get_score_data([ replay.beatmap_hash ])

        # Update timeline and composition viewer
        self.play_graph.plot_plays(np.unique(score_data.index.get_level_values(1)))
        self.composition_viewer.set_composition_from_score_data(score_data, diff_data)


    def get_loaded_data(self):
        return self.__loaded_score_data


    def get_score_data(self, md5s, timestamps=[], mods=[]):
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


    def get_diff_data(self, md5s, timestamps=[], mods=[]):
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

        score_data = self.get_score_data(map_md5_strs)
        diff_data  = self.get_diff_data(map_md5_strs)

        timestamps = np.unique(score_data.index.get_level_values(1))

        self.play_graph.plot_plays(timestamps)
        self.composition_viewer.set_composition_from_score_data(score_data, diff_data)
    

    def __timestamp_region_changed_event(self, data):
        selected_maps = self.map_list.get_selected()
        
        score_data = self.get_score_data(selected_maps, timestamps=data['timestamps'])
        diff_data = self.get_diff_data(selected_maps, timestamps=data['timestamps'])

        self.composition_viewer.set_composition_from_score_data(score_data, diff_data)
        self.composition_viewer.emit_master_selection()

        # if len(data['timestamps']) == 1:
        #     self.composition_viewer.reset_roi_selections()
        #     score_data = self.composition_viewer.get_selected()

        #     self.show_map_event.emit(score_data, data['md5_strs'])


    def __show_map_event(self):
        self.logger.debug('__show_map_event')

        self.composition_viewer.reset_roi_selections()
        score_data, diff_data = self.composition_viewer.get_selected()

        if isinstance(score_data, type(None)) or isinstance(diff_data, type(None)):
            self.status_label.setText('No data selected')
            return

        timestamps = np.unique(score_data.index.get_level_values(0))
        md5s = self.map_list.get_selected()

        if (len(md5s) == 0) or (len(timestamps) == 0):
            self.status_label.setText('A play must be selected to show the map')
            return

        if (len(md5s) > 1) or (len(timestamps) > 1):
            self.status_label.setText('Only one play must be selected to show the map')
            return

        self.status_label.setText('')
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
            self.map_list.reload_map_list(self.__loaded_diff_data.data())


    def __open_replay_dialog(self):
        self.logger.debug('__open_replay_dialog')

        name_filter = 'osu! replay files (*.osr)'

        self.status_label.hide()
        self.progress_bar.show()

        file_names = PyQt5.QtWidgets.QFileDialog.getOpenFileNames(self, 'Open replay',  f'{AppConfig.cfg["osu_dir"]}', name_filter)[0]
        if len(file_names) == 0:
            return

        num_files = len(file_names)

        for file_name, i in zip(file_names, range(num_files)):
            self.replay_open_event.emit(file_name)

            self.progress_bar.setValue(100 * i / num_files)
            PyQt5.QtWidgets.QApplication.processEvents()

        self.progress_bar.hide()
        self.status_label.show()


    def __recalc_difficulties(self):
        self.logger.debug('__recalc_difficulties')

        self.status_label.hide()
        self.progress_bar.show()
        
        # Go through the list of maps
        self.__loaded_diff_data.drop()

        map_list = self.__loaded_score_data.data().groupby([ 'MD5', 'TIMESTAMP', 'MODS' ])
        num_maps = len(map_list)

        for i, (idx, df) in enumerate(map_list):
            self.__loaded_diff_data.append(DiffNpy.get_data(df))

            self.progress_bar.setValue(100 * i / num_maps)
            PyQt5.QtWidgets.QApplication.processEvents()

        self.progress_bar.hide()
        self.status_label.show()

        self.map_list.reload_map_list(self.__loaded_diff_data.data())
        self.composition_viewer.update_diff_data()
