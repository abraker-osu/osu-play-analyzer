import numpy as np
import math

from osu_analysis import BeatmapIO, ReplayIO, StdMapData, StdReplayData, StdScoreData, Gamemode
from app.misc.utils import Utils
from app.misc.osu_utils import OsuUtils


class DataProcessing():

    @staticmethod
    def get_map_data_from_file(file_name):
        try: beatmap = BeatmapIO.open_beatmap(file_name)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error opening map'))
            return None

        return DataProcessing.get_map_data_from_object(beatmap)


    @staticmethod
    def get_map_data_from_object(beatmap):
        if beatmap.gamemode != Gamemode.OSU:
            print(f'{Gamemode(beatmap.gamemode)} gamemode is not supported')
            return None

        try: map_data = StdMapData.get_map_data(beatmap)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error reading map'))
            return None

        return map_data


    @staticmethod
    def get_replay_data_from_file(file_name):
        try: replay = ReplayIO.open_replay(file_name)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error opening replay'))
            return None

        return DataProcessing.get_replay_data_from_object(replay)


    @staticmethod
    def get_replay_data_from_object(replay):
        try: replay_data = StdReplayData.get_replay_data(replay)
        except Exception as e:
            print(Utils.get_traceback(e, 'Error reading replay'))
            return None

        return replay_data


    @staticmethod
    def process_mods(map_data, replay_data, replay):
        if replay.mods.has_mod('DT') or replay.mods.has_mod('NC'):
            map_data['time'] /= 1.5
            replay_data['time'] /= 1.5
            return

        if replay.mods.has_mod('HT'):
            map_data['time'] *= 1.5
            replay_data['time'] *= 1.5
            return

        if replay.mods.has_mod('HR'):
            map_data['x'] = -map_data['x']
            map_data['y'] = -map_data['y']

    
    @staticmethod
    def get_score_data(map_data, replay_data, ar, cs):
        # Process score data
        settings = StdScoreData.Settings()
        settings.ar_ms = OsuUtils.ar_to_ms(ar)
        settings.hitobject_radius = OsuUtils.cs_to_px(cs)
        settings.pos_hit_range = 100        # ms point of late hit window
        settings.neg_hit_range = 100        # ms point of early hit window
        settings.pos_hit_miss_range = 100   # ms point of late miss window
        settings.neg_hit_miss_range = 100   # ms point of early miss window

        score_data = StdScoreData.get_score_data(replay_data, map_data, settings)
        
        return map_data, replay_data, score_data


    @staticmethod
    def get_difficulty_data(score_data, ar):
        """
        Calculates the difficulty vector for each note
        diff_vec = 
            [ 
                dt,       # BPM (recorded in ms)
                dt_dec,   # time since last BPM increase (ms)
                dt_inc,   # time since last BPM decrease (ms)
                ds,       # distance from last note (osu!px)
                Θ         # angle formed by current and last two notes (deg)
            ]
        """
        map_x = score_data['map_x'].values
        map_y = score_data['map_y'].values
        map_t = score_data['map_t'].values

        act_type = score_data['action'].values  # What action was performed (press, release, hold)
        scr_type = score_data['type'].values    # What the resultant score action was (hit press, hit release, miss, empty, etc)
        
        press_select = (act_type == StdScoreData.ACTION_PRESS)
        empty_filter = (scr_type != StdScoreData.TYPE_EMPTY)
        
        note_start_select = press_select & empty_filter
        note_start_idx_ref = np.arange(note_start_select.shape[0])[note_start_select]
        not_empty_idx_ref = np.arange(empty_filter.shape[0])[empty_filter]

        def __get_note_dt():
            """
            Gets the time interal between each note
            Data that does not pertain to a valid entries is marked as np.nan
            
            Entries consist of score points related to press, release, etc. 
            An entry is valid if:
                - The entry is a press for any note but the first one
            """
            note_start_map_t = map_t[note_start_select]

            dt = np.empty(map_t.shape[0]) * np.nan
            dt[note_start_idx_ref[1:]] = note_start_map_t[1:] - note_start_map_t[:-1]

            return dt

        def __get_dt_dec():
            """
            Get the time passed since last time interval decrease (BPM increase)
            Data that does not pertain to a valid entries is marked as np.nan
            
            Entries consist of score points related to press, release, etc. 
            An entry is valid if:
                - The entry is a press for any note
            """
            note_start_map_t = map_t[note_start_select]

            dt0 = note_start_map_t[1:-1] - note_start_map_t[:-2]   # t1 - t0
            dt1 = note_start_map_t[2:] - note_start_map_t[1:-1]    # t2 - t1

            dt_dec = np.empty(map_t.shape[0]) * np.nan

            # The first inverval decrease comes from lack of notes before the start of the map. 
            # The time since last decrease for first note is ALWAYS 0
            # The time since last decrease for the second note is ALWAYS the time between the first and second notes
            dt_dec[note_start_idx_ref[0]] = 0
            dt_dec[note_start_idx_ref[1]] = dt0[0]

            ms = dt0[0]

            # How much the interval needs to change by to be considered a BPM increase
            # For example, if the previous interval is 100ms and the current is 50ms,
            # then the interval is considered a BPM increase (1/4 snap to 1/8 or 1/2 to 1/4, etc). 
            # On the other hand, if the previous interval is 100ms and the interval changes to 95ms, 
            # then the interval is not considered a BPM increase.
            d_threshold = 0.95  # Must be <= 1

            for i in range(dt0.shape[0]):
                if dt1[i] < dt0[i]*d_threshold:
                    # Next note is closer to the previous one than expected
                    # Reset time since last decrease
                    ms = 0
                else:
                    # Otherwise, keep adding time; Current note is t2, 
                    # so the time interval to add is t2 - t1
                    ms += dt1[i]

                dt_dec[note_start_idx_ref[i + 2]] = ms

            return dt_dec

        def __get_dt_inc():
            """
            Get the time passed since last time interval increase (BPM decrease)
            Data that does not pertain to a valid entries is marked as np.nan
            
            Entries consist of score points related to press, release, etc. 
            An entry is valid if:
                - The entry is a press for any note
            """
            note_start_map_t = map_t[note_start_select]

            dt0 = note_start_map_t[1:-1] - note_start_map_t[:-2]   # t1 - t0
            dt1 = note_start_map_t[2:] - note_start_map_t[1:-1]    # t2 - t1

            dt_inc = np.empty(map_t.shape[0]) * np.nan

            # The first inverval increase comes as soon as note t2 is further than expected
            # This makes the time since last increase for first and second notes ALWAYS 0
            dt_inc[note_start_idx_ref[0:2]] = 0

            ms = 0

            # How much the interval needs to change by to be considered a BPM decrease
            # For example, if the previous interval is 100ms and the current is 200ms,
            # then the interval is considered a BPM decrease (1/8 snap to 1/4 or 1/4 to 1/2, etc). 
            # On the other hand, if the previous interval is 100ms and the interval changes to 105ms, 
            # then the interval is not considered a BPM increase.
            d_threshold = 1.05  # Must be >= 1

            for i in range(dt0.shape[0]):
                if dt1[i] > dt0[i]*d_threshold:
                    # Next note is further from the previous than expected, but actual
                    # time resets from the moment the note that was expected did not occur.
                    # This expected note would have been at t1 + (t1 - t0), so we need to determine
                    # the time difference between t2 and t1 + (t1 - t0), which is (t2 - t1) - (t1 - t0)
                    ms = dt1[i] - dt0[i]
                else:
                    # Otherwise, keep adding time; Current note is t2, 
                    # so the time interval to add is t2 - t1
                    ms += dt1[i]

                dt_inc[note_start_idx_ref[i + 2]] = ms

            return dt_inc
            
        def __get_ds():
            """
            Gets the spacing between each note
            Data that does not pertain to a valid entries is marked as np.nan
            
            Entries consist of score points related to press, release, etc. 
            An entry is valid if:
                - It is not an empty hit
            Entries include:
                - All scorepoints, regardless of whether they are press, release, or hold.
            """
            not_empty_map_x = map_x[empty_filter]
            not_empty_map_y = map_y[empty_filter]

            dx = not_empty_map_x[1:] - not_empty_map_x[:-1]  # x1 - x0
            dy = not_empty_map_y[1:] - not_empty_map_y[:-1]  # y1 - y0

            ds = np.empty(map_x.shape[0]) * np.nan
            
            # Cursor is assumed to start on first note, so distance from prev point is 0
            ds[not_empty_idx_ref[0]] = 0
            ds[not_empty_idx_ref[1:]] = (dx**2 + dy**2)**0.5

            return ds

        def __get_angles():
            """
            Gets the angle between each note
            Data that does not pertain to a valid entries is marked as np.nan
            
            Entries consist of score points related to press, release, etc. 
            An entry is valid if:
                - It is not an empty hit
                - It is not the first or last entry 
                    (requires a point present before and after to calc angle of current point)
            """
            not_empty_map_x = map_x[empty_filter]
            not_empty_map_y = map_y[empty_filter]

            dx0 = not_empty_map_x[1:-1] - not_empty_map_x[:-2]   # x1 - x0
            dx1 = not_empty_map_x[2:] - not_empty_map_x[1:-1]    # x2 - x1

            dy0 = not_empty_map_y[1:-1] - not_empty_map_y[:-2]   # y1 - y0
            dy1 = not_empty_map_y[2:] - not_empty_map_y[1:-1]    # y2 - y1
            
            theta_d0 = np.arctan2(dy0, dx0)*(180/math.pi)
            theta_d1 = np.arctan2(dy1, dx1)*(180/math.pi)

            thetas = np.abs(theta_d1 - theta_d0)
            thetas[thetas > 180] = 360 - thetas[thetas > 180]
            thetas = np.round(thetas)

            angles = np.empty(map_x.shape[0]) * np.nan
            
            # angles[0] = np.nan (implicit)
            angles[not_empty_idx_ref[1:-1]] = thetas
            # angles[-1] = np.nan (implicit)

            return angles

        def __get_notes_visible():
            """
            Gets the number of notes visible at each time point
            Data that does not pertain to a valid entries is marked as np.nan
            
            Entries consist of score points related to press, release, etc. 
            An entry is valid if:
                - All entries are valid

            # TODO: Figure out how I want to do this. Number of notes present is
            #       not representative of visual difficulty due to sliders. Perhaps
            #       total hitobject area is a better metric? Will need to be normalized
            *       to CS.
            #
            #       See https://discord.com/channels/546120878908506119/886986744090734682/928768553899925535
            #       for brief idea regarding area and overlap metrics.
            """
            timings = map_t[empty_filter]
            ar_ms = OsuUtils.ar_to_ms(ar)

            notes_visible = np.empty(map_x.shape[0]) * np.nan
            for i in range(timings.shape[0]):
                ar_select = (timings[i] <= timings) & (timings <= (timings[i] + ar_ms))
                notes_visible[not_empty_idx_ref[i]] = np.count_nonzero(ar_select)

            return notes_visible


        dt     = __get_note_dt()
        dt_dec = __get_dt_dec()
        dt_inc = __get_dt_inc()
        ds     = __get_ds()
        angles = __get_angles()

        return dt, dt_dec, dt_inc, ds, angles



    @staticmethod
    def get_performance_data(score_data):
        #hit_types_miss = score_data['type'] == StdScoreData.TYPE_MISS
        #num_total = score_data['type'].values.shape[0]
        #num_misses = score_data['type'].values[hit_types_miss].shape[0]

        ### Too many misses tends to falsely lower the deviation. Disallow plays with >10% misses
        #print(f'num total hits: {num_total}   num: misses {num_misses} ({100 * num_misses/num_total:.2f}%)')
        #if num_misses/num_total > 0.1:
        #    raise Exception('Invalid Play. Too many misses')
        
        x_offsets = score_data['replay_x'].values - score_data['map_x'].values
        y_offsets = score_data['replay_y'].values - score_data['map_y'].values
        t_offsets = score_data['replay_t'].values - score_data['map_t'].values

        # Correct for incoming direction
        dx = score_data['map_x'].values[1:] - score_data['map_x'].values[:-1]
        dy = score_data['map_y'].values[1:] - score_data['map_y'].values[:-1]

        map_thetas = np.arctan2(dy, dx)
        hit_thetas = np.arctan2(y_offsets, x_offsets)
        mags = (x_offsets**2 + y_offsets**2)**0.5

        x_offsets[1:] = mags[1:]*np.cos(map_thetas - hit_thetas[1:])
        y_offsets[1:] = mags[1:]*np.sin(map_thetas - hit_thetas[1:])

        # Filter out nans that happen due to misc reasons (usually due to empty slices or div by zero)
        #nan_filter = ~np.isnan(x_offsets) & ~np.isnan(y_offsets)

        #x_offsets = x_offsets[nan_filter]
        #y_offsets = y_offsets[nan_filter]
        #t_offsets = t_offsets[nan_filter]

        return x_offsets, y_offsets, t_offsets


    @staticmethod
    def get_data(score_data, timestamp, map_md5, mods, cs, ar):
        dt, dt_dec, dt_inc, ds, angles = DataProcessing.get_difficulty_data(score_data, ar)
        x_offsets, y_offsets, t_offsets = DataProcessing.get_performance_data(score_data)
        hash_mask = 0xFFFFFFFFFFFF0000

        if not (dt.shape[0] == dt_dec.shape[0] == dt_inc.shape[0] == ds.shape[0] == angles.shape[0] == x_offsets.shape[0] == y_offsets.shape[0] == t_offsets.shape[0]):
            print(
                'Data shapes do not match:',
                f'   DT: {dt.shape[0]} '
                f'   DT_DEC: {dt_dec.shape[0]} '
                f'   DT_INC: {dt_inc.shape[0]} '
                f'   DS: {ds.shape[0]} '
                f'   ANGLES: {angles.shape[0]} '
                f'   X_OFFSETS: {x_offsets.shape[0]} '
                f'   Y_OFFSETS: {y_offsets.shape[0]} '
                f'   T_OFFSETS: {t_offsets.shape[0]} '
            )
            raise Exception('Data shapes do not match')

        timings = score_data['map_t'].values
        htypes = score_data['type'].values
        otypes = score_data['action'].values

        if not (dt.shape[0] == timings.shape[0] == htypes.shape[0] == otypes.shape[0]):
            print(
                'Data shapes do not match:',
                f'   DT: {dt.shape[0]} '
                f'   TIMINGS: {timings.shape[0]} '
                f'   HTYPES: {htypes.shape[0]} '
                f'   OTYPES: {otypes.shape[0]} '
            )

        timestamp = np.full_like(dt, timestamp)
        md5_hash = np.full_like(dt, int(map_md5, 16) & hash_mask)
        mod_data = np.full_like(dt, mods)
        cs = np.full_like(dt, cs)
        ar = np.full_like(dt, ar)

        return np.c_[
            timestamp,  # TIMESTAMP 
            md5_hash,   # MAP_MD5
            mod_data,   # MODS
            cs,         # CS        
            ar,         # AR        
            htypes,     # HIT_TYPE
            otypes,     # OBJECT_TYPE
            timings,    # TIMINGS   
            dt,         # DT        
            dt_dec,     # DT_INC    
            dt_inc,     # DT_DEC    
            ds,         # DS        
            angles,     # ANGLE     
            x_offsets,  # X_OFFSETS 
            y_offsets,  # Y_OFFSETS 
            t_offsets,  # T_OFFSETS
        ]
 