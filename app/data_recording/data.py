
class RecData():    
    TIMESTAMP = 0   # Timestamp of the play
    MAP_HASH  = 1   # Map's md5 hash
    MODS      = 2   # Mods used
    CS        = 3   # Map's CS
    AR        = 4   # Map's AR
    HIT_TYPE  = 5   # Hit type (0: HITP, 1: HITR, 2: AIMH, 3: MISS, 4: EMPTY)
    ACT_TYPE  = 6   # Action type (0: Press, 1: Hold, 2: Release)
    TIMINGS   = 7   # Timings of the hit
    DT        = 8  # Time between notes in the pattern (s)
    DT_DEC    = 9  # Time since last BPM decrease
    DT_INC    = 10  # Time since last BPM increase
    DS        = 11  # Distance between notes in the pattern (osu!px)
    ANGLE     = 12  # Angle between notes in the pattern (deg)
    X_OFFSETS = 13  # How far the pattern is from the center of the note along the x-axis
    Y_OFFSETS = 14  # How far the pattern is from the center of the note along the y-axis
    T_OFFSETS = 15  # How early/late the note was hit
    NUM_COLS  = 16
