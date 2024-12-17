import random
import numpy as np
from map_generator import MapGenerator
from file_managers import AppConfig

NUM_NOTES = 48 # Total number of notes

BPM = 140
d_timing = 60000 / BPM
radius = 54.4 - 4.48 * 4
distance = radius * 8

min_x = radius
min_y = radius
max_x = 512 - min_x
max_y = 384 - min_y

for middle_note_percentage in np.arange(0.05, 0.95, 0.05):
    MapGenerator.start(ar=9.0, cs=4.0, od=10.0, hp=10.0, sm=1.0, st=1)
    MapGenerator.set_meta(version=f'{(middle_note_percentage * 100):.0f}%', creator=f'{BPM}_BPM')
    curr_x = max_x / 2
    curr_y = max_y / 2

    for j in range(NUM_NOTES):
        match j % 3:
            case 0:  # 1st note of the set
                timing = d_timing * middle_note_percentage
            case 1:  # Middle
                timing = d_timing * (1 - middle_note_percentage)
            case 2:  # Last
                timing = d_timing / 2

        MapGenerator.add_note([
            [timing, curr_x, curr_y, 0]
        ])

        angle = 2 * np.pi * random.random()
        change_x = distance * timing / d_timing * np.cos(angle)
        change_y = distance * timing / d_timing * np.sin(angle)
        while not (min_x <= curr_x + change_x <= max_x and min_y <= curr_y + change_y <= max_y):
            angle = 2 * np.pi * random.random()
            change_x = distance * timing / d_timing * np.cos(angle)
            change_y = distance * timing / d_timing * np.sin(angle)
        curr_x += change_x
        curr_y += change_y

    # Generate the .osu data and save the map
    map_data = MapGenerator.gen()
    map_path = f'{AppConfig.cfg["osu_dir"]}/Songs/osu_play_analyzer/'
    MapGenerator.save(map_data, map_path)

# Display generated map in Map Display > Generated
gen_map_event.emit(map_data)
