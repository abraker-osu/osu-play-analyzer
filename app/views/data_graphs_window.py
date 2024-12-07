"""
Window displaying various graphs pertaining to the data selected in the data_overview_window.
A menubar on the top allows the user to select which graph to display.
"""
import time
import PyQt5

from app.misc.Logger import Logger

from app.graphs.score.hit_offset_graph import HitOffsetGraph
from app.graphs.score.score_hit_doffset_graph import ScoreHitDOffsetGraph
from app.graphs.score.score_toffset_multimap import ScoreTOffsetMultimap
from app.graphs.score.hit_distr_graph import HitDistrGraph
from app.graphs.score.doffset_distr_graph import DoffsetsDistrGraph
from app.graphs.score.aim_graph import AimGraph

from app.graphs.time.graph_timing_bpm_dec import GraphTimingBPMDec
from app.graphs.time.graph_timing_bpm_inc import GraphTimingBPMInc
from app.graphs.time.graph_timing_aim_diff import GraphTimeAimDifficulty
from app.graphs.time.graph_timing_reading import GraphTimeReadingDifficulty

from app.graphs.difficulty.graph_aim_difficulty import GraphAimDifficulty
from app.graphs.difficulty.graph_tap_difficulty import GraphTapDifficulty

from app.graphs.map.graph_toffset_bpm_inc import GraphTOffsetBPMInc
from app.graphs.map.graph_toffset_bpm import GraphTOffsetBPM
from app.graphs.map.map_toffset_rhy_graph import MapToffsetRhyGraph
from app.graphs.map.map_toffset_rhyd_graph import MapToffsetRhydGraph
from app.graphs.map.graph_toffset_velocity import GraphTOffsetVelocity

from app.graphs.deviation.dev_graph_angle import DevGraphAngle
from app.graphs.deviation.dev_graph_vel import DevGraphVel
from app.graphs.deviation.dev_graph_rhythm import DevGraphRhythm
from app.graphs.deviation.dev_doffsets import DevDOffsets
from app.graphs.deviation.dev_offsets import DevOffsets
from app.graphs.deviation.dev_t_graph_ar import DevTGraphAR
from app.graphs.deviation.dev_visible_ar import DevVisibleAR


