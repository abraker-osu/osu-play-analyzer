import numpy as np


class ScoreNpyData():

    SCORE_ID    = 0   # ID of score
    TIMESTAMP   = 1   # Timestamp of the play
    MAP_MD5_LH  = 2   # Map's md5 hash (lowerhalf)
    MAP_MD5_UH  = 3   # Map's md5 hash (upperhalf)
    MODS        = 4   # Mods used
    CS          = 5   # Map's CS
    AR          = 6   # Map's AR    
    IDX         = 7   # Index of the scorepoint in the map
    TYPE_MAP    = 8   # Action type (0: Press, 1: Hold, 2: Release)
    TYPE_HIT    = 9   # Hit type (0: HITP, 1: HITR, 2: AIMH, 3: MISS, 4: EMPTY)
    T_MAP       = 10  # Timings of the scorepoint
    T_HIT       = 11  # Timings of the hit
    X_MAP       = 12  # X position of the scorepoint
    X_HIT       = 13  # X position of the hit
    Y_MAP       = 14  # Y position of the scorepoint
    Y_HIT       = 15  # Y position of the hit
    NUM_COLS    = 16

    @staticmethod
    def get_md5_str(md5_lh, md5_uh):
        return f'{md5_uh:016x}{md5_lh:016x}'


    @staticmethod
    def get_md5s(data):
        # LSB first
        return data[:, [ScoreNpyData.MAP_MD5_LH, ScoreNpyData.MAP_MD5_UH]].astype(np.uint64)


    @staticmethod
    def get_unique_md5s(data):
        # LSB first
        return np.unique(data[:, [ScoreNpyData.MAP_MD5_LH, ScoreNpyData.MAP_MD5_UH]], axis=0).astype(np.uint64)


    @staticmethod
    def get_unique_meta(data):
        # LSB first
        return np.unique(data[:, [ScoreNpyData.MAP_MD5_LH, ScoreNpyData.MAP_MD5_UH, ScoreNpyData.TIMESTAMP]], axis=0)


    @staticmethod
    def select_md5s(data, md5_strs):
        hash_mask = 0xFFFFFFFFFFFFFFFF
        md5_data = data[:, [ScoreNpyData.MAP_MD5_LH, ScoreNpyData.MAP_MD5_UH]].astype(np.uint64)
        
        select = np.zeros((data.shape[0], ), dtype=np.bool)

        for md5_str in md5_strs:
            md5_int = int(md5_str, 16)

            map_int_lh = (md5_int >>  0) & hash_mask
            map_int_uh = (md5_int >> 64) & hash_mask

            select |= (map_int_uh == md5_data[:, 1]) & (map_int_lh == md5_data[:, 0])

        return select


    @staticmethod
    def select_md5(data, md5_lh, md5_uh):
        return \
            (data[:, ScoreNpyData.MAP_MD5_UH].astype(np.uint64) == md5_uh) & \
            (data[:, ScoreNpyData.MAP_MD5_LH].astype(np.uint64) == md5_lh)


    @staticmethod
    def select_meta(data, md5_lh, md5_uh, timestamp):
        return \
            (data[:, ScoreNpyData.MAP_MD5_UH].astype(np.uint64)  == md5_uh) & \
            (data[:, ScoreNpyData.MAP_MD5_LH].astype(np.uint64)  == md5_lh) & \
            (data[:, ScoreNpyData.TIMESTAMP] == timestamp)


class DiffNpyData():

    MAP_MD5_LH   = 0   # Map hash lower half
    MAP_MD5_UH   = 1   # Map hash upper half
    TIMESTAMP    = 2   # Timestamp
    IDX          = 3   # Score point index
    T_PRESS_DIFF = 4   # Time difference between presses
    T_PRESS_RATE = 5  # Time difference across 3 presses
    T_PRESS_INC  = 6   # Time since last increase between scorepoint press timing
    T_PRESS_DEC  = 7   # Time since last decrease between scorepoint press timing
    T_PRESS_RHM  = 8   # Scorepoint press's relative spacing compared to other scorepoint presses
    T_HOLD_DUR   = 9   # Time duration of hold
    XY_DIST      = 10   # Distance between every scorepoint
    XY_ANGLE     = 11  # Angle between every scorepoint
    XY_LIN_VEL   = 12  # Linear velocity between every scorepoint
    XY_ANG_VEL   = 13  # Angular velocity between every scorepoint
    VIS_VISIBLE  = 14  # Number of notes visible
    NUM_COLS     = 15

    @staticmethod
    def get_data_meta(diff_data, md5_lh, md5_uh, timestamp):
        meta_data = diff_data[:, [DiffNpyData.MAP_MD5_UH, DiffNpyData.MAP_MD5_LH, DiffNpyData.TIMESTAMP]]
        select = \
            (meta_data[:, 2] == md5_uh) & \
            (meta_data[:, 1] == md5_lh) & \
            (meta_data[:, 0] == timestamp)

        return diff_data[select, :]


    @staticmethod
    def is_invalid(diff_data):
        return np.isnan(diff_data)


    @staticmethod
    def get_data_score(diff_data, score_data):
        # List of unique entries
        unique_meta_data = np.unique(score_data[:, [ScoreNpyData.MAP_MD5_LH, ScoreNpyData.MAP_MD5_UH, ScoreNpyData.TIMESTAMP]], axis=0)

        # The size of entry in diff data should match the one in score data
        # If it doesn't, it either non-existent or corrupted
        data_out = np.zeros((score_data.shape[0], DiffNpyData.NUM_COLS))*np.nan
        
        # The selection features a column for diff data and a column for score data
        # This allows to match the selection blocks in diff data with the selection blocks in score data
        select_score = np.zeros((score_data.shape[0], ), dtype=np.bool)
        select_diff  = np.zeros((diff_data.shape[0], ), dtype=np.bool)

        for meta_data in unique_meta_data:
            select_score |= \
                (score_data[:, ScoreNpyData.MAP_MD5_LH] == meta_data[0]) & \
                (score_data[:, ScoreNpyData.MAP_MD5_UH] == meta_data[1]) & \
                (score_data[:, ScoreNpyData.TIMESTAMP]  == meta_data[2])

            select_diff |= \
                (diff_data[:, DiffNpyData.MAP_MD5_LH] == meta_data[0]) & \
                (diff_data[:, DiffNpyData.MAP_MD5_UH] == meta_data[1]) & \
                (diff_data[:, DiffNpyData.TIMESTAMP]  == meta_data[2])

            # Check to make data can be copied properly
            if np.count_nonzero(select_score) != np.count_nonzero(select_diff):
                continue

            data_out[select_score, :] = diff_data[select_diff, :]

        return data_out

