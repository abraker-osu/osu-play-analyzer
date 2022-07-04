import os
import sys
import traceback
import time
import numpy as np

from pyqtgraph.Qt import QtGui

from app.misc.Logger import Logger
from app.views.data_graphs_window import DataGraphsWindow
from app.views.data_overview_window import DataOverviewWindow
from app.views.map_architect_window import MapArchitectWindow
from app.views.map_display_window import MapDisplayWindow

from app.file_managers import AppConfig, MapsDB
from app.data_recording.osu_recorder import OsuRecorder

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
class App(QtGui.QMainWindow):

    logger = Logger.get_logger(__name__)
    debug = True

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        os.makedirs('data', exist_ok=True)

        MapsDB.check_db()

        self.__contruct_gui()
        self.__connect_signals()

        OsuRecorder.start_monitor()


    def __contruct_gui(self):
        self.logger.debug('Constructing GUI start')

        self.data_graphs_window   = DataGraphsWindow()
        self.data_overview_window = DataOverviewWindow()
        self.map_display_window   = MapDisplayWindow()
        self.map_architect_window = MapArchitectWindow()

        self.setWindowTitle('osu! performance analyzer')

        self.generate_map_button = QtGui.QPushButton('Generate map')
        self.generate_map_button.clicked.connect(self.generate_map_button_clicked)
        self.generate_map_button.setToolTip('Figure settings to use to generate maps for data recording')

        self.analyze_data_button = QtGui.QPushButton('Analyze data')
        self.analyze_data_button.clicked.connect(self.analyze_data_button_clicked)
        self.analyze_data_button.setToolTip('Analyze data gathered from data recording')

        self.record_data_button = QtGui.QPushButton('Record data')
        self.record_data_button.clicked.connect(self.record_data_button_clicked)
        self.record_data_button.setToolTip('Generate maps for player performance data recording')

        self.browse_plays_button = QtGui.QPushButton('Browse plays')
        self.browse_plays_button.clicked.connect(self.browse_plays_button_clicked)
        self.browse_plays_button.setToolTip('Look through data recordings made by you and other players')

        self.train_skills_button = QtGui.QPushButton('Train skills')
        self.train_skills_button.clicked.connect(self.train_skills_button_clicked)
        self.train_skills_button.setToolTip('See your performance as you play maps')

        self.status_text = QtGui.QLabel()
        if not os.path.isdir(AppConfig.cfg['osu_dir']):
            self.status_text.setText(
                'Invalid osu! path! Find config.json in app folder and edit it.\n' + \
                'Then restart the app.\n' + \
                'Make sure to use double backslashes for osu! path (ex: "C:\\\\Games\\\\osu!")\n'
            )

            self.generate_map_button.setEnabled(False)
            self.analyze_data_button.setEnabled(False)
            self.record_data_button.setEnabled(False)
            self.browse_plays_button.setEnabled(False)
            self.train_skills_button.setEnabled(False)

        self.main_widget = QtGui.QWidget()
        self.setCentralWidget(self.main_widget)

        self.layout = QtGui.QVBoxLayout(self.main_widget)
        self.layout.addWidget(self.generate_map_button)
        self.layout.addWidget(self.analyze_data_button)
        self.layout.addWidget(self.record_data_button)
        self.layout.addWidget(self.browse_plays_button)
        self.layout.addWidget(self.train_skills_button)
        self.layout.addWidget(self.status_text)

        self.setFixedWidth(480)
        self.show()

        self.logger.debug('Constructing GUI end')


    def __connect_signals(self):
        self.logger.debug('Connecting signals start')

        OsuRecorder.new_replay_event.connect(self.new_replay_event)
        
        self.data_overview_window.show_map_event.connect(self.map_display_window.set_from_play_data)
        self.data_overview_window.show_map_event.connect(self.data_graphs_window.overview_single_map_selection_event)
        self.data_overview_window.region_changed.connect(self.data_graphs_window.set_from_play_data)

        self.map_architect_window.gen_map_event.connect(self.map_display_window.set_from_generated)

        self.logger.debug('Connecting signals end')


    def generate_map_button_clicked(self):
        self.logger.info_debug(App.debug, 'generate_map_button_clicked')

        self.data_graphs_window.hide() 
        self.data_overview_window.show()
        self.map_display_window.show()
        self.map_architect_window.show()


    def analyze_data_button_clicked(self):
        self.logger.info_debug(App.debug, 'analyze_data_button_clicked')

        self.data_graphs_window.show() 
        self.data_overview_window.show()
        self.map_display_window.hide()
        self.map_architect_window.hide()


    def record_data_button_clicked(self):
        self.logger.info_debug(App.debug, 'record_data_button_clicked')

        self.data_graphs_window.show() 
        self.data_overview_window.hide()
        self.map_display_window.hide()
        self.map_architect_window.show()


    def browse_plays_button_clicked(self):
        self.logger.info_debug(App.debug, 'browse_plays_button_clicked')

        self.data_graphs_window.hide() 
        self.data_overview_window.show()
        self.map_display_window.show()
        self.map_architect_window.hide()


    def train_skills_button_clicked(self):
        self.logger.info_debug(App.debug, 'train_skills_button_clicked')

        self.data_graphs_window.show() 
        self.data_overview_window.hide()
        self.map_display_window.show()
        self.map_architect_window.hide()


    def new_replay_event(self, data, is_import):
        self.logger.debug('new_replay_event - enter')

        map_data, replay_data, score_data, name, md5_str = data

        cs   = score_data['CS'].values[0]
        ar   = score_data['AR'].values[0]
        mods = score_data['MODS'].values[0]

        # Broadcast the new replay event to the other windows
        time_start = time.time()
        self.data_overview_window.new_replay_event(is_import, md5_str)
        self.logger.debug(f'data_overview_window load time: {time.time() - time_start}')

        if not is_import:
            time_start = time.time()
            self.data_graphs_window.new_replay_event(score_data)
            self.logger.debug(f'data_graphs_window load time:: {time.time() - time_start}')

            time_start = time.time()
            self.map_display_window.new_replay_event(map_data, replay_data, cs, ar, mods, name)
            self.logger.debug(f'map_display_window load time: {time.time() - time_start}')
        self.logger.debug('new_replay_event - exit')


    def closeEvent(self, event):
        self.logger.info_debug(App.debug, 'closeEvent')

        # Gracefully stop monitoring
        #if self.engaged:
        #    self.__action_event()
        #score_data_obj.save_data_and_close()
        #diff_data_obj.save_data_and_close()

        # Hide any widgets to allow the app to close
        self.data_graphs_window.hide() 
        self.data_overview_window.hide()
        self.map_architect_window.hide()
        self.map_display_window.hide()

        # Proceed
        event.accept()
