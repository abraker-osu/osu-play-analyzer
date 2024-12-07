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

from PyQt5 import QtCore
from PyQt5 import QtWidgets

from osu_analysis import StdMapData

from app.misc.Logger import Logger
from app.misc.osu_utils import OsuUtils
from app.widgets.map_display import MapDisplay


class MapDisplayWindow(QtWidgets.QMainWindow):

    logger = Logger.get_logger(__name__)

    time_changed_event = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        self.logger.debug('__init__ enter')

        QtWidgets.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Map Display')

        self.selected_map_display  = MapDisplay()
        self.generated_map_display = MapDisplay()
        self.processed_map_display = MapDisplay()
        self.map_tabs = QtWidgets.QTabWidget()

        self.map_tabs.addTab(self.selected_map_display, 'Selected')
        self.map_tabs.addTab(self.generated_map_display, 'Generated')
        self.map_tabs.addTab(self.processed_map_display, 'Processed')

        self.selected_map_display.time_changed_event.connect(self.time_changed_event)

        self.setCentralWidget(self.map_tabs)

        self.logger.debug('__init__ exit')


    def set_from_score_data(self, score_data):
        self.selected_map_display.set_from_score_data(score_data)

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
        self.selected_map_display.new_replay_event(map_data, replay_data, cs, ar, mods, name)


    def set_time(self, time):
        self.selected_map_display.set_time(time)


    def set_from_generated(self, osu_data):
        self.generated_map_display.open_map_from_osu_data(osu_data)


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

        self.generated_map_display.set_map_full(map_data, cs, ar)
