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
import time
import threading
import pyqtgraph

from PyQt6 import QtCore
from PyQt6 import QtWidgets

import numpy as np
import pandas as pd
from file_managers.config_mgr import AppConfig

from osu_interfaces import Mod
from osu_db import MapsDB

from misc.Logger import Logger



class PlayListHelper():

    @staticmethod
    def map_name_str(maps_db, md5_str):
        result = maps_db.get_map_file_name(md5_str)
        if result is None:
            return md5_str

        return result.replace('\\', '/').split('/')[-1]


    @staticmethod
    def map_mods_str(score_data):
        mods = score_data.index.get_level_values(2)[0]
        mods_text = Mod(int(mods)).get_mods_txt()
        mods_text = f' +{mods_text}' if len(mods_text) != 0 else ''


    @staticmethod
    def map_timestamp_str(score_data):
        timestamp_start = min(score_data.index.get_level_values(1))
        timestamp_end   = max(score_data.index.get_level_values(1))

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
    def map_avg_bpm(score_data):
        # TODO: This needs to be select by single timestamp
        data = 15000/score_data['DIFF_T_PRESS_DIFF'].values
        data = data[~np.isnan(data)]

        return f'{np.mean(data):.2f}'


    @staticmethod
    def map_avg_lin_vel(score_data):
        # TODO: This needs to be select by single timestamp
        data = score_data['DIFF_XY_LIN_VEL'].values
        data = data[~np.isnan(data)]

        return f'{np.mean(data):.2f}'


    @staticmethod
    def map_avg_ang_vel(score_data):
        # TODO: This needs to be select by single timestamp
        data = score_data['DIFF_XY_ANG_VEL'].values
        data = data[~np.isnan(data)]

        return f'{np.mean(data):.2f}'


    @staticmethod
    def do_get_timestamps(score_data):
        return np.unique(score_data.index.get_level_values(1))



