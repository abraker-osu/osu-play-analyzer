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
import tinydb
import numpy as np
from pyqtgraph.Qt import QtGui, QtCore

from app.data_recording.data import RecData
from app.file_managers import MapsDB, PlayData
from osu_analysis import Mod


class PlayList(QtGui.QListWidget):

    map_selected = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        # TODO: Maybe change this to be a TableWidget from pyqtgraph 
        #       so more columns can be seen and data can be sorted by those columns
        QtGui.QListWidget.__init__(self, parent)

        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        self.map_idx_hashes = np.asarray([])
        self.selected_map_hash = None

        self.reload_map_list()

        if self.map_idx_hashes.size > 0:
            self.setCurrentRow(0)
            
        self.itemSelectionChanged.connect(self.__list_select_event)
        # TODO: Select all maps in the list


    def reload_map_list(self):
        self.clear()

        play_data = PlayData.data.astype(np.uint64)
        maps_table = MapsDB.maps_table

        map_hashes = play_data[:, RecData.MAP_HASH]
        self.map_idx_hashes = np.unique(map_hashes)

        # Go through unlisted maps
        for map_hash in self.map_idx_hashes:
            data_select = map_hashes == map_hash
            unique_mods = np.unique(play_data[data_select, RecData.MODS])

            # Find the map the hash is related to in db
            maps = maps_table.search(tinydb.where('md5h') == hex(map_hash)[2:-4])
            if len(maps) == 0:
                self.addItem(map_hash)
                continue

            for map_mods in unique_mods:
                map_mods = Mod(int(map_mods))

                # Resolve mod
                mods_text = map_mods.get_mods_txt()
                mods_text = f' +{mods_text}' if len(mods_text) != 0 else ''

                # Add map to list
                self.addItem(maps[0]['path'].split('/')[-1] + mods_text)
                #self.append(map_hash)

    
    def new_replay_event(self):
        pass


    def __list_select_event(self):
        play_data_map_hashes = PlayData.data[:, RecData.MAP_HASH].astype(np.uint64)

        idxs = np.asarray([ self.row(item) for item in self.selectedItems() ])
        select = np.full_like(play_data_map_hashes, 0, dtype=np.bool)

        for idx in idxs:
            select |= (play_data_map_hashes == self.map_idx_hashes[idx])

        self.map_selected.emit(PlayData.data[select])