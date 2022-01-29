"""
Window displaying various graphs pertaining to the data selected in the data_overview_window.
A menubar on the top allows the user to select which graph to display.
"""
from os import PathLike
import numpy as np
np.set_printoptions(suppress=True)

from PyQt5.QtCore import Qt
from numpy.core.fromnumeric import transpose
from pyqtgraph.Qt import QtGui

from app.graphs.hit_offset_graph import HitOffsetGraph
from app.graphs.hit_distr_graph import HitDistrGraph
from app.graphs.aim_graph import AimGraph

from app.graphs.dev_graph_angle import DevGraphAngle
from app.graphs.dev_graph_vel import DevGraphVel
from app.graphs.dev_graph_rhythm import DevGraphRhythm

from app.graphs.graph_toffset_bpm import GraphTOffsetBPM
from app.graphs.graph_toffset_bpm_inc import GraphTOffsetBPMInc

from app.data_recording.data import RecData
from app.file_managers import PlayData


class DataGraphsWindow(QtGui.QMainWindow):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Data graphs')
    
        self.hit_offset_graph = HitOffsetGraph()
        self.hit_distr_graph = HitDistrGraph()
        self.aim_display = AimGraph()

        self.toffset_bpm = GraphTOffsetBPM()
        self.toffset_bpm_inc = GraphTOffsetBPMInc()

        self.dev_graph_angle = DevGraphAngle()
        self.dev_graph_vel = DevGraphVel()
        self.dev_graph_rhythm = DevGraphRhythm()

        self.replay_tabs = QtGui.QTabWidget()
        self.replay_tabs.addTab(self.hit_offset_graph, 'Hit offsets')
        self.replay_tabs.addTab(self.hit_distr_graph, 'Hit distribution')
        self.replay_tabs.addTab(self.aim_display, 'Aim display')

        self.map_tabs = QtGui.QTabWidget()
        self.map_tabs.addTab(self.toffset_bpm, 'T-offset vs BPM')
        self.map_tabs.addTab(self.toffset_bpm_inc, 'T-offset vs BPM Inc')

        self.play_data_tabs = QtGui.QTabWidget()
        self.play_data_tabs.addTab(self.dev_graph_angle, 'Dev vs Angle')
        self.play_data_tabs.addTab(self.dev_graph_vel, 'Dev vs Velocity')
        self.play_data_tabs.addTab(self.dev_graph_rhythm, 'Dev vs Rhythm')
        
        self.main_widget = QtGui.QTabWidget()
        self.main_widget.addTab(self.replay_tabs, 'Replay graphs')
        self.main_widget.addTab(self.map_tabs, 'Map graphs')
        self.main_widget.addTab(self.play_data_tabs, 'Deviation data graphs')
        self.setCentralWidget(self.main_widget)


    def new_replay_event(self):
        play_data = PlayData.data
        data_filter = (play_data[:, RecData.TIMESTAMP] == max(play_data[:, RecData.TIMESTAMP]))
        play_data = play_data[data_filter]

        self.hit_offset_graph.plot_data(play_data)
        self.hit_distr_graph.plot_data(play_data)
        self.aim_display.plot_data(play_data)

        self.toffset_bpm.plot_data(play_data)
        self.toffset_bpm_inc.plot_data(play_data)


    def overview_single_map_selection_event(self, play_data):
        """
        Called when a single map is selected in the overview window.
        """
        self.hit_offset_graph.plot_data(play_data)
        self.hit_distr_graph.plot_data(play_data)
        self.aim_display.plot_data(play_data)

        self.toffset_bpm.plot_data(play_data)


    def set_from_play_data(self, play_data):
        if play_data.shape[0] == 0:
            # TODO: Clear plots
            return

        self.toffset_bpm.plot_data(play_data)
        self.toffset_bpm_inc.plot_data(play_data)

        self.dev_graph_angle.plot_data(play_data)
        self.dev_graph_vel.plot_data(play_data)
        self.dev_graph_rhythm.plot_data(play_data)
