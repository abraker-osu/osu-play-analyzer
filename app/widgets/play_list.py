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
import numpy as np
from pyqtgraph.Qt import QtGui, QtCore

from app.data_recording.data import RecData
from app.file_managers import MapsDB, PlayData
from osu_analysis import Mod



class PlayList(pyqtgraph.TableWidget):

    map_selected = QtCore.pyqtSignal(object)

    def __init__(self):
        pyqtgraph.TableWidget.__init__(self)

        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.verticalHeader().setDefaultSectionSize(10)

        self.reload_map_list()
        
        if self.rowCount() > 0:
            self.selectRow(0)
            
        self.selectionModel().selectionChanged.connect(self.__list_select_event)
        # TODO: Select all maps in the list


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
            return
            
        map_md5h_str = self.__md5_to_md5h_str_func(map_md5)
        map_name_str = self.__md5h_str_to_name_func(map_md5h_str)
        map_mods_str = self.__mods_to_name_func(map_mod)

        data = np.empty(
            shape=(1, ),
            dtype=[
                ('md5',  np.uint64),  # Map hash (int, not shown)
                ('IMod', np.uint64),  # Mods used on the map (int, not shown)
                ('Name', object),     # Name of the map 
                ('Mods', object),     # Mods used on the map (string)
            ]
        )

        data['md5']  = map_md5
        data['IMod'] = map_mod
        data['Name'] = map_name_str
        data['Mods'] = map_mods_str
        
        self.appendData(data)


    def reload_map_list(self):
        self.clear()

        if PlayData.data.shape[0] == 0:
            return

        md5_to_md5h_str  = np.vectorize(lambda md5: self.__md5_to_md5h_str_func(md5))
        md5h_str_to_name = np.vectorize(lambda md5h_str: self.__md5h_str_to_name_func(md5h_str))
        mod_to_name      = np.vectorize(lambda mod: self.__mods_to_name_func(mod))

        map_hash_mods = PlayData.data[:, [ RecData.MAP_HASH, RecData.MODS ]].astype(np.uint64)
        unique_map_hash_mods = np.unique(map_hash_mods, axis=0)

        data = np.empty(
            shape=(unique_map_hash_mods.shape[0], ),
            dtype=[
                ('md5',  np.uint64),  # Map hash (int, not shown)
                ('IMod', np.uint64),  # Mods used on the map (int, not shown)
                ('Name', object),     # Name of the map 
                ('Mods', object),     # Mods used on the map (string)
            ]
        )

        data['md5']  = unique_map_hash_mods[:, 0]
        data['IMod'] = unique_map_hash_mods[:, 1]
        data['Name'] = md5h_str_to_name(md5_to_md5h_str(data['md5']))
        data['Mods'] = mod_to_name(data['IMod'])

        self.setData(data)

        self.setColumnHidden(0, True)
        self.setColumnHidden(1, True)
    

    def new_replay_event(self):
        pass

    
    def __list_select_event(self, _):
        map_hash_mods = PlayData.data[:, [ RecData.MAP_HASH, RecData.MODS ]].astype(np.uint64)
        select = np.zeros((map_hash_mods.shape[0], ), dtype=np.bool)

        selection_model = self.selectionModel()
        md5_selects = selection_model.selectedRows(column=0)
        mod_selects = selection_model.selectedRows(column=1)

        for md5, mod in zip(md5_selects, mod_selects):
            md5 = int(md5.data(role=QtCore.Qt.DisplayRole))
            mod = int(mod.data(role=QtCore.Qt.DisplayRole))

            print(md5, mod)
            
            select |= ((md5 == map_hash_mods[:, 0]) & (mod == map_hash_mods[:, 1]))

        self.map_selected.emit(PlayData.data[select])

    
    @staticmethod
    def __md5_to_md5h_str_func(md5):
        # Since map_md5h is the integer representation of a portion of the lower 
        # half of the md5 hash, there might be zeros in most significant digits of
        # the resultant uin64 encoded value. It's possible to detect that by 
        # checking size of the resulting hash string in hex form 
        # (it must be 12 characters). From there, fill the front with zeros to 
        # make it complete
        map_md5h_str = hex(md5)[2:-4]
        if len(map_md5h_str) < 12:
            map_md5h_str = '0'*(12 - len(map_md5h_str)) + map_md5h_str

        return map_md5h_str


    @staticmethod
    def __md5h_str_to_name_func(md5_str):
        results = MapsDB.maps_table.search(tinydb.where('md5h') == md5_str)
        if len(results) == 0:
            return md5_str

        return results[0]['path'].split('/')[-1]


    @staticmethod
    def __mods_to_name_func(mods):
        mods_text = Mod(int(mods)).get_mods_txt()
        return f' +{mods_text}' if len(mods_text) != 0 else ''