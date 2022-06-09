import time
import itertools
import multiprocessing
import numpy as np
import pandas as pd


from osu_analysis import Mod
from app.misc.task_proc import TaskProc
from app.file_managers import score_data_obj
from app.file_managers.db_mgr import MapsDB


class PlayListHelper():

    def __init__(self):
        self.data_queue = multiprocessing.Queue()



    def reload_map_list_worker_thread(self):
        """
        Splits workload into batches of 100 maps to process
        and distributes those batches across 4 processes.

        This allows the gui to continue working while adding
        loaded maps as they are processed. Sends completed
        batches via `self.data_queue`.
        """
        # Thanks https://stackoverflow.com/a/62913856
        def batcher(iterable, batch_size):
            iterator = iter(iterable)
            while batch := list(itertools.islice(iterator, batch_size)):
                yield [ _._v_pathname for _ in batch ]

        batch_size = 100
        
        task_proc = TaskProc(num_workers=4)
        task_proc.start(task=self.do_read_task)

        nodes = score_data_obj.data()._handle.get_node('/')
        for batch in batcher(nodes, batch_size):
            task_proc.add(batch)

        task_proc.end()


    def do_read_task(self, data):
        """
        Processes a batch of md5 strings to get map data
        """
        play_list_data = map(PlayListHelper.do_read, data)
        self.data_queue.put(
            pd.DataFrame(play_list_data, columns=
                ['md5', 'Name', 'Mods', 'Time', 'Data', 'Avg BPM', 'Avg Lin Vel', 'Avg Ang Vel']
            )
        )


    @staticmethod
    def do_read(md5_str):
        """
        Processes a single md5 str to get map data
        """
        score_data = score_data_obj.data(md5_str)

        return [
            md5_str,
            PlayListHelper.map_name_str(md5_str),
            PlayListHelper.map_mods_str(score_data),
            PlayListHelper.map_timestamp_str(score_data),
            PlayListHelper.map_num_data(score_data),
            PlayListHelper.map_avg_bpm(score_data),
            PlayListHelper.map_avg_lin_vel(score_data),
            PlayListHelper.map_avg_ang_vel(score_data),
        ]


    @staticmethod
    def map_name_str(md5_str):
        result, _ = MapsDB.get_map_file_name(md5_str[1:])
        if result == None:
            return md5_str

        return result.replace('\\', '/').split('/')[-1]


    @staticmethod
    def map_mods_str(score_data):
        mods = score_data['MODS'].values[0]
        mods_text = Mod(int(mods)).get_mods_txt()
        mods_text = f' +{mods_text}' if len(mods_text) != 0 else ''


    @staticmethod
    def map_timestamp_str(score_data):
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
    def map_num_data(score_data):
        return score_data.shape[0]


    @staticmethod
    def map_avg_bpm(score_data): 
        data = 15000/score_data['DIFF_T_PRESS_DIFF'].values
        data = data[~np.isnan(data)]

        return f'{np.mean(data):.2f}'


    @staticmethod
    def map_avg_lin_vel(score_data):  
        data = score_data['DIFF_XY_LIN_VEL'].values
        data = data[~np.isnan(data)]

        return f'{np.mean(data):.2f}'


    @staticmethod
    def map_avg_ang_vel(score_data):    
        data = score_data['DIFF_XY_ANG_VEL'].values
        data = data[~np.isnan(data)]

        return f'{np.mean(data):.2f}'


    @staticmethod
    def do_get_timestamps(map_md5_str):
        score_data = score_data_obj.data(map_md5_str)
        return np.unique(score_data.index.get_level_values(0))
