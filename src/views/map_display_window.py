"""
Window that allows to view beatmaps and replays.

Different tabs available:
* Selected:
    - Currently selected beatmap/replay from overview window
    - Latest played beatmap/replay detected
    - Custom loaded beatmap/replay
- Generated:
    - Generated beatmap/replay from the map architect window
- Processed:
    - A special view of the beatmap that reorients patterns
      to a common axis and displays 3 notes at a time
      (prev, current, next). This is used to get a sense of
      what the processing alogrithm is doing.

      Map viewed here is same as in the selected tab.
"""
import pandas as pd

from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets

from osu_analysis import StdMapData

from misc.Logger import Logger
from widgets.map_display import MapDisplay
from widgets.mouse_graph import MouseGraph
from widgets.map_mouse_graph import MapMouseGraph

from file_managers import AppConfig


class MapDisplayWindow(QtWidgets.QMainWindow):

    logger = Logger.get_logger(__name__)

    time_changed_event = QtCore.pyqtSignal(object)

    def __init__(self, parent = None):
        self.logger.debug('__init__ enter')

        QtWidgets.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Map Display')

        self.widget = QtWidgets.QWidget()
        self.setCentralWidget(self.widget)

        self.__layout = QtWidgets.QVBoxLayout()
        self.widget.setLayout(self.__layout)

        self.menu_bar = QtWidgets.QMenuBar()
        self.__layout.addWidget(self.menu_bar)

        self.file_menu = QtWidgets.QMenu("&File")
        self.menu_bar.addMenu(self.file_menu)

        self.open_map_action = QtGui.QAction('&Open *.osu')
        self.open_map_action.triggered.connect(self.__open_map_dialog)
        self.file_menu.addAction(self.open_map_action)

        self.open_replay_action = QtGui.QAction('&Open *.osr')
        self.open_replay_action.triggered.connect(self.__open_replay_dialog)
        self.file_menu.addAction(self.open_replay_action)

        self.disp_tabs = QtWidgets.QTabWidget()
        self.__layout.addWidget(self.disp_tabs)

        self.map_tabs = QtWidgets.QTabWidget()
        self.disp_tabs.addTab(self.map_tabs, 'Map Displays')

        self.map_display_selected = MapDisplay()
        self.map_tabs.addTab(self.map_display_selected, 'Selected')

        self.map_display_generated = MapDisplay()
        self.map_tabs.addTab(self.map_display_generated, 'Generated')

        self.map_display_processed = MapDisplay()
        self.map_tabs.addTab(self.map_display_processed, 'Processed')

        self.graph_mouse = MouseGraph()
        self.disp_tabs.addTab(self.graph_mouse, 'Replay Graphs')

        self.graph_map_mouse = MapMouseGraph()
        self.disp_tabs.addTab(self.graph_map_mouse, 'Map mouse graph')

        self.map_display_selected.time_changed_event.connect(self.time_changed_event)

        self.logger.debug('__init__ exit')


    def set_from_score_data(self, score_data):
        self.map_display_selected.set_from_score_data(score_data)

        '''
        cs = score_data['cs'][0]
        data_x = np.zeros(len(score_data)*3)
        data_y = np.zeros(len(score_data)*3)
        data_t = np.zeros(len(score_data)*3)

        data_x[0::3] = 200
        data_y[0::3] = -300
        data_t[0::3] = score_data[:-2, ]

        data_x[1::3] = 200
        data_y[1::3] = -300
        data_t[1::3] = score_data[1:-1, ]

        data_x[2::3] = -200
        data_y[2::3] = -300
        data_t[2::3] = score_data[2:, ]
        '''


    def new_replay_event(self, map_data, replay_data, cs, ar, mods, name):
        self.logger.debug('new_replay_event')
        self.map_display_selected.new_replay_event(map_data, replay_data, cs, ar, mods, name)


    def set_time(self, time):
        self.map_display_selected.set_time(time)


    def set_from_generated(self, osu_data):
        self.map_display_generated.open_map_from_osu_data(osu_data)


    def set_from_generated_old(self, gen_data, cs, ar):
        map_data = [
            pd.DataFrame(
            [
                [ t + 0, x, y, StdMapData.TYPE_PRESS,   StdMapData.TYPE_CIRCLE ],
                [ t + 1, x, y, StdMapData.TYPE_RELEASE, StdMapData.TYPE_CIRCLE ],
            ],
            columns=['time', 'x', 'y', 'type', 'object'])
            for t, x, y in zip(gen_data[:, 0], gen_data[:, 1], gen_data[:, 2])
        ]
        map_data = pd.concat(map_data, axis=0, keys=range(len(map_data)), names=[ 'hitobject', 'aimpoint' ])

        #map_data['time'] /= 1000
        map_data['y'] = -map_data['y']

        self.map_display_generated.set_map_full(map_data, cs, ar)


    def __open_replay_dialog(self):
        name_filter = 'osu! replay files (*.osr)'
        if self.map_display_selected.map_md5 is not None:
            name_filter = f'osu! replay files ({self.map_display_selected.map_md5}-*.osr)\nosu! replay files (*.osr)'

        file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Open replay',  f'{AppConfig.cfg["osu_dir"]}/Data/r', name_filter)
        file_name = file_name[0]

        if len(file_name) == 0:
            return

        self.map_display_selected.open_replay_from_file_name(file_name)
        self.graph_mouse.open_replay_from_file_name(file_name)
        self.graph_map_mouse.open_replay_from_file_name(file_name)


    def __open_map_dialog(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file',  f'{AppConfig.cfg["osu_dir"]}/Songs', 'osu! map files (*.osu)')
        file_name = file_name[0]

        if len(file_name) == 0:
            return

        self.map_display_selected.open_map_from_file_name(file_name)
        self.graph_map_mouse.open_map_from_file_name(file_name)

