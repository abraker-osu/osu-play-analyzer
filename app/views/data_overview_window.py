"""
Window displaying a grid of cells containing color fills representing presence of data
The data represented by the filled cells is based on a range, with transparancy indicating how many datapoints are in the given cell range

The user is able to select a range of cells in the grid display to filter/select the data they wish to view in the data_overview_window.
Clicking on a non selected cell will select it, and dragging the mouse will select a range of cells.
Clicking on a selected cell will deselect it, and dragging the mouse will deselect a range of cells.

Since the grid is 2D, only two attributes can be compared at a time. The user can select which attribute to compare by 
selecting which of the two attributes should be displayed in a dropdown on the side.

The is a selection menu on the side that allows the user to select which player's data to view and which timestamped play.

Design note: Maybe have a scatter plot instead. Really depends on how much data there is and how laggy it will get.
"""
import numpy as np
import pandas as pd

import time
from pyqtgraph.Qt import QtGui, QtCore

from app.misc.Logger import Logger
from app.widgets.play_list import PlayList
from app.widgets.plays_graph import PlaysGraph
from app.widgets.composition_viewer import CompositionViewer

from app.data_recording.diff_npy import DiffNpy
from app.data_recording.osu_recorder import OsuRecorder

from app.file_managers import AppConfig, score_data_obj


class DataOverviewWindow(QtGui.QWidget):

    logger = Logger.get_logger(__name__)

    show_map_event = QtCore.pyqtSignal(object, list)
    region_changed = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        self.logger.debug('__init__ enter')

        QtGui.QWidget.__init__(self, parent)

        self.selected_md5_strs = []

        self.setWindowTitle('Data overview')
        
        self.map_list = PlayList()
        self.composition_viewer = CompositionViewer()
        self.play_graph = PlaysGraph()

        self.show_map_btn = QtGui.QPushButton('Show map')
        self.status_label = QtGui.QLabel('')
        self.progress_bar = QtGui.QProgressBar()
        
        self.overview = QtGui.QWidget()
        self.overview_layout = QtGui.QVBoxLayout(self.overview)
        self.overview_layout.setContentsMargins(0, 0, 0, 0)
        self.overview_layout.addWidget(self.composition_viewer)
        self.overview_layout.addWidget(self.play_graph)
        self.overview_layout.addWidget(self.show_map_btn)
        self.overview_layout.addWidget(self.status_label)
        self.overview_layout.addWidget(self.progress_bar)

        self.splitter = QtGui.QSplitter()
        self.splitter.addWidget(self.overview)
        self.splitter.addWidget(self.map_list)

        self.file_menu = QtGui.QMenu("&File")

        self.open_replay_action = QtGui.QAction("&Open *.osr", triggered=lambda: self.__open_replay_dialog())
        self.file_menu.addAction(self.open_replay_action)

        self.recalc_difficulties = QtGui.QAction("&Recalculate difficulties", triggered=lambda: self.__recalc_difficulties())
        self.file_menu.addAction(self.recalc_difficulties)

        self.menu_bar = QtGui.QMenuBar()
        self.menu_bar.addMenu(self.file_menu)

        self.main_layout = QtGui.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.splitter)
        self.main_layout.setMenuBar(self.menu_bar)

        self.progress_bar.hide()

        # Connect signals
        self.map_list.map_selected.connect(self.__map_select_event)
        self.map_list.new_map_loaded.connect(self.composition_viewer.reset_roi_selections)

        self.play_graph.region_changed.connect(self.composition_viewer.set_composition_from_score_data)
        self.composition_viewer.region_changed.connect(self.region_changed)
        self.show_map_btn.clicked.connect(self.__show_map_event)

        self.logger.debug('__init__ exit')
        

    def new_replay_event(self, is_import, md5_str):
        self.logger.debug('new_replay_event')
        self.map_list.load_latest_play(is_import, md5_str)

    
    def __map_select_event(self, map_md5_strs):
        self.logger.debug('__map_select_event')
        self.selected_md5_strs = map_md5_strs
        self.play_graph.plot_plays(map_md5_strs)


    def __show_map_event(self):
        self.logger.debug('__show_map_event')

        self.composition_viewer.reset_roi_selections()
        score_data = self.composition_viewer.get_selected()

        if isinstance(score_data, type(None)):
            self.status_label.setText('No data selected')
            return

        timestamps = np.unique(score_data.index.get_level_values(0))

        if len(timestamps) == 0:
            self.status_label.setText('A play must be selected to show the map')
            return

        if len(timestamps) > 1:
            self.status_label.setText('Only one play must be selected to show the map')
            return

        self.status_label.setText('')
        self.show_map_event.emit(score_data, self.selected_md5_strs)


    def __open_replay_dialog(self):
        self.logger.debug('__open_replay_dialog')

        name_filter = 'osu! replay files (*.osr)'

        self.status_label.hide()
        self.progress_bar.show()

        file_names = QtGui.QFileDialog.getOpenFileNames(self, 'Open replay',  f'{AppConfig.cfg["osu_dir"]}', name_filter)[0]
        if len(file_names) == 0:
            return

        num_files = len(file_names)

        for file_name, i in zip(file_names, range(num_files)):
            OsuRecorder.handle_new_replay.emit(file_name, False, True)

            self.progress_bar.setValue(100 * i / num_files)
            QtGui.QApplication.processEvents()

        self.progress_bar.hide()
        self.status_label.show()


    def __recalc_difficulties(self):
        self.logger.debug('__recalc_difficulties')

        self.status_label.hide()
        self.progress_bar.show()
        
        # Go through the list of maps
        map_md5s = score_data_obj.get_entries()
        for i, map_md5 in enumerate(map_md5s):
            entry = score_data_obj.data(map_md5)

            # Get list of difficulty columns
            diff_cols = [ col for col in entry.columns if col.startswith('DIFF_') ]

            # Remove difficulty columns
            entry.drop(columns=diff_cols, inplace=True)

            # Go through the list of timestamps
            def recalc_diffs():
                timestamps = np.unique(entry.index.get_level_values(0))
                for timestamp in timestamps:
                    # TODO: Prob need to do it per-mod as well
                    data = entry.loc[timestamp]
                    diff_data = DiffNpy.get_data(data)
                    ret = data.join(diff_data, on='IDXS')

                    ret['TIMESTAMP'] = np.full(ret.shape[0], timestamp)
                    ret.reset_index(level=0, inplace=True)
                    ret.set_index(['TIMESTAMP', 'IDXS'], inplace=True)
                    yield ret

            data = pd.concat(recalc_diffs())
            score_data_obj.rewrite(map_md5, data)

            self.progress_bar.setValue(100 * i / len(map_md5s))
            QtGui.QApplication.processEvents()

        self.progress_bar.hide()
        self.status_label.show()

        self.composition_viewer.update_diff_data()
