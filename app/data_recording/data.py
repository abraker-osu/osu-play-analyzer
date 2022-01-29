
class RecData():    
    TIMESTAMP = 0   # Timestamp of the play
    MAP_HASH  = 1   # Map's md5 hash
    MODS      = 2   # Mods used
    CS        = 3   # Map's CS
    AR        = 4   # Map's AR
    HIT_TYPE  = 5   # Hit type (0: HITP, 1: HITR, 2: AIMH, 3: MISS, 4: EMPTY)
    ACT_TYPE  = 6   # Action type (0: Press, 1: Hold, 2: Release)
    TIMINGS   = 7   # Timings of the hit
    X_POS     = 8   # X position of the scorepoint
    Y_POS     = 9   # Y position of the scorepoint
    DT        = 10  # Time between notes in the pattern (s)
    DT_DEC    = 11  # Time since last BPM decrease
    DT_INC    = 12  # Time since last BPM increase
    DS        = 13  # Distance between notes in the pattern (osu!px)
    ANGLE     = 14  # Angle between notes in the pattern (deg)
    DT_RHYM   = 15  # % the note is from previous note to next note (% of tn[2] - tn[0])
    X_OFFSETS = 16  # How far the pattern is from the center of the note along the x-axis
    Y_OFFSETS = 17  # How far the pattern is from the center of the note along the y-axis
    T_OFFSETS = 18  # How early/late the note was hit
    DT_NOTES  = 19  # Time between accross 3 notes in the pattern
    DT_HITS   = 20  # Time between hits across 3 notes in the pattern
    NUM_COLS  = 21
