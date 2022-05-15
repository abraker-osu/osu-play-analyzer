"""
Window displaying various graphs pertaining to the data selected in the data_overview_window.
A menubar on the top allows the user to select which graph to display.
"""
import time

from pyqtgraph.Qt import QtGui

from app.misc.Logger import Logger

from app.graphs.replay.hit_offset_graph import HitOffsetGraph
from app.graphs.replay.replay_hit_doffset_graph import ReplayHitDOffsetGraph
from app.graphs.replay.replay_toffset_multimap import ReplayTOffsetMultimap
from app.graphs.replay.hit_distr_graph import HitDistrGraph
from app.graphs.replay.aim_graph import AimGraph

from app.graphs.difficulty.graph_aim_difficulty import GraphAimDifficulty
from app.graphs.difficulty.graph_tap_difficulty import GraphTapDifficulty

from app.graphs.map.graph_timing_bpm_dec import GraphTimingBPMDec
from app.graphs.map.graph_timing_bpm_inc import GraphTimingBPMInc
from app.graphs.map.graph_toffset_bpm_inc import GraphTOffsetBPMInc
from app.graphs.map.graph_toffset_bpm import GraphTOffsetBPM
from app.graphs.map.map_toffset_rhy_graph import MapToffsetRhyGraph
from app.graphs.map.map_toffset_rhyd_graph import MapToffsetRhydGraph
from app.graphs.map.graph_toffset_velocity import GraphTOffsetVelocity

from app.graphs.deviation.dev_graph_angle import DevGraphAngle
from app.graphs.deviation.dev_graph_vel import DevGraphVel
from app.graphs.deviation.dev_graph_rhythm import DevGraphRhythm

from app.data_recording.data import ScoreNpyData
from app.file_managers import score_data_obj


