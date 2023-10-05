import json
import os
import sys
import traceback
import time
import numpy as np

import PyQt5

from osu_analysis import BeatmapIO, Gamemode

from app.misc.Logger import Logger
from app.file_managers import AppConfig


"""
GUI Display Feature Settings
"""
__DATA_GRAPHS_EN__   = True
__MAP_ARCHITECT_EN__ = True
__MAP_DISPLAY_EN__   = True

"""
Automatic Processes Feature Settings
"""
__AUTO_RECORDER_EN__ = True

from app.views.data_overview_window import DataOverviewWindow
if __DATA_GRAPHS_EN__:   from app.views.data_graphs_window   import DataGraphsWindow
if __MAP_ARCHITECT_EN__: from app.views.map_architect_window import MapArchitectWindow
if __MAP_DISPLAY_EN__:   from app.views.map_display_window   import MapDisplayWindow

from osu_recorder import OsuRecorder


"""
Set numpy settings
"""
np.set_printoptions(suppress=True)



"""
Fix pyqtgraph's csv exporting
"""
from pyqtgraph.exporters.CSVExporter import CSVExporter
from app.misc.pyqtgraph_fixes import plot_csv_export

CSVExporter.export = plot_csv_export



"""
Override default exception hook
"""
sys._excepthook = sys.excepthook
def exception_hook(exctype, value, tb):
    sys.__excepthook = (exctype, value, tb)

    trace = ''.join(traceback.format_exception(exctype, value, tb))
    Logger.get_logger('core').exception(trace)

    # Log assertion errors, but don't exit because of them
    if exctype == AssertionError:
        return

    #score_data_obj.save_data_and_close()
    #diff_data_obj.save_data_and_close()
    sys.exit(1)
sys.excepthook = exception_hook


