import random
import math

from map_generator import MapGenerator
from file_managers import AppConfig


sm = 20
st = 8


MapGenerator.start(ar=8.0, cs=4.0, od=10.0, hp=10.0, sm=sm, st=st)
MapGenerator.set_meta(version=f'slider_rand', creator='map_architect')


slider_len = 50


# TODO: Sliders need to be spaced apart between 100 and 200 osu!px

for i in range(50):
    rand_x = random.randint(-20 + slider_len, 530 - slider_len)
    rand_y = random.randint(slider_len, 460 - slider_len)
    rand_a = random.randint(0, 360)

    x_start = rand_x
    x_end   = rand_x + slider_len*math.cos(rand_a*math.pi/180)

    y_start = rand_y
    y_end   = rand_y + slider_len*math.sin(rand_a*math.pi/180)

    MapGenerator.add_note([
        # dt  x        y        red anchor?
        [150, x_start, y_start, 0],
        [150, x_end,   y_end,   0],
    ])

# Generates the .osu data. `map` is the .osu file text.
map_data = MapGenerator.gen()

map_path = f'K:/Games/osu!/Songs/osu_play_analyzer'
MapGenerator.save(map_data, map_path, res_path='../')