class DataGraphsWindow(PyQt5.QtWidgets.QMainWindow):

    logger = Logger.get_logger(__name__)

    time_changed_event = PyQt5.QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        self.logger.debug('__init__ enter')

        PyQt5.QtWidgets.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Data graphs')

        self.hit_offset_graph = HitOffsetGraph()
        self.score_offset_multimap_graph = ScoreTOffsetMultimap()
        self.score_hit_doffset_graph = ScoreHitDOffsetGraph()
        self.hit_distr_graph = HitDistrGraph()
        self.doffset_distr_graph = DoffsetsDistrGraph()
        self.aim_display = AimGraph()

        self.timing_bpm_dec = GraphTimingBPMDec()
        self.timing_bpm_inc = GraphTimingBPMInc()
        self.timing_aim_diff = GraphTimeAimDifficulty()
        self.timing_reading_diff = GraphTimeReadingDifficulty()

        self.aim_difficulty = GraphAimDifficulty()
        self.tap_difficulty = GraphTapDifficulty()

        self.toffset_bpm_inc = GraphTOffsetBPMInc()
        self.toffset_bpm = GraphTOffsetBPM()
        self.toffset_rhy_graph = MapToffsetRhyGraph()
        self.toffset_rhyd_graph = MapToffsetRhydGraph()
        self.toffset_velocity = GraphTOffsetVelocity()

        self.dev_graph_angle = DevGraphAngle()
        self.dev_graph_vel = DevGraphVel()
        self.dev_graph_rhythm = DevGraphRhythm()
        self.dev_doffsets = DevDOffsets()
        self.dev_offsets = DevOffsets()
        self.dev_t_ar = DevTGraphAR()
        self.dev_visible_ar = DevVisibleAR()

        self.score_tabs = PyQt5.QtWidgets.QTabWidget()
        self.score_tabs.addTab(self.hit_offset_graph, 'Hit offsets')
        self.score_tabs.addTab(self.score_offset_multimap_graph, 'Score offsets multimap')
        self.score_tabs.addTab(self.score_hit_doffset_graph, 'Score hit doffsets')
        self.score_tabs.addTab(self.hit_distr_graph, 'Hit distribution')
        self.score_tabs.addTab(self.doffset_distr_graph, 'Doffset distribution')
        self.score_tabs.addTab(self.aim_display, 'Aim display')

        self.time_tabs = PyQt5.QtWidgets.QTabWidget()
        self.time_tabs.addTab(self.timing_bpm_dec, 'Timing BPM dec')
        self.time_tabs.addTab(self.timing_bpm_inc, 'Timing BPM inc')
        self.time_tabs.addTab(self.timing_aim_diff, 'Timing Aim diff')
        self.time_tabs.addTab(self.timing_reading_diff, 'Timing Reading diff')

        self.difficulty_tabs = PyQt5.QtWidgets.QTabWidget()
        self.difficulty_tabs.addTab(self.aim_difficulty, 'Aim difficulty')
        self.difficulty_tabs.addTab(self.tap_difficulty, 'Tap difficulty')

        self.map_tabs = PyQt5.QtWidgets.QTabWidget()
        self.map_tabs.addTab(self.toffset_bpm_inc, 'T-offset vs BPM Inc')
        self.map_tabs.addTab(self.toffset_bpm, 'T-offset vs Note interval')
        self.map_tabs.addTab(self.toffset_rhy_graph, 'T-offset vs Rhythm')
        #self.map_tabs.addTab(self.toffset_rhyd_graph, 'T-offset vs Rhythm delta')
        self.map_tabs.addTab(self.toffset_velocity, 'T-offset vs Velocity')

        self.play_data_tabs = PyQt5.QtWidgets.QTabWidget()
        self.play_data_tabs.addTab(self.dev_graph_angle, 'Dev vs Angle')
        self.play_data_tabs.addTab(self.dev_graph_vel, 'Dev vs Velocity')
        self.play_data_tabs.addTab(self.dev_graph_rhythm, 'Dev vs Rhythm')
        self.play_data_tabs.addTab(self.dev_doffsets, 'Avg BPM vs Doffsets dev')
        self.play_data_tabs.addTab(self.dev_offsets, 'Avg BPM vs Offsets dev')
        self.play_data_tabs.addTab(self.dev_t_ar, 'AR vs t-dev')
        self.play_data_tabs.addTab(self.dev_visible_ar, 'AR vs # Misses')

        self.main_widget = PyQt5.QtWidgets.QTabWidget()
        self.main_widget.addTab(self.score_tabs, 'Score graphs')
        self.main_widget.addTab(self.time_tabs, 'Time graphs')
        self.main_widget.addTab(self.difficulty_tabs, 'Diff graphs')
        self.main_widget.addTab(self.map_tabs, 'Map graphs')
        self.main_widget.addTab(self.play_data_tabs, 'Deviation data graphs')
        self.setCentralWidget(self.main_widget)

        self.timing_bpm_dec.time_changed_event.connect(self.time_changed_event)
        self.timing_bpm_inc.time_changed_event.connect(self.time_changed_event)
        self.timing_aim_diff.time_changed_event.connect(self.time_changed_event)

        self.logger.debug('__init__ exit')


    def set_time(self, time):
        self.timing_bpm_dec.set_time(time)
        self.timing_bpm_inc.set_time(time)


    def new_replay_event(self, score_data, diff_data):
        '''
        Called when a single new replay is loaded
        '''
        self.logger.debug('new_replay_event')

        self.hit_offset_graph.plot_data(score_data)
        self.score_hit_doffset_graph.plot_data(score_data)
        self.hit_distr_graph.plot_data(score_data)
        self.doffset_distr_graph.plot_data(score_data)
        self.aim_display.plot_data(score_data)

        self.aim_difficulty.plot_data(score_data, diff_data)
        self.tap_difficulty.plot_data(score_data, diff_data)

        self.timing_bpm_dec.plot_data(score_data, diff_data)
        self.timing_bpm_inc.plot_data(score_data, diff_data)
        self.timing_aim_diff.plot_data(score_data, diff_data)
        self.timing_reading_diff.plot_data(score_data, diff_data)

        #self.toffset_bpm_inc.plot_data(score_data)
        ##self.toffset_bpm.plot_data(score_data)
        #self.toffset_rhyd_graph.plot_data(score_data)
        #self.toffset_velocity.plot_data(score_data)
        self.toffset_rhy_graph.plot_data(score_data, diff_data)

        self.dev_doffsets.plot_data(score_data, diff_data)
        self.dev_offsets.plot_data(score_data, diff_data)
        self.dev_t_ar.plot_data(score_data, diff_data)
        self.dev_visible_ar.plot_data(score_data, diff_data)


    def overview_single_map_selection_event(self, score_data, diff_data):
        """
        Called when a single map is selected in the overview window.
        """
        self.logger.debug('overview_single_map_selection_event')

        self.hit_offset_graph.plot_data(score_data)
        self.score_offset_multimap_graph.plot_data(score_data)
        self.score_hit_doffset_graph.plot_data(score_data)
        self.hit_distr_graph.plot_data(score_data)
        self.doffset_distr_graph.plot_data(score_data)
        self.aim_display.plot_data(score_data)

        self.toffset_rhy_graph.plot_data(score_data, diff_data)

        self.timing_bpm_dec.plot_data(score_data, diff_data)
        self.timing_bpm_inc.plot_data(score_data, diff_data)
        self.timing_aim_diff.plot_data(score_data, diff_data)
        self.timing_reading_diff.plot_data(score_data, diff_data)

        self.aim_difficulty.plot_data(score_data, diff_data)
        self.tap_difficulty.plot_data(score_data, diff_data)

        self.toffset_bpm.plot_data(score_data, diff_data)

        self.dev_t_ar.plot_data(score_data, diff_data)
        self.dev_visible_ar.plot_data(score_data, diff_data)

    def set_from_play_data(self, score_data, diff_data):
        '''
        Called whenever the selection in the overview window changes
        '''
        self.logger.debug('set_from_play_data')

        if 0 in [ score_data.shape[0], diff_data.shape[0] ]:
            # TODO: Clear plots
            return

        self.timing_bpm_dec.plot_data(score_data, diff_data)
        self.timing_bpm_inc.plot_data(score_data, diff_data)
        self.timing_aim_diff.plot_data(score_data, diff_data)

        #self.toffset_bpm_inc.plot_data(score_data)
        #self.toffset_bpm.plot_data(score_data)
        #self.toffset_rhyd_graph.plot_data(score_data)
        #self.toffset_velocity.plot_data(score_data)
        self.toffset_rhy_graph.plot_data(score_data, diff_data)

        #self.dev_graph_angle.plot_data(score_data)
        #self.dev_graph_vel.plot_data(score_data)
        #self.dev_graph_rhythm.plot_data(score_data)
        self.dev_doffsets.plot_data(score_data, diff_data)
        self.dev_offsets.plot_data(score_data, diff_data)
        self.dev_t_ar.plot_data(score_data, diff_data)
        self.dev_visible_ar.plot_data(score_data, diff_data)
