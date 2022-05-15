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
import time
import numpy as np
from pyqtgraph.Qt import QtGui, QtCore

from app.misc.Logger import Logger
from app.data_recording.data import ScoreNpyData
from app.file_managers import MapsDB, score_data_obj
from osu_analysis import Mod


class PlayList(pyqtgraph.TableWidget):

    logger = Logger.get_logger(__name__)

    map_selected = QtCore.pyqtSignal(object)
    new_map_loaded = QtCore.pyqtSignal()

    def __init__(self):
        self.logger.debug(f'__init__ enter')

        pyqtgraph.TableWidget.__init__(self)

        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.verticalHeader().setDefaultSectionSize(10)

        self.reload_map_list()
        
        if self.rowCount() > 0:
            self.selectRow(0)
            
        self.selectionModel().selectionChanged.connect(self.__list_select_event)

        # Hide displayed columns
        self.setColumnHidden(0, True)
        #self.setColumnHidden(1, True)

        self.logger.debug(f'__init__ exit')


    def load_latest_play(self, is_import, map_md5_str):
        if score_data_obj.is_empty():
            return

        # Get list of hashes and mods for loaded maps
        map_hashes = np.asarray([ int(self.model().data(self.model().index(i, 0), role=QtCore.Qt.DisplayRole), 16) for i in range(self.rowCount()) ])

        if map_md5_str in map_hashes:
            # Check if only one map is selected
            if len(self.selectionModel().selectedRows()) <= 1:
                # Select to new map
                matching_items = self.findItems(str(map_md5_str), QtCore.Qt.MatchContains)
                if matching_items:
                    self.setCurrentItem(matching_items[0])

            if not is_import:
                # Fire off the new map loaded event so the roi selection in composition viewer is reset
                self.logger.debug('new_map_loaded.emit ->')
                self.new_map_loaded.emit()
                self.logger.debug('new_map_loaded.emit <-')

            # Fire off the list select event so the timeline in overview window is updated
            if not is_import:
                self.__list_select_event(None)
            return

        # Build data structure and add to table
        data = np.empty(
            shape=(1, ),
            dtype=[
                ('md5',  object),         # Map hash (str, not shown)
                ('Name', object),         # Name of the map 
                ('Mods', object),         # Mods used on the map (string)
                ('Time', object),         # Time of the play
                ('Data', np.uint64),      # Number of points in the play
                ('Avg BPM', object),      # Average BPM of the map
                ('Avg Lin Vel', object),  # Average linear velocity of the map
                ('Avg Ang Vel', object),  # Average angular velocity of the map
            ]
        )

        # Process data to get stuff that will be shown
        score_data = score_data_obj.data(map_md5_str)

        map_name_str       = self.__map_name_str(map_md5_str)
        map_mods_str       = self.__map_mods_str(score_data)
        map_time_str       = self.__map_timestamp_str(score_data)
        map_num_points     = score_data.shape[0]
        map_avg_bpm        = self.__map_avg_bpm(score_data)
        map_to_avg_lin_vel = self.__map_avg_lin_vel(score_data)
        map_to_avg_ang_vel = self.__map_avg_ang_vel(score_data)

        data['md5']  = map_md5_str
        data['Name'] = map_name_str
        data['Mods'] = map_mods_str
        data['Time'] = map_time_str
        data['Data'] = map_num_points
        data['Avg BPM'] = map_avg_bpm
        data['Avg Lin Vel'] = map_to_avg_lin_vel
        data['Avg Ang Vel'] = map_to_avg_ang_vel
        
        self.appendData(data)
        
        # Check if only one map is selected
        if len(self.selectionModel().selectedRows()) <= 1:
            # Select to new map
            matching_items = self.findItems(str(map_md5_str), QtCore.Qt.MatchContains)
            if matching_items:
                self.setCurrentItem(matching_items[0])

            if not is_import:
                # Fire off the new map loaded event so the roi selection in composition viewer is reset
                self.logger.debug(f'new_map_loaded.emit ->')
                self.new_map_loaded.emit()
                self.logger.debug(f'new_map_loaded.emit <-')

        if not is_import:
            # Fire off the list select event so the timeline in overview window is updated
            self.__list_select_event(None)


    def reload_map_list(self):
        self.clear()

        if score_data_obj.is_empty():
            return

        map_md5_strs = score_data_obj.get_entries()
        num_md5_strs = len(map_md5_strs)
        print(map_md5_strs)

        data = np.empty(
            shape=(num_md5_strs, ),
            dtype=[
                ('md5',  object),         # Map hash (str, not shown)
                ('Name', object),         # Name of the map 
                ('Mods', object),         # Mods used on the map (string)
                ('Time', object),         # Time of the play
                ('Data', np.uint64),      # Number of points in the play
                ('Avg BPM', object),      # Average BPM of the map
                ('Avg Lin Vel', object),  # Average linear velocity of the map
                ('Avg Ang Vel', object),  # Average angular velocity of the map
            ]
        )

        self.logger.debug(f'Num of plays to load: {num_md5_strs}')

        md5_to_score_data  = np.frompyfunc(score_data_obj.data, 1, 1)
        score_datas        = md5_to_score_data(map_md5_strs)

        md5_to_name        = np.frompyfunc(self.__map_name_str, 1, 1)
        map_to_mod         = np.frompyfunc(self.__map_mods_str, 1, 1)
        map_to_time_str    = np.frompyfunc(self.__map_timestamp_str, 1, 1)
        map_to_num_points  = np.frompyfunc(lambda score_data: score_data.shape[0], 1, 1)
        map_to_avg_bpm     = np.frompyfunc(self.__map_avg_bpm, 1, 1)
        map_to_avg_lin_vel = np.frompyfunc(self.__map_avg_lin_vel, 1, 1)
        map_to_avg_ang_vel = np.frompyfunc(self.__map_avg_ang_vel, 1, 1)

        data['md5']  = map_md5_strs
        data['Name'] = md5_to_name(map_md5_strs)
        data['Mods'] = map_to_mod(score_datas)
        data['Time'] = map_to_time_str(score_datas)
        data['Data'] = map_to_num_points(score_datas)
        data['Avg BPM'] = map_to_avg_bpm(score_datas)
        data['Avg Lin Vel'] = map_to_avg_lin_vel(score_datas)
        data['Avg Ang Vel'] = map_to_avg_ang_vel(score_datas)

        self.setData(data)    

    
    def __list_select_event(self, _):
        self.logger.info_debug(True, '__list_select_event')

        selected_rows = self.selectionModel().selectedRows(column=0)
        md5_strs = [ selected_row.data(role=QtCore.Qt.DisplayRole) for selected_row in selected_rows ]

        self.logger.debug('map_selected.emit ->')
        self.map_selected.emit(md5_strs)
        self.logger.debug('map_selected.emit <-')


    @staticmethod
    def __map_name_str(md5_str):
        result, _ = MapsDB.get_map_file_name(md5_str)
        if result == None:
            return md5_str

        return result.replace('\\', '/').split('/')[-1]


    @staticmethod
    def __map_mods_str(score_data):
        mods = score_data['MODS'].values[0]
        mods_text = Mod(int(mods)).get_mods_txt()

        return f' +{mods_text}' if len(mods_text) != 0 else ''


    @staticmethod
    def __map_timestamp_str(score_data):
        timestamp_start = min(score_data.index.get_level_values(0))
        timestamp_end   = max(score_data.index.get_level_values(0))

        try:
            if timestamp_start == timestamp_end:
                play_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp_start))

                time_str = f'{play_time}'
            else:
                play_start = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp_start))
                play_end   = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp_end))

                time_str = f'{play_start} - {play_end}'
        except IndexError:
            play_start = 'N/A'
            play_end   = 'N/A'

        return time_str


    @staticmethod
    def __map_avg_bpm(score_data):        
        data = 15000/score_data['DIFF_T_PRESS_DIFF'].values
        data = data[~np.isnan(data)]

        return f'{np.mean(data):.2f}'


    @staticmethod
    def __map_avg_lin_vel(score_data):        
        data = score_data['DIFF_XY_LIN_VEL'].values
        data = data[~np.isnan(data)]

        return f'{np.mean(data):.2f}'


    @staticmethod
    def __map_avg_ang_vel(score_data):        
        data = score_data['DIFF_XY_ANG_VEL'].values
        data = data[~np.isnan(data)]

        return f'{np.mean(data):.2f}'
