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
from pyqtgraph.Qt import QtGui, QtCore

from app.widgets.play_list import PlayList
from app.widgets.plays_graph import PlaysGraph
from app.widgets.composition_viewer import CompositionViewer

from app.data_recording.data import RecData
from app.data_recording.osu_recorder import OsuRecorder

from app.file_managers import AppConfig


class DataOverviewWindow(QtGui.QWidget):

    show_map_event = QtCore.pyqtSignal(object)
    region_changed = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.map_list_data = []
        self.selected_map_hash = None

        self.setWindowTitle('Data overview')
        
        self.map_list = PlayList()

        self.composition_viewer = CompositionViewer()
        self.play_graph = PlaysGraph()
        self.show_map_btn = QtGui.QPushButton('Show map')
        self.status_label = QtGui.QLabel('')
        
        self.overview = QtGui.QWidget()
        self.overview_layout = QtGui.QVBoxLayout(self.overview)
        self.overview_layout.setContentsMargins(0, 0, 0, 0)
        self.overview_layout.addWidget(self.composition_viewer)
        self.overview_layout.addWidget(self.play_graph)
        self.overview_layout.addWidget(self.show_map_btn)
        self.overview_layout.addWidget(self.status_label)

        self.splitter = QtGui.QSplitter()
        self.splitter.addWidget(self.overview)
        self.splitter.addWidget(self.map_list)

        self.file_menu = QtGui.QMenu("&File")
        self.open_replay_action = QtGui.QAction("&Open *.osr", triggered=lambda: self.__open_replay_dialog())
        self.file_menu.addAction(self.open_replay_action)

        self.menu_bar  = QtGui.QMenuBar()
        self.menu_bar.addMenu(self.file_menu)

        self.main_layout = QtGui.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.splitter)
        self.main_layout.setMenuBar(self.menu_bar)

        self.map_list.map_selected.connect(self.__map_select_event)
        self.play_graph.region_changed.connect(self.composition_viewer.set_composition_from_play_data)
        self.composition_viewer.region_changed.connect(self.region_changed)
        self.show_map_btn.clicked.connect(self.__show_map_event)
        

    def new_replay_event(self):
        self.map_list.load_latest_play()

    
    def __map_select_event(self, play_data):
        self.play_graph.plot_plays(play_data)


    def __show_map_event(self):
        play_data = self.composition_viewer.get_selected()
        unique_timestamps = np.unique(play_data[:, RecData.TIMESTAMP])

        if unique_timestamps.size == 0:
            self.status_label.setText('A play must be selected to show the map')
            return

        if unique_timestamps.size > 1:
            self.status_label.setText('Only one play must be selected to show the map')
            return

        self.status_label.setText('')
        self.show_map_event.emit(play_data)


    def __open_replay_dialog(self):
        name_filter = 'osu! replay files (*.osr)'

        file_names = QtGui.QFileDialog.getOpenFileNames(self, 'Open replay',  f'{AppConfig.cfg["osu_dir"]}', name_filter)
        for file_name in file_names[0]:
            if len(file_name) == 0:
                continue

            OsuRecorder.handle_new_replay(file_name, wait=False)