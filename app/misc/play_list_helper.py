import time
import multiprocessing
import numpy as np
import pandas as pd

from osu_analysis import Mod
from app.file_managers import MapsDB, score_data_obj


class PlayListHelper():

    @staticmethod
    def do_read(md5_str):
        score_data = score_data_obj.data(md5_str)

        return [
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
