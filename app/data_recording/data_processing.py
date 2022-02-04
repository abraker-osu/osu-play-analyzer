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
            # Do nothing
            pass
            
    
    @staticmethod
    def get_score_data(map_data, replay_data, cs, ar):
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
        release_select = (act_type == StdScoreData.ACTION_RELEASE)
        empty_filter = (scr_type != StdScoreData.TYPE_EMPTY)
        
        note_single_select = press_select
        note_slider_select = (press_select | release_select)

        note_single_idx_ref = np.arange(note_single_select.shape[0])[note_single_select]
        note_slider_idx_ref = np.arange(note_slider_select.shape[0])[note_slider_select]
        not_empty_idx_ref = np.arange(empty_filter.shape[0])[empty_filter]

        if not_empty_idx_ref.shape[0] <= 3:
            print('Warning: Not enough notes to calculate difficulty')

        def __get_note_dt():
            """
            Gets the time interal between each note
            Data that does not pertain to a valid entries is marked as np.nan
            
            Entries consist of score points related to press, release, etc. 
            An entry is valid if:
                - The entry is a press for any note but the first one
            """
            note_start_map_t = map_t[note_single_select]

            dt = np.empty(map_t.shape[0]) * np.nan

            # Not enough note presses
            if note_single_idx_ref.shape[0] <= 2:
                return dt

            dt[note_single_idx_ref[1:]] = note_start_map_t[1:] - note_start_map_t[:-1]

            return dt

        def __get_dt_dec():
            """
            Get the time passed since last time interval decrease (BPM increase)
            Data that does not pertain to a valid entries is marked as np.nan
            
            Entries consist of score points related to press, release, etc. 
            An entry is valid if:
                - The entry is a press for any note
            """
            note_start_map_t = map_t[note_single_select]

            dt0 = note_start_map_t[1:-1] - note_start_map_t[:-2]   # t1 - t0
            dt1 = note_start_map_t[2:] - note_start_map_t[1:-1]    # t2 - t1

            dt_dec = np.empty(map_t.shape[0]) * np.nan

            # Not enough note presses
            if note_single_idx_ref.shape[0] <= 3:
                return dt_dec

            # The first inverval decrease comes from lack of notes before the start of the map. 
            # The time since last decrease for first note is ALWAYS 0
            # The time since last decrease for the second note is ALWAYS the time between the first and second notes
            dt_dec[note_single_idx_ref[0]] = 0
            dt_dec[note_single_idx_ref[1]] = dt0[0]

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

                dt_dec[note_single_idx_ref[i + 2]] = ms

            return dt_dec

        def __get_dt_inc():
            """
            Get the time passed since last time interval increase (BPM decrease)
            Data that does not pertain to a valid entries is marked as np.nan
            
            Entries consist of score points related to press, release, etc. 
            An entry is valid if:
                - The entry is a press for any note
            """
            note_start_map_t = map_t[note_single_select]

            dt0 = note_start_map_t[1:-1] - note_start_map_t[:-2]   # t1 - t0
            dt1 = note_start_map_t[2:] - note_start_map_t[1:-1]    # t2 - t1

            dt_inc = np.empty(map_t.shape[0]) * np.nan

            # Not enough note presses
            if note_single_idx_ref.shape[0] <= 3:
                return dt_inc

            # The first inverval increase comes as soon as note t2 is further than expected
            # This makes the time since last increase for first and second notes ALWAYS 0
            dt_inc[note_single_idx_ref[0:2]] = 0

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

                dt_inc[note_single_idx_ref[i + 2]] = ms

            return dt_inc
            
        def __get_ds():
            """
            Gets the spacing between each aimpoint
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

            # Not enough notes
            if not_empty_idx_ref.shape[0] <= 2:
                return ds
            
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
                - It is a single note
                - It is either the start or end of a slider
                    (in-between slider aimpoints are not considered)

            TODO: Ignore overlaps because https://i.imgur.com/Iwuajar.gif
            """
            slider_map_x = map_x[note_slider_select]
            slider_map_y = map_y[note_slider_select]

            dx0 = slider_map_x[1:-1] - slider_map_x[:-2]   # x1 - x0
            dx1 = slider_map_x[2:] - slider_map_x[1:-1]    # x2 - x1

            dy0 = slider_map_y[1:-1] - slider_map_y[:-2]   # y1 - y0
            dy1 = slider_map_y[2:] - slider_map_y[1:-1]    # y2 - y1
            
            theta_d0 = np.arctan2(dy0, dx0)*(180/math.pi)
            theta_d1 = np.arctan2(dy1, dx1)*(180/math.pi)

            thetas = np.abs(theta_d1 - theta_d0)
            thetas[thetas > 180] = 360 - thetas[thetas > 180]
            thetas = np.round(thetas)

            angles = np.empty(map_x.shape[0]) * np.nan

            # Not enough notes
            if note_slider_idx_ref.shape[0] <= 3:
                return angles
            
            # angles[0] = np.nan (implicit)
            angles[note_slider_idx_ref[1:-1]] = thetas
            # angles[-1] = np.nan (implicit)

            return angles


        def __get_rhythm_percent():
            # TODO: See https://discord.com/channels/546120878908506119/886986744090734682/935701345451786290
            # https://cdn.discordapp.com/attachments/886986744090734682/935701344721961010/unknown.png
            #
            # somewhere between 0.25 and 0.5, 0.5 and 0.75 would be considered irregular snaps, therefore higher rhythmic complexity 
            # for slightly off from 50%, I expect offsets equal to (t2 - t0)/2 - (t2 - t0)*percent 
            """
            Gets % the note is spaced from previous note to next note
            Data that does not pertain to a valid entries is marked as np.nan
            
            Entries consist of score points related to press, release, etc. 
            An entry is valid if:
                - The entry is a press
                - First 2 notes are excluded
            """
            note_start_map_t = map_t[note_single_select]

            n_percent = np.empty(map_t.shape[0]) * np.nan

            # Not enough note presses
            if note_single_idx_ref.shape[0] <= 2:
                return n_percent

            # tn[2] - tn[0]
            total_interval = note_start_map_t[2:] - note_start_map_t[:-2]

            # tn[1] - tn[0]
            interval = note_start_map_t[1:] - note_start_map_t[:-1]

            n_percent[note_single_idx_ref[2:]] = interval[:-1]/total_interval
            return n_percent


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

        dt      = __get_note_dt()
        dt_dec  = __get_dt_dec()
        dt_inc  = __get_dt_inc()
        ds      = __get_ds()
        angles  = __get_angles()
        dt_rhym = __get_rhythm_percent()

        return dt, dt_dec, dt_inc, ds, angles, dt_rhym


    @staticmethod
    def get_performance_data(score_data):
        map_x = score_data['map_x'].values
        map_y = score_data['map_y'].values
        map_t = score_data['map_t'].values

        act_type = score_data['action'].values  # What action was performed (press, release, hold)
        scr_type = score_data['type'].values    # What the resultant score action was (hit press, hit release, miss, empty, etc)

        hit_t = score_data['replay_t'].values
        
        press_select = (act_type == StdScoreData.ACTION_PRESS)
        valid_select = (scr_type == StdScoreData.TYPE_HITP)

        def __get_hit_interval_offset():
            """
            Gets the difference between tap timing and note timing across 3 notes
            Data that does not pertain to a valid entries is marked as np.nan
            
            Entries consist of score points related to press 
            An entry is valid if:
                - The entry is a press for any note 
                - First 2 notes are invalid
            """
            dt_notes = np.empty(map_t.shape[0]) * np.nan
            dt_hits  = np.empty(map_t.shape[0]) * np.nan

            # Not enough note presses
            if np.sum(press_select) <= 3:
                return dt_notes, dt_hits

            dt_notes_idx_ref = np.arange(map_t.shape[0])
            dt_hits_idx_ref  = np.arange(map_t.shape[0])

            note_start_map_t = map_t[press_select]
            hit_press_replay_t = hit_t[press_select]

            # size = orig[note_press_select]
            dt_notes_idx_ref = dt_notes_idx_ref[press_select]
            dt_hits_idx_ref = dt_hits_idx_ref[press_select]

            #print('note_start_map_t: ', note_start_map_t.shape[0])
            #print('dt_notes_mask: ', np.sum(dt_notes_mask))
            #print('dt_hits_mask: ', dt_hits_mask[:10])

            # Timing t[i]
            note_timings0 = note_start_map_t[:-2]
            hit_timings0 = hit_press_replay_t[:-2]

            # Timing t[i + 2]
            note_timings1 = note_start_map_t[2:]
            hit_timings1 = hit_press_replay_t[2:]

            # d_tn = tn[i + 2] - tn[i]
            # d_th = (th[i + 2] - tn[i + 2]) - (th[i] - tn[i])
            _dt_notes = note_timings1 - note_timings0
            _dt_hits  = (hit_timings1 - hit_timings0) - (note_timings1 - note_timings0)

            # size = orig[note_press_select] - 2
            dt_notes_idx_ref = dt_notes_idx_ref[2:]
            
            # All 3 notes in question must be valid hit presses
            # size = (orig[note_press_select] - 2)[valid_select]
            valid_press_select = valid_select[dt_hits_idx_ref]
            valid_press_select = (valid_press_select[2:] & valid_press_select[1:-1] & valid_press_select[:-2])
            dt_hits_idx_ref = dt_hits_idx_ref[2:][valid_press_select]

            # Record interval across 3 notes for all presses, but for hits record only valid presses
            dt_notes[dt_notes_idx_ref] = _dt_notes
            dt_hits[dt_hits_idx_ref] = _dt_hits[valid_press_select]

            return dt_notes, dt_hits

        def __get_position_offsets():
            """
            Gets rotation compensated offset between notes. Rotation compensated means, 
            all triplets of notes are rotated to be orthogonal to a common direction
            """
            x_offsets = score_data['replay_x'].values - score_data['map_x'].values
            y_offsets = score_data['replay_y'].values - score_data['map_y'].values

            # Correct for incoming direction
            dx = map_x[1:] - map_x[:-1]
            dy = map_y[1:] - map_y[:-1]

            map_thetas = np.arctan2(dy, dx)
            hit_thetas = np.arctan2(y_offsets, x_offsets)
            mags = (x_offsets**2 + y_offsets**2)**0.5

            x_offsets[1:] = mags[1:]*np.cos(map_thetas - hit_thetas[1:])
            y_offsets[1:] = mags[1:]*np.sin(map_thetas - hit_thetas[1:])

            return x_offsets, y_offsets

        dt_notes, dt_hits = __get_hit_interval_offset()
        x_offsets, y_offsets = __get_position_offsets()

        return dt_notes, dt_hits, x_offsets, y_offsets, (hit_t - map_t)


    @staticmethod
    def get_data(score_data, timestamp, map_md5, mods, cs, ar):
        dt, dt_dec, dt_inc, ds, angles, dt_rhym = DataProcessing.get_difficulty_data(score_data, ar)
        dt_notes, dt_hits, x_offsets, y_offsets, t_offsets = DataProcessing.get_performance_data(score_data)
        hash_mask = 0xFFFFFFFFFFFF0000

        if not (
            dt.shape[0] == dt_dec.shape[0] == dt_inc.shape[0] == ds.shape[0] == angles.shape[0] == dt_rhym.shape[0] ==
            dt_notes.shape[0] == dt_hits.shape[0] == x_offsets.shape[0] == y_offsets.shape[0] == t_offsets.shape[0]
        ):
            print(
                'Data shapes do not match:',
                f'   DT: {dt.shape[0]} '
                f'   DT_DEC: {dt_dec.shape[0]} '
                f'   DT_INC: {dt_inc.shape[0]} '
                f'   DS: {ds.shape[0]} '
                f'   ANGLES: {angles.shape[0]} '
                f'   DT_RHYM: {dt_rhym.shape[0]} '
                f'   X_OFFSETS: {x_offsets.shape[0]} '
                f'   Y_OFFSETS: {y_offsets.shape[0]} '
                f'   T_OFFSETS: {t_offsets.shape[0]} '
                f'   DT_NOTES: {dt_notes.shape[0]} '
                f'   DT_HITS: {dt_hits.shape[0]} '
            )
            raise Exception('Data shapes do not match')

        timings = score_data['map_t'].values
        x_pos = score_data['map_x'].values
        y_pos = score_data['map_y'].values
        htypes = score_data['type'].values
        otypes = score_data['action'].values

        if not (dt.shape[0] == timings.shape[0] == htypes.shape[0] == otypes.shape[0] == x_pos.shape[0] == y_pos.shape[0]):
            print(
                'Data shapes do not match:',
                f'   DT: {dt.shape[0]} '
                f'   TIMINGS: {timings.shape[0]} '
                f'   X_POS: {x_pos.shape[0]} '
                f'   Y_POS: {y_pos.shape[0]} '
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
            x_pos,      # X_POS
            y_pos,      # Y_POS
            dt,         # DT        
            dt_dec,     # DT_DEC     
            dt_inc,     # DT_INC   
            ds,         # DS
            angles,     # ANGLE
            dt_rhym,    # DT_RHYM
            x_offsets,  # X_OFFSETS 
            y_offsets,  # Y_OFFSETS 
            t_offsets,  # T_OFFSETS
            dt_notes,   # DT_NOTES
            dt_hits     # DT_HITS
        ]
 