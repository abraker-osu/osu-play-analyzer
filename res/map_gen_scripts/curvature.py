import random
import math
import os

from map_generator import MapGenerator
from file_managers import AppConfig



PLAYFIELD_W = 384
PLAYFIELD_H = 480

center_x = PLAYFIELD_W / 2 + 100
center_y = PLAYFIELD_H / 2 - 50

TARGET_VELOCITY = 100
TIME_DELTA = 0.2  # seconds
AMPLITUDE = 150


MapGenerator.start(ar=8.0, cs=4.0, od=10.0, hp=10.0, sm=1.0, st=1)
MapGenerator.set_meta(version=f'loop_{TARGET_VELOCITY}', creator='unknown')


# Generate a loop on path
def get_xy(i, m):
     x  = center_x + m*(math.sin(i) * math.sin(3*i))
     y  = center_y + m*(math.sin(i) * math.cos(3*i))

     return x, y


# Disance calc helper function
def dist(x0, y0, x1, y1):
     return math.sqrt((x1 - x0)**2 + (y1 - y0)**2)



x0, y0 = get_xy(0, AMPLITUDE)
MapGenerator.add_note([
   [ TIME_DELTA*1000, x0, y0, 0 ]
])

di = 0

for i in range(200):
    # Solve for constant velocity
    while True:
        x1, y1 = get_xy(di*TIME_DELTA, AMPLITUDE)
        vel = dist(x0, y0, x1, y1) / TIME_DELTA

        if vel > TARGET_VELOCITY:
            break

        di += 0.01

    print(f'vel: {vel:.2f}')

    MapGenerator.add_note([
        [ TIME_DELTA*1000, x1, y1, 0 ]
    ])

    x0 = x1
    y0 = y1


map_data = MapGenerator.gen()
map_path = f'{AppConfig.cfg["osu_dir"]}/Songs/osu_play_analyzer/'
MapGenerator.save(map_data, map_path)

# Done to display generated map in Map Display > Generated
gen_map_event.emit(map_data)
