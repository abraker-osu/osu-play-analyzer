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
import pyqtgraph
import tinydb
import time
import numpy as np
from pyqtgraph.Qt import QtGui, QtCore

from app.data_recording.data import RecData
from app.file_managers import MapsDB, PlayData
from osu_analysis import Mod



class PlayList(pyqtgraph.TableWidget):

    map_selected = QtCore.pyqtSignal(object)
    new_map_loaded = QtCore.pyqtSignal()

    def __init__(self):
        pyqtgraph.TableWidget.__init__(self)

        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.verticalHeader().setDefaultSectionSize(10)

        self.reload_map_list()
        
        if self.rowCount() > 0:
            self.selectRow(0)
            
        self.selectionModel().selectionChanged.connect(self.__list_select_event)

        self.setColumnHidden(0, True)
        self.setColumnHidden(1, True)


    def load_latest_play(self):
        play_data = PlayData.data.astype(np.uint64)
        if PlayData.data.shape[0] == 0:
            return

        # Determine what was the latest play
        data_filter = \
            (play_data[:, RecData.TIMESTAMP] == play_data[0, RecData.TIMESTAMP])
        play_data = play_data[data_filter]

        # Get list of hashes and mods for loaded maps
        md5s = np.asarray([ int(self.model().data(self.model().index(i, 0), role=QtCore.Qt.DisplayRole)) for i in range(self.rowCount()) ])
        mods = np.asarray([ int(self.model().data(self.model().index(i, 1), role=QtCore.Qt.DisplayRole)) for i in range(self.rowCount()) ])

        # Get map's md5 half hash and mods used in the play
        map_md5 = play_data[0, RecData.MAP_HASH]
        map_mod = play_data[0, RecData.MODS]

        if (map_md5 in md5s) and (map_mod in mods):
            # Check if only one map is selected
            if len(self.selectionModel().selectedRows()) <= 1:
                # Select to new map
                matching_items = self.findItems(str(map_md5), QtCore.Qt.MatchContains)
                if matching_items:
                    self.setCurrentItem(matching_items[0])

            # Fire off the new map loaded event so the roi selection in composition viewer is reset
            self.new_map_loaded.emit()

            # Fire off the list select event so the timeline in overview window is updated
            self.__list_select_event(None)
            return
            
        # Process data to get stuff that will be shown
        map_md5h_str = MapsDB.md5h_to_md5h_str_func(map_md5)
        map_name_str = self.__md5h_str_to_name_func(map_md5h_str)
        map_mods_str = self.__mods_to_name_func(map_mod)
        map_time_str = self.__md5_to_timestamp_str(map_md5, map_mod)
        map_num_points = self.__md5_to_num_data(map_md5, map_mod)
        map_avg_bpm = self.__md5_to_avg_bpm(map_md5, map_mod)

        # Build data structure and add to table
        data = np.empty(
            shape=(1, ),
            dtype=[
                ('md5',  np.uint64),   # Map hash (int, not shown)
                ('IMod', np.uint64),   # Mods used on the map (int, not shown)
                ('Name', object),      # Name of the map 
                ('Mods', object),      # Mods used on the map (string)
                ('Time', object),      # Time of the play
                ('Data', np.uint64),   # Number of points in the play
                ('Avg BPM', object)    # Average BPM of the map
            ]
        )

        data['md5']  = map_md5
        data['IMod'] = map_mod
        data['Name'] = map_name_str
        data['Mods'] = map_mods_str
        data['Time'] = map_time_str
        data['Data'] = map_num_points
        data['Avg BPM'] = map_avg_bpm
        
        self.appendData(data)
        
        # Check if only one map is selected
        if len(self.selectionModel().selectedRows()) <= 1:
            # Select to new map
            matching_items = self.findItems(str(map_md5), QtCore.Qt.MatchContains)
            if matching_items:
                self.setCurrentItem(matching_items[0])

            # Fire off the new map loaded event so the roi selection in composition viewer is reset
            self.new_map_loaded.emit()

        # Fire off the list select event so the timeline in overview window is updated
        self.__list_select_event(None)


    def reload_map_list(self):
        self.clear()

        if PlayData.data.shape[0] == 0:
            return

        md5h_to_md5h_str = np.vectorize(lambda md5h: MapsDB.md5h_to_md5h_str_func(md5h))
        md5h_str_to_name = np.vectorize(lambda md5h_str: self.__md5h_str_to_name_func(md5h_str))
        mod_to_name      = np.vectorize(lambda mod: self.__mods_to_name_func(mod))
        md5_to_time_str  = np.vectorize(lambda md5, mods: self.__md5_to_timestamp_str(md5, mods))
        map_num_points   = np.vectorize(lambda md5, mods: self.__md5_to_num_data(md5, mods))
        md5_to_avg_bpm   = np.vectorize(lambda md5, mods: self.__md5_to_avg_bpm(md5, mods))

        map_hash_mods = PlayData.data[:, [ RecData.MAP_HASH, RecData.MODS ]].astype(np.uint64)
        unique_map_hash_mods = np.unique(map_hash_mods, axis=0)

        data = np.empty(
            shape=(unique_map_hash_mods.shape[0], ),
            dtype=[
                ('md5',  np.uint64),  # Map hash (int, not shown)
                ('IMod', np.uint64),  # Mods used on the map (int, not shown)
                ('Name', object),     # Name of the map 
                ('Mods', object),     # Mods used on the map (string)
                ('Time', object),     # Time of the play
                ('Data', np.uint64),  # Number of points in the play
                ('Avg BPM', object)   # Average BPM of the map
            ]
        )

        print('Num of plays to load:', unique_map_hash_mods.shape[0])

        data['md5']  = unique_map_hash_mods[:, 0]
        data['IMod'] = unique_map_hash_mods[:, 1]
        data['Name'] = md5h_str_to_name(md5h_to_md5h_str(data['md5']))
        data['Mods'] = mod_to_name(data['IMod'])
        data['Time'] = md5_to_time_str(data['md5'], data['IMod'])
        data['Data'] = map_num_points(data['md5'], data['IMod'])
        data['Avg BPM'] = md5_to_avg_bpm(data['md5'], data['IMod'])

        self.setData(data)    

    
    def __list_select_event(self, _):
        map_hash_mods = PlayData.data[:, [ RecData.MAP_HASH, RecData.MODS ]].astype(np.uint64)
        select = np.zeros((map_hash_mods.shape[0], ), dtype=np.bool)

        selection_model = self.selectionModel()
        md5_selects = selection_model.selectedRows(column=0)
        mod_selects = selection_model.selectedRows(column=1)

        for md5, mod in zip(md5_selects, mod_selects):
            md5 = int(md5.data(role=QtCore.Qt.DisplayRole))
            mod = int(mod.data(role=QtCore.Qt.DisplayRole))
            
            select |= ((md5 == map_hash_mods[:, 0]) & (mod == map_hash_mods[:, 1]))

        self.map_selected.emit(PlayData.data[select])


    @staticmethod
    def __md5h_str_to_name_func(md5h_str):
        result, _ = MapsDB.get_map_file_name(md5h_str, md5h=True)
        if result == None:
            return md5h_str

        return result.replace('\\', '/').split('/')[-1]


    @staticmethod
    def __md5_to_timestamp_str(md5, mods):
        play_select = (PlayData.data[:, [ RecData.MAP_HASH, RecData.MODS ]] == (md5, mods)).all(axis=1)
        unique_timestamps = np.unique(PlayData.data[play_select, RecData.TIMESTAMP])
        
        play_start = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(unique_timestamps[0]))
        play_end   = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(unique_timestamps[-1]))

        return f'{play_start} - {play_end}'


    @staticmethod
    def __md5_to_num_data(md5, mods):
        play = (PlayData.data[:, [ RecData.MAP_HASH, RecData.MODS ]] == (md5, mods)).all(axis=1)
        unique_timestamp = np.unique(PlayData.data[play, RecData.TIMESTAMP])[0]

        return play[PlayData.data[:, RecData.TIMESTAMP] == unique_timestamp].shape[0]


    @staticmethod
    def __md5_to_avg_bpm(md5, mods):
        play = (PlayData.data[:, [ RecData.MAP_HASH, RecData.MODS ]] == (md5, mods)).all(axis=1)
        unique_timestamp = np.unique(PlayData.data[play, RecData.TIMESTAMP])[0]

        one_play = PlayData.data[PlayData.data[:, RecData.TIMESTAMP] == unique_timestamp]
        bpm_data = 30000/one_play[:, RecData.DT_NOTES]
        bpm_data = bpm_data[~(np.isnan(bpm_data) | np.isinf(bpm_data))]

        return f'{np.mean(bpm_data):.2f}'


    @staticmethod
    def __mods_to_name_func(mods):
        mods_text = Mod(int(mods)).get_mods_txt()
        return f' +{mods_text}' if len(mods_text) != 0 else ''