class PlayList(pyqtgraph.TableWidget):

    logger = Logger.get_logger(__name__)

    map_selected = QtCore.pyqtSignal(object)
    new_map_loaded = QtCore.pyqtSignal()

    __batch_processed = QtCore.pyqtSignal(object)

    def __init__(self):
        self.logger.debug(f'__init__ - enter')

        pyqtgraph.TableWidget.__init__(self)

        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.verticalHeader().setDefaultSectionSize(10)

        self.__maps_db = MapsDB(AppConfig.cfg['osu_dir'])

        self.__batch_processed.connect(self.__add_data)
        self.__table_is_configured = False

        self.selectionModel().selectionChanged.connect(self.__list_select_event)

        self.logger.debug(f'__init__ - exit')


    def load_play(self, diff_data):
        # Get list of hashes for loaded maps
        map_hashes = [ self.model().data(self.model().index(i, 0), role=QtCore.Qt.ItemDataRole.DisplayRole) for i in range(self.rowCount()) ]
        diff_data_md5 = diff_data.index.get_level_values(0)[0]

        # FIXME: Plays from same map but different mods do not load
        # TODO: Check against md5 AND mods
        if diff_data_md5 not in map_hashes:
            self.logger.debug('load_play_md5 - Map hash not found in table data. Creating new item entry...')

            # Build data structure and add to table
            self.appendData(
                pd.DataFrame([
                    [
                        diff_data_md5,
                        PlayListHelper.map_name_str(self.__maps_db, diff_data_md5),
                        PlayListHelper.map_mods_str(diff_data),
                        PlayListHelper.map_timestamp_str(diff_data),
                        diff_data.shape[0],
                        PlayListHelper.map_avg_bpm(diff_data),
                        PlayListHelper.map_avg_lin_vel(diff_data),
                        PlayListHelper.map_avg_ang_vel(diff_data),
                    ]
                ],
                columns=['md5', 'Name', 'Mods', 'Time', 'Data', 'Avg BPM', 'Avg Lin Vel', 'Avg Ang Vel']
            ).values)

            self.__check_table_config()
        else:
            # TODO: Update timestamp column
            pass

        # Check if one or no map is selected. If multiple maps
        # are selected, it is likely undesirable to switch to
        # any one specific map, so don't do it
        is_not_multiple_selected = (len(self.selectionModel().selectedRows()) <= 1)

        if is_not_multiple_selected:
            # If map already exists in listings, select it
            matching_items = self.findItems(str(diff_data_md5), QtCore.Qt.MatchFlag.MatchContains)
            if not matching_items:
                self.logger.warning('Failed to find map item in table data')
                return

            self.logger.debug('load_play_md5 - Found map item in table data. Setting it as selected...')

            # Blocks the `selectionChanged` signal
            self.selectionModel().blockSignals(True)
            self.setCurrentItem(matching_items[0])
            self.selectionModel().blockSignals(False)

            # Select first row
            #if self.rowCount() > 0:
            #    self.selectRow(0)


    def reload_map_list(self, score_data):
        self.logger.debug('reload_map_list - enter')

        # Deselect selection before changes to play list
        # Block the `selectionChanged` signal
        self.selectionModel().blockSignals(True)
        self.setCurrentItem(None)
        self.selectionModel().blockSignals(False)

        self.clear()

        if score_data is None:
            self.logger.debug('reload_map_list - nothing to reload')
            return

        # Clearing table resets table config
        self.__table_is_configured = False

        thread = threading.Thread(target=self.__reload_map_list_thread, args=(score_data, ))
        thread.start()


    def __reload_map_list_thread(self, score_data):
        data = []

        entries = score_data.groupby(level=0)
        num_entries = len(entries)

        self.logger.debug(f'reload_map_list - num entries to load: {num_entries}')

        for i, entry in enumerate(entries):
            data.append([
                entry[0],
                PlayListHelper.map_name_str(self.__maps_db, entry[0]),
                PlayListHelper.map_mods_str(entry[1]),
                PlayListHelper.map_timestamp_str(entry[1]),
                entry[1].shape[0],
                PlayListHelper.map_avg_bpm(entry[1]),
                PlayListHelper.map_avg_lin_vel(entry[1]),
                PlayListHelper.map_avg_ang_vel(entry[1]),
            ])

            # Send data for GUI update every 100 entries
            if ((i % 100) == 0) or (i == (num_entries - 1)):
                self.__batch_processed.emit(
                    pd.DataFrame(
                        data[:],
                        columns=['md5', 'Name', 'Mods', 'Time', 'Data', 'Avg BPM', 'Avg Lin Vel', 'Avg Ang Vel']
                    )
                )

                data = []


    def get_num_selected(self):
        return len(self.selectionModel().selectedRows())


    def get_selected(self):
        #print([ row.data() for row in self.selectionModel().selectedRows() ])
        #print([ row.row() for row in self.selectionModel().selectedRows() ])

        return [
            (
                self.model().data(self.model().index(selection.row(), 0), role=QtCore.Qt.ItemDataRole.DisplayRole)#,  # MD5
                #self.model().data(self.model().index(selection.row(), 2), role=QtCore.Qt.ItemDataRole.DisplayRole)   # MOD
            )
            for selection in self.selectionModel().selectedRows()
        ]


    def __add_data(self, data):
        self.appendData(data.values)
        self.__check_table_config()


    def __check_table_config(self):
        """
        Configures table if it's not already configured
        """
        if self.__table_is_configured:
            return

        # Set header labels
        header_labels = [ 'md5', 'Name', 'Mods', 'Time', 'Data', 'Avg BPM', 'Avg Lin Vel', 'Avg Ang Vel' ]
        self.setHorizontalHeaderLabels(header_labels)

        # Hide displayed columns
        self.setColumnHidden(0, True)

        self.__table_is_configured = True


    def __list_select_event(self, _):
        selected_rows = self.selectionModel().selectedRows(column=0)
        md5_strs = [ selected_row.data(role=QtCore.Qt.ItemDataRole.DisplayRole) for selected_row in selected_rows ]

        self.logger.debug('__list_select_event - map_selected.emit ->')
        self.map_selected.emit(md5_strs)
        self.logger.debug('__list_select_event - map_selected.emit <-')
