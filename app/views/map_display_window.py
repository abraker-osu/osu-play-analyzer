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
import numpy as np
import pandas as pd

from pyqtgraph.Qt import QtGui, QtCore

from osu_analysis import StdMapData
from app.misc.osu_utils import OsuUtils
from app.widgets.map_display import MapDisplay

class MapDisplayWindow(QtGui.QMainWindow):

    data_loaded = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Map Display')

        self.selected_map_display = MapDisplay()
        self.generated_map_display = MapDisplay()
        self.processed_map_display = MapDisplay()
        self.map_tabs = QtGui.QTabWidget()

        self.map_tabs.addTab(self.selected_map_display, 'Selected')
        self.map_tabs.addTab(self.generated_map_display, 'Generated')
        self.map_tabs.addTab(self.processed_map_display, 'Processed')

        self.setCentralWidget(self.map_tabs)
        

    def set_from_play_data(self, play_data):
        self.selected_map_display.set_from_play_data(play_data)


    def new_replay_event(self, map_data, replay_data, cs, ar, mods, name):
        self.selected_map_display.new_replay_event(map_data, replay_data, cs, ar, mods, name)


    def set_from_generated(self, gen_data, cs, ar):
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

        map_data['time'] /= 1000
        map_data['y'] = -map_data['y']

        self.generated_map_display.set_map_full(map_data, cs, ar)