class DataGraphsWindow(QtGui.QMainWindow):

    logger = Logger.get_logger(__name__)

    def __init__(self, parent=None):
        self.logger.debug('__init__ enter')

        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Data graphs')
    
        self.hit_offset_graph = HitOffsetGraph()
        self.replay_offset_multimap_graph = ReplayTOffsetMultimap()
        self.replay_hit_doffset_graph = ReplayHitDOffsetGraph()
        self.hit_distr_graph = HitDistrGraph()
        self.aim_display = AimGraph()

        self.aim_difficulty = GraphAimDifficulty()
        self.tap_difficulty = GraphTapDifficulty()

        self.timing_bpm_dec = GraphTimingBPMDec()
        self.timing_bpm_inc = GraphTimingBPMInc()
        self.toffset_bpm_inc = GraphTOffsetBPMInc()
        self.toffset_bpm = GraphTOffsetBPM()
        self.toffset_rhy_graph = MapToffsetRhyGraph()
        self.toffset_rhyd_graph = MapToffsetRhydGraph()
        self.toffset_velocity = GraphTOffsetVelocity()
        
        self.dev_graph_angle = DevGraphAngle()
        self.dev_graph_vel = DevGraphVel()
        self.dev_graph_rhythm = DevGraphRhythm()

        self.replay_tabs = QtGui.QTabWidget()
        self.replay_tabs.addTab(self.hit_offset_graph, 'Hit offsets')
        self.replay_tabs.addTab(self.replay_offset_multimap_graph, 'Replay offsets multimap')
        self.replay_tabs.addTab(self.replay_hit_doffset_graph, 'Replay hit doffsets')
        self.replay_tabs.addTab(self.hit_distr_graph, 'Hit distribution')
        self.replay_tabs.addTab(self.aim_display, 'Aim display')

        self.difficulty_tabs = QtGui.QTabWidget()
        self.difficulty_tabs.addTab(self.aim_difficulty, 'Aim difficulty')
        self.difficulty_tabs.addTab(self.tap_difficulty, 'Tap difficulty')

        self.map_tabs = QtGui.QTabWidget()
        #self.map_tabs.addTab(self.timing_bpm_dec, 'Timing BPM dec')
        #self.map_tabs.addTab(self.timing_bpm_inc, 'Timing BPM inc')
        self.map_tabs.addTab(self.toffset_bpm_inc, 'T-offset vs BPM Inc')
        self.map_tabs.addTab(self.toffset_bpm, 'T-offset vs BPM')
        #self.map_tabs.addTab(self.toffset_rhy_graph, 'T-offset vs Rhythm')
        #self.map_tabs.addTab(self.toffset_rhyd_graph, 'T-offset vs Rhythm delta')
        self.map_tabs.addTab(self.toffset_velocity, 'T-offset vs Velocity')

        self.play_data_tabs = QtGui.QTabWidget()
        self.play_data_tabs.addTab(self.dev_graph_angle, 'Dev vs Angle')
        self.play_data_tabs.addTab(self.dev_graph_vel, 'Dev vs Velocity')
        self.play_data_tabs.addTab(self.dev_graph_rhythm, 'Dev vs Rhythm')
        
        self.main_widget = QtGui.QTabWidget()
        self.main_widget.addTab(self.replay_tabs, 'Replay graphs')
        self.main_widget.addTab(self.difficulty_tabs, 'Diff graphs')
        self.main_widget.addTab(self.map_tabs, 'Map graphs')
        self.main_widget.addTab(self.play_data_tabs, 'Deviation data graphs')
        self.setCentralWidget(self.main_widget)

        self.logger.debug('__init__ exit')


    def new_replay_event(self, score_data):
        '''
        Called when a single new replay is loaded
        '''
        self.logger.debug('new_replay_event')

        self.hit_offset_graph.plot_data(score_data)
        self.replay_hit_doffset_graph.plot_data(score_data)
        self.hit_distr_graph.plot_data(score_data)
        self.aim_display.plot_data(score_data)

        self.aim_difficulty.plot_data(score_data)
        self.tap_difficulty.plot_data(score_data)

        #self.timing_bpm_dec.plot_data(score_data)
        #self.timing_bpm_inc.plot_data(score_data)
        #self.toffset_bpm_inc.plot_data(score_data)
        ##self.toffset_bpm.plot_data(score_data)
        #self.toffset_rhy_graph.plot_data(score_data)
        #self.toffset_rhyd_graph.plot_data(score_data)
        #self.toffset_velocity.plot_data(score_data)


    def overview_single_map_selection_event(self, score_data):
        """
        Called when a single map is selected in the overview window.
        """
        self.logger.debug('overview_single_map_selection_event')

        self.hit_offset_graph.plot_data(score_data)
        self.replay_offset_multimap_graph.plot_data(score_data)
        self.replay_hit_doffset_graph.plot_data(score_data)
        self.hit_distr_graph.plot_data(score_data)
        self.aim_display.plot_data(score_data)

        self.aim_difficulty.plot_data(score_data)
        self.tap_difficulty.plot_data(score_data)

        self.toffset_bpm.plot_data(score_data)


    def set_from_play_data(self, score_data):
        '''
        Called whenever the selection in the overview window changes
        '''
        self.logger.debug('set_from_play_data')

        if score_data.shape[0] == 0:
            # TODO: Clear plots
            return

        #self.timing_bpm_dec.plot_data(score_data)
        #self.timing_bpm_inc.plot_data(score_data)
        #self.toffset_bpm_inc.plot_data(score_data)
        #self.toffset_bpm.plot_data(score_data)
        #self.toffset_rhy_graph.plot_data(score_data)
        #self.toffset_rhyd_graph.plot_data(score_data)
        #self.toffset_velocity.plot_data(score_data)

        #self.dev_graph_angle.plot_data(score_data)
        #self.dev_graph_vel.plot_data(score_data)
        #self.dev_graph_rhythm.plot_data(score_data)
