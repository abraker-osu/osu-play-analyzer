import random
import math
import numpy as np

from map_generator import MapGenerator
from file_managers import AppConfig


MAX_DIST = 200.0
DT       = 220
#AR      = 9.2

prev_x = None
prev_y = None


for d_timing in [ 170, 200, 230, 260 ]:
    for i, ar in enumerate(np.arange(0, 10, 0.25)):
        MapGenerator.start(ar=ar, cs=4.0, od=10.0, hp=10.0, sm=1.0, st=1)
        MapGenerator.set_meta(version=f'{i}_{ar:.2f}_{d_timing}', creator=f't_{d_timing}')

        for i in range(50):
            while True:
                curr_x = 500*random.random()
                curr_y = 400*random.random()

                is_prev_x = not isinstance(prev_x, type(None))
                is_prev_y = not isinstance(prev_y, type(None))

                if is_prev_x and is_prev_y:
                    dist = ((curr_x - prev_x)**2 + (curr_y - prev_y)**2)**0.5
                    if dist > MAX_DIST:
                        continue
                break

            prev_x = curr_x
            prev_y = curr_y

            MapGenerator.add_note([
                [ random.choice([ d_timing ]), curr_x, curr_y, 0 ]
            ])


        # Generates the .osu data. `map` is the .osu file text.
        map_data = MapGenerator.gen()

        map_path = f'{AppConfig.cfg["osu_dir"]}/Songs/osu_play_analyzer/'
        MapGenerator.save(map_data, map_path)


# Done to display generated map in Map Display > Generated
gen_map_event.emit(map_data)
