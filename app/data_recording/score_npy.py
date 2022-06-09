import numpy as np
import pandas as pd

from osu_analysis import BeatmapIO, ReplayIO, StdMapData, StdReplayData, StdScoreData, Gamemode

from app.misc.Logger import Logger
from app.misc.utils import Utils
from app.misc.osu_utils import OsuUtils


class ScoreNpy():

    logger = Logger.get_logger(__name__)

    @staticmethod
    def __get_map_data_from_file(file_name):
        try: beatmap = BeatmapIO.open_beatmap(file_name)
        except Exception as e:
            ScoreNpy.logger.error(Utils.get_traceback(e, 'Error opening map'))
            return None

        return ScoreNpy.__get_map_data_from_object(beatmap)


    @staticmethod
    def __get_map_data_from_object(beatmap):
        if beatmap.gamemode != Gamemode.OSU:
            ScoreNpy.logger.info(f'{Gamemode(beatmap.gamemode)} gamemode is not supported')
            return None

        try: map_data = StdMapData.get_map_data(beatmap)
        except Exception as e:
            ScoreNpy.logger.error(Utils.get_traceback(e, 'Error reading map'))
            return None

        return map_data


    @staticmethod
    def __get_replay_data_from_file(file_name):
        try: replay = ReplayIO.open_replay(file_name)
        except Exception as e:
            ScoreNpy.logger.error(Utils.get_traceback(e, 'Error opening replay'))
            return None

        return ScoreNpy.__get_replay_data_from_object(replay)


    @staticmethod
    def __get_replay_data_from_object(replay):
        try: replay_data = StdReplayData.get_replay_data(replay)
        except Exception as e:
            ScoreNpy.logger.error(Utils.get_traceback(e, 'Error reading replay'))
            return None

        return replay_data


    @staticmethod
    def __process_mods(map_data, replay_data, replay):
        if replay.mods.has_mod('DT') or replay.mods.has_mod('NC'):
            map_data['time'] /= 1.5
            replay_data['time'] /= 1.5
            return

        if replay.mods.has_mod('HT'):
            map_data['time'] *= 1.5
            replay_data['time'] *= 1.5
            return

        if replay.mods.has_mod('HR'):
            # Do nothing
            pass
            
    
    @staticmethod
    def __get_score_data(map_data, replay_data, cs, ar):
        # Process score data
        settings = StdScoreData.Settings()
        settings.ar_ms = OsuUtils.ar_to_ms(ar)
        settings.hitobject_radius = OsuUtils.cs_to_px(cs)/2
        settings.pos_hit_range = 100        # ms point of late hit window
        settings.neg_hit_range = 100        # ms point of early hit window
        settings.pos_hit_miss_range = 100   # ms point of late miss window
        settings.neg_hit_miss_range = 100   # ms point of early miss window

        score_data = StdScoreData.get_score_data(replay_data, map_data, settings)
        
        return score_data


    @staticmethod
    def __get_data(score_data, timestamp, score_id, mods, map_md5, cs, ar):
        size = score_data.shape[0]

        df = pd.DataFrame()
        df['MD5']         = [ map_md5 ] * size
        df['TIMESTAMP']   = np.full(size, int(timestamp))
        df['MODS']        = np.full(size, mods)
        df['CS']          = np.full(size, cs)
        df['AR']          = np.full(size, ar)
        df['IDXS']        = np.arange(size)
        df['T_MAP']       = score_data['map_t']
        df['X_MAP']       = score_data['map_x']
        df['Y_MAP']       = score_data['map_y']
        df['T_HIT']       = score_data['replay_t']
        df['X_HIT']       = score_data['replay_x']
        df['Y_HIT']       = score_data['replay_y']
        df['TYPE_MAP']    = score_data['action']
        df['TYPE_HIT']    = score_data['type']

        df.set_index(['MD5', 'TIMESTAMP', 'IDXS'], inplace=True)
        return df


    @staticmethod
    def compile_data(beatmap, replay):
        if type(beatmap) is not str:
            map_data = ScoreNpy.__get_map_data_from_object(beatmap)
        else:
            map_data = ScoreNpy.__get_map_data_from_file(beatmap)

        if type(replay) is not str:
            replay_data = ScoreNpy.__get_replay_data_from_object(replay)
        else:
            replay_data = ScoreNpy.__get_replay_data_from_file(replay)

        ScoreNpy.__process_mods(map_data, replay_data, replay)

        # Get data
        try: timestamp = replay.timestamp.timestamp()
        except OSError:
            timestamp = 0

        score_data = ScoreNpy.__get_score_data(
            map_data, 
            replay_data, 
            beatmap.difficulty.cs, 
            beatmap.difficulty.ar
        )
        
        return map_data, replay_data, ScoreNpy.__get_data(
            score_data, 
            timestamp,
            replay.score_id, 
            replay.mods.value, 
            beatmap.metadata.beatmap_md5, 
            beatmap.difficulty.cs, 
            beatmap.difficulty.ar
        )


