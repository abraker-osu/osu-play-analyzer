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
from app.graphs.aim_graph import AimGraph

from app.graphs.dev_graph_angle import DevGraphAngle
from app.graphs.dev_graph_vel import DevGraphVel

from app.graphs.graph_toffset_bpm import GraphTOffsetBPM

from app.data_recording.data import RecData
from app.file_managers import PlayData


class DataGraphsWindow(QtGui.QMainWindow):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Data graphs')
    
        self.hit_offset_graph = HitOffsetGraph()
        self.aim_display = AimGraph()

        self.toffset_bpm = GraphTOffsetBPM()

        self.dev_graph_angle = DevGraphAngle()
        self.dev_graph_vel = DevGraphVel()

        self.replay_tabs = QtGui.QTabWidget()
        self.replay_tabs.addTab(self.hit_offset_graph, 'Hit offsets')
        self.replay_tabs.addTab(self.aim_display, 'Aim display')

        self.map_tabs = QtGui.QTabWidget()
        self.map_tabs.addTab(self.toffset_bpm, 'T-offset vs BPM')
        self.map_tabs.addTab(QtGui.QLabel('TODO'), 'Map Graph2')

        self.play_data_tabs = QtGui.QTabWidget()
        self.play_data_tabs.addTab(self.dev_graph_angle, 'Dev vs Angle')
        self.play_data_tabs.addTab(self.dev_graph_vel, 'Dev vs Velocity')
        
        self.main_widget = QtGui.QTabWidget()
        self.main_widget.addTab(self.replay_tabs, 'Replay graphs')
        self.main_widget.addTab(self.map_tabs, 'Map graphs')
        self.main_widget.addTab(self.play_data_tabs, 'Deviation data graphs')
        self.setCentralWidget(self.main_widget)


    def new_replay_event(self):
        play_data = PlayData.data

        self.hit_offset_graph.plot_data(play_data)
        self.aim_display.plot_data(play_data)

        self.toffset_bpm.plot_data(play_data)


    def overview_single_map_selection_event(self, play_data):
        """
        Called when a single map is selected in the overview window.
        """
        self.hit_offset_graph.plot_data(play_data)
        self.aim_display.plot_data(play_data)

        self.toffset_bpm.plot_data(play_data)


    def set_from_play_data(self, play_data):
        if play_data.shape[0] == 0:
            # TODO: Clear plots
            return

        self.toffset_bpm.plot_data(play_data)

        self.__graph_deviation_data(play_data)
    

    def __graph_deviation_data(self, play_data):
        col_data = np.asarray([
              #   COL        MIN  MAX
            [ RecData.CS,     0,   10 ],
            [ RecData.AR,     0,   10 ],
            [ RecData.DT,     0, 1000 ],
            [ RecData.DT_INC, 0, 5000 ],
            [ RecData.DT_DEC, 0, 5000 ],
            [ RecData.DS,     0,  512 ],
            [ RecData.ANGLE,  0,  180 ],
        ])

        data = play_data[:, col_data[:, 0]]
        if data.shape[0] == 0:
            return

        idxs = np.zeros(data.shape)
        num_bins = 10

        # Sorts data into N-dimensional grid chunks numbered from 0 to num_bins - 1
        for i in range(col_data.shape[0]):
            #nan_filter = ~np.isnan(data[:, i])
            #filtered_data = data[nan_filter, i]

            #if filtered_data.shape[0] != 0:
            #    xmin, xmax = np.min(filtered_data), np.max(filtered_data)
            #    print(i, xmin, xmax)

            idxs[:, i] = np.digitize(data[:, i], np.linspace(col_data[i, 1], col_data[i, 2], num_bins))

        # Use the data enumerated by grid chunks to calculate unique "hashes" for each chunk containing data
        # This is done by interpreting the grid as an N-dimensional array which resides in memory, and calculating
        # memory offset where each chunk resides.
        hashed = np.array(idxs[:, 0])
        for i in range(col_data.shape[0] - 1):
            hashed += idxs[:, i + 1] * (num_bins ** (i + 1))
        unique_hashed, unique_idxs = np.unique(hashed, return_index=True)
        
        #print(idxs)
        #print(unique_hashed)
        #print(unique_idxs)

        # Resultant values from processing into grid chunks
        effective_values = (col_data[:, 1] + (col_data[:, 2] - col_data[:, 1]) / num_bins).T * idxs
        #print(effective_values)

        # +7 for dev_t, dev_x, dev_y, mean_t, mean_x, mean_y, num_points
        dev_data = np.zeros((unique_idxs.shape[0], col_data.shape[0] + 7))
        for idx, i in zip(unique_idxs, range(unique_idxs.shape[0])):
            map_data_section = col_data.shape[0]
            data_select = (unique_hashed[i] == hashed)

            dev_data[i, :map_data_section] = effective_values[idx, :map_data_section]
            dev_data[i, map_data_section + 0] = np.std(play_data[data_select, RecData.T_OFFSETS])
            dev_data[i, map_data_section + 1] = np.std(play_data[data_select, RecData.X_OFFSETS])
            dev_data[i, map_data_section + 2] = np.std(play_data[data_select, RecData.Y_OFFSETS])
            dev_data[i, map_data_section + 3] = np.mean(play_data[data_select, RecData.T_OFFSETS])
            dev_data[i, map_data_section + 4] = np.mean(play_data[data_select, RecData.X_OFFSETS])
            dev_data[i, map_data_section + 5] = np.mean(play_data[data_select, RecData.Y_OFFSETS])
            dev_data[i, map_data_section + 6] = np.count_nonzero(data_select)

        filter_insufficient = (dev_data[:, map_data_section + 6] > 20)
        dev_data = dev_data[filter_insufficient, :]

        print(f'total data entries: {idxs.shape[0]}    unique entries: {unique_hashed.shape[0]}   sufficient entries: {dev_data.shape[0]}')

        #print(dev_data)

        # TODO: There are 7 variables (columns) and data needs to be sorted into 
        # unique combinations of those variables. I think hashing each row and then running
        # np.unique on the resultant hashes is a good first start. That will give unique combinations
        # as well as how many there are, and that can be iterated over to get the mean and deviation.

        self.dev_graph_angle.plot_data(dev_data)
        self.dev_graph_vel.plot_data(dev_data)
