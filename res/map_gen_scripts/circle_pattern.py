import random
import math

from map_generator import MapGenerator


MapGenerator.start(ar=8.0, cs=4.0, od=10.0, hp=10.0, sm=1.0, st=1)
MapGenerator.set_meta(version='test', creator='unknown')


for i in range(50):
     MapGenerator.add_note([
         [random.choice([250, 500]), 200 + 100*math.cos(i), 200 + 100*math.sin(i), 0]
     ])

# Add a slider. Only first and last timings matter.
# The rest are there for sake of data format consistency.
MapGenerator.add_note([
     # dt  x   y    red anchor?
     [50, 100, 100, 0],
     [50, 500, 130, 0],
     [50, 500, 200, 1],
     [50, 100, 200, 0],
     [50, 500, 300, 0],
])

map_data = MapGenerator.gen()

# Done to display generated map in Map Display > Generated
gen_map_event.emit(map_data)

