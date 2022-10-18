import math

import numpy as np
import pandas as pd

from app.misc.Logger import Logger
from app.misc.osu_utils import OsuUtils

from osu_analysis import StdScoreData



class DiffNpy():

    logger = Logger.get_logger(__name__)

    @staticmethod
    def __process_t_press(score_data):
        """
        Calculates press related difficulty attributes
        diff_vec = [ 
            t_press_diff,  # Time difference between presses
            t_press_inc,   # Time since last increase between scorepoint press timing
            t_press_dec,   # Time since last decrease between scorepoint press timing
            t_press_rhm,   # Scorepoint press's relative spacing compared to other scorepoint presses
            t_hold_dur,    # Time duration of hold
        ]
        """
        map_t = score_data['T_MAP'].values

        prs_select = (score_data['TYPE_MAP'] == StdScoreData.ACTION_PRESS)
        rel_select = (score_data['TYPE_MAP'] == StdScoreData.ACTION_RELEASE)
        hld_select = (score_data['TYPE_MAP'] == StdScoreData.ACTION_HOLD)

        map_t_prs_select = prs_select
        map_t_rel_select = rel_select

        # TODO: Figure out how to relate presses to releases associated with holds
        #map_t_hld_select = np.zeros(map_t.shape[0], dtype=np.bool)
        #map_t_hld_select[1:] = (prs_select[:-1] & rel_select[1:]) | (hld_select[:-1] & rel_select[1:])

        map_t_prs_idx_ref = np.arange(map_t_prs_select.shape[0])[map_t_prs_select]
        #map_t_hld_idx_ref = np.arange(map_t_hld_select.shape[0])[map_t_hld_select]

        def __get_t_press_mask():
            t_press_mask = np.zeros(score_data.shape[0])
            t_press_mask[map_t_prs_select] = 1

            return t_press_mask

        def __get_t_press_diff():
            """
            Gets the difference between each scorepoint press timing
            Invalid entries are set to int32.max

            Valid range: [0, int32.max - 1]

            Invalid scorepoints:
                - Scorepoint indices: [0]
                - Scorepoints that are not a press type
                  Use t_press_mask to filter out invalid entries
            """
            t_press_diff = np.full(score_data.shape[0], np.nan)
            
            # Not enough scorepoint presses
            if map_t_prs_idx_ref.shape[0] < 2:
                return t_press_diff

            map_t_prs = map_t[map_t_prs_select]
            t_press_diff[map_t_prs_idx_ref[1:]] = map_t_prs[1:] - map_t_prs[:-1]
            return t_press_diff

        def __get_t_press_rate():
            """
            Gets the difference across 3 scorepoint press timings
            Invalid entries are set to int32.max

            Valid range: [0, int32.max - 1]

            Invalid scorepoints:
                - Scorepoint indices: [0, 1]
                - Scorepoints that are not a press type
                  Use t_press_mask to filter out invalid entries
            """
            t_press_diff = np.full(score_data.shape[0], np.nan)
            
            # Not enough scorepoint presses
            if map_t_prs_idx_ref.shape[0] < 3:
                return t_press_diff

            map_t_prs = map_t[map_t_prs_select]
            t_press_diff[map_t_prs_idx_ref[2:]] = map_t_prs[2:] - map_t_prs[:-2]
            return t_press_diff

        def __get_t_press_inc():
            """
            Get the time since last increase in scorepoint press timing
            Invalid entries are set to int32.max

            A scorepoint is valid if:
                - Scorepoint indices: [0, 1]
                - Scorepoints that are not a press type
                  Use t_press_mask to filter out invalid entries
            """
            t_press_inc = np.full(score_data.shape[0], np.nan)     

            # Not enough scorepoint presses
            if map_t_prs_idx_ref.shape[0] < 3:
                return t_press_inc

            map_t_prs = map_t[map_t_prs_select]

            dt0 = map_t_prs[1:-1] - map_t_prs[:-2]   # t1 - t0
            dt1 = map_t_prs[2:] - map_t_prs[1:-1]    # t2 - t1

            # The first interval increase comes as soon as note t2 is further than expected
            # This makes the time since last increase for first and second notes ALWAYS 0
            t_press_inc[map_t_prs_idx_ref[0:2]] = 0

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

                t_press_inc[map_t_prs_idx_ref[i + 2]] = ms

            return t_press_inc

        def __get_t_press_dec():
            """
            Get the time since last decrease in scorepoint press timing
            Invalid entries are set to int32.max

            A scorepoint is valid if:
                - Scorepoint indices: [0, 1]
                - Scorepoints that are not a press type
                  Use t_press_mask to filter out invalid entries
            """
            t_press_dec = np.full(score_data.shape[0], np.nan)     

            # Not enough scorepoint presses
            if map_t_prs_idx_ref.shape[0] < 3:
                return t_press_dec

            map_t_prs = map_t[map_t_prs_select]

            dt0 = map_t_prs[1:-1] - map_t_prs[:-2]   # t1 - t0
            dt1 = map_t_prs[2:] - map_t_prs[1:-1]    # t2 - t1

            # The first interval decrease comes from lack of notes before the start of the map. 
            # The time since last decrease for first note is ALWAYS 0
            # The time since last decrease for the second note is ALWAYS the time between the first and second notes
            t_press_dec[map_t_prs_idx_ref[0]] = 0
            t_press_dec[map_t_prs_idx_ref[1]] = dt0[0]

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

                t_press_dec[map_t_prs_idx_ref[i + 2]] = ms

            return t_press_dec

        def __get_t_press_rhm():
            # TODO: See https://discord.com/channels/546120878908506119/886986744090734682/935701345451786290
            # https://cdn.discordapp.com/attachments/886986744090734682/935701344721961010/unknown.png
            #
            # somewhere between 0.25 and 0.5, 0.5 and 0.75 would be considered irregular snaps, therefore higher rhythmic complexity 
            # for slightly off from 50%, I expect offsets equal to (t2 - t0)/2 - (t2 - t0)*percent 
            """
            Scorepoint press's relative spacing compared to other scorepoint presses x ϵ (0, 1)
            Invalid entries are set to int32.max

            A scorepoint is valid if:
                - Scorepoint indices: [0, 1]
                - Scorepoints that are not a press type
                  Use t_press_mask to filter out invalid entries
            """
            t_press_rhm = np.full(score_data.shape[0], np.nan)     

            # Not enough scorepoint presses
            if map_t_prs_idx_ref.shape[0] < 3:
                return t_press_rhm

            map_t_prs = map_t[map_t_prs_select]

            part  = map_t_prs[1:] - map_t_prs[:-1]  # t1 - t0
            total = map_t_prs[2:] - map_t_prs[:-2]  # t2 - t0

            # x = (t1 - t0)/(t2 - t0])
            t_press_rhm[map_t_prs_idx_ref[2:]] = 100*part[:-1]/total
            return t_press_rhm

        def __get_t_hold_dur():
            """
            Gets the duration between press and release scorepoints
            Invalid entries are set to int32.max

            A scorepoint is valid if:
                - Scorepoint indices: [0]
                - Scorepoints that are ???
            """
            t_hold_dur = np.full(score_data.shape[0], np.nan) 
            
            # TODO: Figure this out
            return t_hold_dur
            
            # Not enough scorepoint presses
            if map_t_hld_idx_ref.shape[0] <= 0:
                return t_hold_dur

            map_t_prs_hld = map_t[map_t_prs_select & map_t_hld_select]
            map_t_rel_hld = map_t[map_t_rel_select & map_t_hld_select]

            # +1 to set it for release scorepoint instead of press
            t_hold_dur[map_t_hld_idx_ref + 1] = map_t_rel_hld - map_t_prs_hld
            return t_hold_dur

        t_press_mask = __get_t_press_mask()
        t_press_diff = __get_t_press_diff()
        t_press_rate = __get_t_press_rate()
        t_press_inc  = __get_t_press_inc()
        t_press_dec  = __get_t_press_dec()
        t_press_rhm  = __get_t_press_rhm()
        t_hold_dur   = __get_t_hold_dur()

        return t_press_mask, t_press_diff, t_press_rate, t_press_inc, t_press_dec, t_press_rhm, t_hold_dur


    @staticmethod
    def __process_xy(score_data):
        """
        Calculates aim related difficulty attributes
        diff_vec = [ 
            xy_dist,       # Distance between every scorepoint
            xy_angle,      # Angle between every scorepoint
            xy_lin_vel,    # Linear velocity between every scorepoint
            xy_ang_vel,    # Angular velocity between every scorepoint
        ]
        """
        map_t = score_data['T_MAP'].values
        map_x = score_data['X_MAP'].values
        map_y = score_data['Y_MAP'].values

        prs_select = (score_data['TYPE_MAP'] == StdScoreData.ACTION_PRESS)
        hld_select = (score_data['TYPE_MAP'] == StdScoreData.ACTION_HOLD)

        aim_select = prs_select | hld_select
        map_aim_ref = np.arange(score_data.shape[0])[aim_select]

        map_len = score_data.shape[0]

        def __get_xy_dist():
            """
            Gets the spacing between each aimpoint
            Invalid entries are set to int32.max

            A scorepoint is valid if:
                - Scorepoint indices: [0]
            """
            xy_dist = np.full(map_len, np.nan) 

            # Not enough scorepoints
            if map_len < 2:
                return xy_dist

            dx = map_x[1:] - map_x[:-1]  # x1 - x0
            dy = map_y[1:] - map_y[:-1]  # y1 - y0
            
            # Cursor is assumed to start on first note, so distance from prev point is 0
            # xy_dist[0] = 0 (implicit)
            xy_dist[1:] = (dx**2 + dy**2)**0.5

            return xy_dist

        def __get_xy_angle():
            """
            Gets the angle between each scorepoint in deg
            Invalid entries are set to int32.max

            A scorepoint is valid if:
                - Scorepoint indices: [0, -1]
                    (requires a point present before and after to calc angle of current point)

            TODO: Ignore overlaps because https://i.imgur.com/Iwuajar.gif
            """
            xy_angle = np.full(map_len, np.nan) 

            # Not enough scorepoints
            if map_len < 3:
                return xy_angle

            dx0 = map_x[1:-1] - map_x[:-2]   # x1 - x0
            dx1 = map_x[2:] - map_x[1:-1]    # x2 - x1

            dy0 = map_y[1:-1] - map_y[:-2]   # y1 - y0
            dy1 = map_y[2:] - map_y[1:-1]    # y2 - y1
            
            theta_d0 = np.arctan2(dy0, dx0)*(180/math.pi)
            theta_d1 = np.arctan2(dy1, dx1)*(180/math.pi)

            thetas = np.abs(theta_d1 - theta_d0)
            thetas[thetas > 180] = 360 - thetas[thetas > 180]
            thetas = np.round(thetas)
            
            # xy_angle[0] = np.nan (implicit)
            xy_angle[1:-1] = thetas
            # xy_angle[-1] = np.nan (implicit)

            return xy_angle

        def __get_xy_lin_vel():
            """
            Gets the linear velocity between each aimpoint
            Invalid entries are set to int32.max

            A scorepoint is valid if:
                - Scorepoint indices: [0]
            """
            xy_lin_vel = np.full(map_len, np.nan) 

            # Not enough scorepoints
            if map_len < 2:
                return xy_lin_vel

            dx = map_x[1:] - map_x[:-1]  # x1 - x0
            dy = map_y[1:] - map_y[:-1]  # y1 - y0
            vels = (dx**2 + dy**2)**0.5

            # xy_lin_vel[0] = 0 (implicit)
            xy_lin_vel[1:] = vels / (map_t[1:] - map_t[:-1])

            return xy_lin_vel

        def __get_xy_ang_vel():
            """
            Gets the angular velocity between each aimpoint in RPM
            Invalid entries are set to int32.max

            A scorepoint is valid if:
                - Scorepoint indices: [0]
            """
            xy_ang_vel = np.full(map_len, np.nan) 

            # Not enough scorepoints
            if map_len < 3:
                return xy_ang_vel

            dx0 = map_x[1:-1] - map_x[:-2]   # x1 - x0
            dx1 = map_x[2:] - map_x[1:-1]    # x2 - x1

            dy0 = map_y[1:-1] - map_y[:-2]   # y1 - y0
            dy1 = map_y[2:] - map_y[1:-1]    # y2 - y1
            
            theta_d0 = np.arctan2(dy0, dx0)*(180/math.pi)
            theta_d1 = np.arctan2(dy1, dx1)*(180/math.pi)

            thetas = np.abs(theta_d1 - theta_d0)
            thetas[thetas > 180] = 360 - thetas[thetas > 180]
            thetas = np.round(thetas)
            
            # xy_ang_vel[0] = 0 (implicit)
            # xy_ang_vel[1] = 0 (implicit)
            xy_ang_vel[2:] = 60000/360*thetas/(map_t[2:] - map_t[:-2])  # (deg/ms)*(1000 ms/s)*(60 s/min)*(1 rot/360 deg)
            
            return xy_ang_vel

        xy_dist    = __get_xy_dist()
        xy_angle   = __get_xy_angle()
        xy_lin_vel = __get_xy_lin_vel()
        xy_ang_vel = __get_xy_ang_vel()

        return xy_dist, xy_angle, xy_lin_vel, xy_ang_vel


    @staticmethod
    def __process_visual(score_data):
        # TODO: Figure out how I want to do this. Number of notes present is
        #       not representative of visual difficulty due to sliders. Perhaps
        #       total hitobject area is a better metric? Will need to be normalized
        #       to CS.
        #
        #       See https://discord.com/channels/546120878908506119/886986744090734682/928768553899925535
        #       for brief idea regarding area and overlap metrics.
        """
        Calculates reading related difficulty attributes
        diff_vec = [ 
            vis_visible,    # Number of notes visible
        ]
        """
        map_t = score_data['T_MAP'].values
        map_x = score_data['X_MAP'].values
        map_y = score_data['Y_MAP'].values

        ar_ms = OsuUtils.ar_to_ms(score_data['AR'].values[0])

        prs_select = (score_data['TYPE_MAP'] == StdScoreData.ACTION_PRESS)
        rel_select = (score_data['TYPE_MAP'] == StdScoreData.ACTION_RELEASE)
        
        map_t_prs_select = prs_select
        map_t_rel_select = rel_select
        map_t_hld_select = prs_select[:-1] & rel_select[1:]

        map_t_prs_idx_ref = np.arange(map_t_prs_select.shape[0])[map_t_prs_select]
        map_t_hld_idx_ref = np.arange(map_t_hld_select.shape[0])[map_t_hld_select]

        def __get_vis_visible():
            """
            Gets the number of notes visible
            Invalid entries are set to int32.max

            A scorepoint is valid if:
                - Scorepoints that are not a press type
                  Use t_press_mask to filter out invalid entries
            """
            vis_visible = np.full(score_data.shape[0], np.nan) 
            map_t_prs = map_t[map_t_prs_select]

            for i in range(map_t_prs_idx_ref.shape[0]):
                # TODO: Right hand side should really be release time
                ar_select = (map_t_prs[i] <= map_t_prs) & (map_t_prs <= (map_t_prs[i] + ar_ms))
                #print(f'{i}: {map_t_prs[i]} <= map_t_prs & map_t_prs <= {map_t_prs[i] + ar_ms}')
                vis_visible[map_t_prs_idx_ref[i]] = np.count_nonzero(ar_select)

            return vis_visible

        vis_visible = __get_vis_visible()

        return vis_visible


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
    def get_data(score_data):
        t_press_mask, \
        t_press_diff, \
        t_press_rate, \
        t_press_inc,  \
        t_press_dec,  \
        t_press_rhm,  \
        t_hold_dur    \
            = DiffNpy.__process_t_press(score_data)

        xy_dist,      \
        xy_angle,     \
        xy_lin_vel,   \
        xy_ang_vel    \
            = DiffNpy.__process_xy(score_data)

        vis_visible   \
            = DiffNpy.__process_visual(score_data)

        # NOTE: Must start with "DIFF_" so that difficulty specific
        # columns can be recognized and recalculated upon request
        df = pd.DataFrame()
        df['MD5']               = score_data.index.get_level_values(0)
        df['TIMESTAMP']         = score_data.index.get_level_values(1)
        df['MODS']              = score_data.index.get_level_values(2)
        df['IDXS']              = score_data.index.get_level_values(3)
        df['DIFF_T_PRESS_DIFF'] = t_press_diff
        df['DIFF_T_PRESS_RATE'] = t_press_rate
        df['DIFF_T_PRESS_INC']  = t_press_inc
        df['DIFF_T_PRESS_DEC']  = t_press_dec
        df['DIFF_T_PRESS_RHM']  = t_press_rhm
        df['DIFF_T_HOLD_DUR']   = t_hold_dur
        df['DIFF_XY_DIST']      = xy_dist
        df['DIFF_XY_ANGLE']     = xy_angle
        df['DIFF_XY_LIN_VEL']   = xy_lin_vel
        df['DIFF_XY_ANG_VEL']   = xy_ang_vel
        df['DIFF_VIS_VISIBLE']  = vis_visible

        df.set_index(['MD5', 'TIMESTAMP', 'MODS', 'IDXS'], inplace=True)
        return df


    @staticmethod
    def get_blank_data():
        df = pd.DataFrame(columns=[
            'MD5', 'TIMESTAMP', 'MODS', 'IDXS', 
            'DIFF_T_PRESS_DIFF', 'DIFF_T_PRESS_RATE', 'DIFF_T_PRESS_INC', 'DIFF_T_PRESS_DEC', 'DIFF_T_PRESS_RHM', 'DIFF_T_HOLD_DUR', 
            'DIFF_XY_DIST', 'DIFF_XY_ANGLE', 'DIFF_XY_LIN_VEL', 'DIFF_XY_ANG_VEL', 
            'DIFF_VIS_VISIBLE'
        ])

        df.set_index(['MD5', 'TIMESTAMP', 'MODS', 'IDXS'], inplace=True)
        return df