"""
Main app class
"""
class App(PyQt5.QtWidgets.QMainWindow):

    __play_handler_signal = PyQt5.QtCore.pyqtSignal(object, object)

    logger = Logger.get_logger(__name__)
    debug = True

    def __init__(self):
        PyQt5.QtWidgets.QMainWindow.__init__(self)

        self.__contruct_gui_stage1()

        if not os.path.isdir(AppConfig.cfg['osu_dir']):
            msg = PyQt5.QtWidgets.QMessageBox()
            msg.setIcon(PyQt5.QtWidgets.QMessageBox.Information)
            msg.setWindowTitle('osu! folder config')
            msg.setText('Locate your osu! folder')
            msg.setStandardButtons(PyQt5.QtWidgets.QMessageBox.Ok)
            msg.exec_()

            osu_dir = str(PyQt5.QtWidgets.QFileDialog.getExistingDirectory(self, 'Select osu! folder'))
            if len(osu_dir) == 0:
                self.status_text.setText(
                    'Invalid osu! path! Alternatively find config.json in app folder and edit it.\n' + \
                    'Then restart the app.\n' + \
                    'Make sure to use double backslashes for osu! path (ex: "C:\\\\Games\\\\osu!")\n'
                )

                self.data_overview_button.setEnabled(False)
                self.data_graphs_button.setEnabled(False)
                self.map_architect_button.setEnabled(False)
                self.map_display_button.setEnabled(False)

                return

            AppConfig.cfg['osu_dir'] = osu_dir
            with open('config.json', 'w') as f:
                json.dump(AppConfig.cfg, f, indent=4)

        self.__osu_recorder = OsuRecorder(AppConfig.cfg['osu_dir'], callback=self.__play_handler_signal.emit)

        if __AUTO_RECORDER_EN__:
            self.__osu_recorder.start(self.__play_handler_signal.emit)

        self.__construct_gui_state2()
        self.__connect_signals()
        self.__load_data()


    def __contruct_gui_stage1(self):
        """
        Stage 1 Constructs the initial main selection
        window that's visible at the start.
        """
        self.logger.debug('__construct_gui_state1 start')

        self.setWindowTitle('osu! performance analyzer')

        self.data_overview_button = PyQt5.QtWidgets.QPushButton('Data overview')
        self.data_overview_button.clicked.connect(self.data_overview_button_clicked)
        self.data_overview_button.setToolTip('Select maps and view their composition')

        self.data_graphs_button = PyQt5.QtWidgets.QPushButton('Data graphs')
        self.data_graphs_button.clicked.connect(self.data_graphs_button_clicked)
        self.data_graphs_button.setToolTip('View map metrics and statistics')

        self.map_architect_button = PyQt5.QtWidgets.QPushButton('Map architect')
        self.map_architect_button.clicked.connect(self.map_architect_button_clicked)
        self.map_architect_button.setToolTip('Generate maps for player performance data recording')

        self.map_display_button = PyQt5.QtWidgets.QPushButton('Map display')
        self.map_display_button.clicked.connect(self.map_display_button_clicked)
        self.map_display_button.setToolTip('Display selected and generated map')

        self.status_text = PyQt5.QtWidgets.QLabel()
        self.main_widget = PyQt5.QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)

        self.layout = PyQt5.QtWidgets.QVBoxLayout(self.main_widget)
        self.layout.addWidget(self.data_overview_button)
        self.layout.addWidget(self.data_graphs_button)
        self.layout.addWidget(self.map_architect_button)
        self.layout.addWidget(self.map_display_button)
        self.layout.addWidget(self.status_text)

        self.setFixedWidth(480)
        self.show()

        self.logger.debug('__construct_gui_state1 end')


    def __construct_gui_state2(self):
        """
        Stage 2 Constructs everything else - windows that show
        when selecting options on main window.

        The two stages are needed because certain components depend
        on `osu_path` being valid, and to ensure that is true, stage 2
        is conditionally run only if it is valid.
        """
        self.logger.debug('__construct_gui_state2 start')

        self.data_overview_window = DataOverviewWindow()
        if __DATA_GRAPHS_EN__:   self.data_graphs_window   = DataGraphsWindow()
        if __MAP_DISPLAY_EN__:   self.map_display_window   = MapDisplayWindow()
        if __MAP_ARCHITECT_EN__: self.map_architect_window = MapArchitectWindow()

        self.logger.debug('__construct_gui_state2 end')


    def __connect_signals(self):
        self.logger.debug('Connecting signals start')

        if __DATA_GRAPHS_EN__:
            self.data_overview_window.show_map_event.connect(self.data_graphs_window.overview_single_map_selection_event)
            self.data_overview_window.region_changed.connect(self.data_graphs_window.set_from_play_data)

            if __MAP_DISPLAY_EN__:
                self.data_graphs_window.time_changed_event.connect(self.map_display_window.set_time)
                self.map_display_window.time_changed_event.connect(self.data_graphs_window.set_time)

        self.data_overview_window.replay_open_event.connect(self.__osu_recorder.handle_new_replay)

        if __MAP_DISPLAY_EN__:
            self.data_overview_window.show_map_event.connect(self.map_display_window.set_from_score_data)

            if __MAP_ARCHITECT_EN__:
                self.map_architect_window.gen_map_event.connect(self.map_display_window.set_from_generated)

        self.__play_handler_signal.connect(self.__play_handler)

        self.logger.debug('Connecting signals end')


    def __load_data(self):
        #self.data_overview_window.map_list.reload_map_list(score_data_obj.data())
        pass


    def data_overview_button_clicked(self):
        self.logger.info_debug(App.debug, 'data_overview_button_clicked')
        self.data_overview_window.show()


    def data_graphs_button_clicked(self):
        self.logger.info_debug(App.debug, 'data_graphs_button_clicked')

        if __DATA_GRAPHS_EN__:
            self.data_graphs_window.show()


    def map_architect_button_clicked(self):
        self.logger.info_debug(App.debug, 'map_architect_button_clicked')

        if __MAP_ARCHITECT_EN__:
            self.map_architect_window.show()


    def map_display_button_clicked(self):
        self.logger.info_debug(App.debug, 'map_display_button_clicked')

        if __MAP_DISPLAY_EN__:
            self.map_display_window.show()


    def __play_handler(self, beatmap, replay):
        self.logger.info_debug(App.debug, '__play_handler')

        # Needed sleep to wait for osu! to finish writing the replay file
        time.sleep(2)

        if self.data_overview_window.is_exist(replay.beatmap_hash, replay.timestamp):
            self.logger.info(f'Replay already exists in data: md5={replay.beatmap_hash}  timestamp={replay.timestamp}')
            return

        if replay.game_mode != Gamemode.OSU:
            self.logger.info(f'{replay.game_mode} gamemode is not supported')
            return

        is_import = False

        if beatmap is None:
            # See if it's a generated map, it has its md5 hash in the name
            map_file_name = f'{AppConfig.cfg["osu_dir"]}/Songs/osu_play_analyzer/{replay.beatmap_hash}.osu'
            if not os.path.isfile(map_file_name):
                self.logger.warning(f'Map {map_file_name} not longer exists!')
                return

            try:
                beatmap = BeatmapIO.open_beatmap(map_file_name)
                if AppConfig.cfg['delete_gen'] == True:
                    os.remove(map_file_name)

                is_import = True
            except FileNotFoundError:
                self.logger.warning(f'Map {map_file_name} not longer exists!')
                return

        self.data_overview_window.append_to_data(beatmap, replay)
        self.data_overview_window.show_map()

        #self.logger.debug(f'data_overview_window load time: {time.time() - time_start}')

        #if not is_import:
        #    time_start = time.time()
        #    self.data_graphs_window.new_replay_event(score_data)
        #    self.logger.debug(f'data_graphs_window load time:: {time.time() - time_start}')

        #    cs   = score_data['CS'].values[0]
        #    ar   = score_data['AR'].values[0]
        #    mods = score_data['MODS'].values[0]

        #    time_start = time.time()
        #    self.map_display_window.new_replay_event(map_data, replay_data, cs, ar, mods, name)
        #    self.logger.debug(f'map_display_window load time: {time.time() - time_start}')


    def closeEvent(self, event):
        self.logger.info_debug(App.debug, 'closeEvent')

        # Gracefully stop monitoring
        #if self.engaged:
        #    self.__action_event()
        #score_data_obj.save_data_and_close()
        #diff_data_obj.save_data_and_close()

        # Hide any widgets to allow the app to close
        try:
            self.data_overview_window.hide()
            if __DATA_GRAPHS_EN__:   self.data_graphs_window.hide()
            if __MAP_ARCHITECT_EN__: self.map_architect_window.hide()
            if __MAP_DISPLAY_EN__:   self.map_display_window.hide()
        except AttributeError:
            pass

        # Proceed
        event.accept()