class PlayNpyData():

    SCORE_ID     = 0   # ID of score
    TIMESTAMP    = 1   # Timestamp of the play
    MAP_MD5_LH   = 2   # Map's md5 hash (lowerhalf)
    MAP_MD5_UH   = 3   # Map's md5 hash (upperhalf)
    MODS         = 4   # Mods used
    CS           = 5   # Circle size (radius in osu!px)
    AR           = 6   # Approach rate (in ms)
    IDX          = 7   # Index of the scorepoint in the map
    TYPE_MAP     = 8   # Action type (0: Press, 1: Hold, 2: Release)
    TYPE_HIT     = 9   # Hit type (0: HITP, 1: HITR, 2: AIMH, 3: MISS, 4: EMPTY)
    T_MAP        = 10  # Timings of the scorepoint
    T_HIT        = 11  # Timings of the hit
    X_MAP        = 12  # X position of the scorepoint
    X_HIT        = 13  # X position of the hit
    Y_MAP        = 14  # Y position of the scorepoint
    Y_HIT        = 15  # Y position of the hit
    #MAP_MD5_LH   = 16  # Map hash lower half
    #MAP_MD5_UH   = 17  # Map hash upper half
    #TIMESTAMP    = 18  # Timestamp
    #IDX          = 19  # Score point index
    T_PRESS_DIFF = 20  # Time difference between presses
    T_PRESS_RATE = 21  # Time difference across 3 presses
    T_PRESS_INC  = 22  # Time since last increase between scorepoint press timing
    T_PRESS_DEC  = 23  # Time since last decrease between scorepoint press timing
    T_PRESS_RHM  = 24  # Scorepoint press's relative spacing compared to other scorepoint presses
    T_HOLD_DUR   = 25  # Time duration of hold
    XY_DIST      = 26  # Distance between every scorepoint
    XY_ANGLE     = 27  # Angle between every scorepoint
    XY_LIN_VEL   = 28  # Linear velocity between every scorepoint
    XY_ANG_VEL   = 29  # Angular velocity between every scorepoint
    VIS_VISIBLE  = 30  # Number of notes visible
    NUM_COLS     = 31

    @staticmethod
    def get_md5s(data):
        # LSB first
        return data[:, [ScoreNpyData.MAP_MD5_LH, ScoreNpyData.MAP_MD5_UH]].astype(np.uint64)

    @staticmethod
    def get_md5_str(md5_lh, md5_uh):
        return f'{md5_uh:016x}{md5_lh:016x}'


    @staticmethod
    def get_unique_md5s(data):
        # LSB first
        return np.unique(data[:, [ScoreNpyData.MAP_MD5_LH, ScoreNpyData.MAP_MD5_UH]], axis=0).astype(np.uint64)


    @staticmethod
    def get_unique_meta(data):
        # LSB first
        return np.unique(data[:, [ScoreNpyData.MAP_MD5_LH, ScoreNpyData.MAP_MD5_UH, ScoreNpyData.TIMESTAMP]], axis=0)


    @staticmethod
    def select_md5s(data, md5_strs):
        hash_mask = 0xFFFFFFFFFFFFFFFF
        md5_data = data[:, [ScoreNpyData.MAP_MD5_LH, ScoreNpyData.MAP_MD5_UH]].astype(np.uint64)
        
        select = np.zeros((data.shape[0], ), dtype=np.bool)

        for md5_str in md5_strs:
            md5_int = int(md5_str, 16)

            map_int_lh = (md5_int >>  0) & hash_mask
            map_int_uh = (md5_int >> 64) & hash_mask

            select |= (map_int_uh == md5_data[:, 1]) & (map_int_lh == md5_data[:, 0])

        return select


    @staticmethod
    def select_md5(data, md5_lh, md5_uh):
        return \
            (data[:, ScoreNpyData.MAP_MD5_UH] == md5_uh) & \
            (data[:, ScoreNpyData.MAP_MD5_LH] == md5_lh)
