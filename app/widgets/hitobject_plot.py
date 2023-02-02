import pyqtgraph
import numpy as np
from pyqtgraph import QtCore, QtGui

from osu_analysis import StdMapData


class HitobjectPlot(pyqtgraph.GraphItem):

    HITOBJECT_RADIUS = 30

    def __init__(self):
        pyqtgraph.GraphItem.__init__(self)
        pyqtgraph.setConfigOptions(antialias=True)

        self.pen = pyqtgraph.mkPen(width=HitobjectPlot.HITOBJECT_RADIUS)
        self.pen.setCapStyle(QtCore.Qt.RoundCap)
        self.setPen(self.pen)
    

    def set_map_timeline(self, map_data, y_pos=0):
        self.scatter.clear()
        
        press_select = map_data['type'] == StdMapData.TYPE_PRESS
        release_select = map_data['type'] == StdMapData.TYPE_RELEASE

        start_times = map_data[press_select]['time']
        end_times   = map_data[release_select]['time']
        h_types     = map_data[press_select]['object']

        pos  = []
        adj  = []
        size = []

        obj_num = -1

        for start_time, end_time, h_type in zip(start_times, end_times, h_types):
            pos.append([ start_time, y_pos ])
            size.append(HitobjectPlot.HITOBJECT_RADIUS)
            obj_num += 1

            # Slider end
            if h_type == StdMapData.TYPE_SLIDER:
                pos.append([ end_time, y_pos ])
                size.append(0)
                obj_num += 1

                adj.append([ obj_num - 1, obj_num ])
            else:
                adj.append([ obj_num, obj_num ])

        pos = np.asarray(pos, dtype=np.float32)
        adj = np.asarray(adj, dtype=np.int32)

        self.setData(pos=pos, adj=adj, size=size, symbol='o', pxMode=True)


    def set_map_display(self, t, map_data, ar_ms, cs_px):
        # Reset drawn with empty data (sliders don't disappear otherwise)
        pos = np.zeros((0, 2), dtype=np.float32)
        adj = np.zeros((0, ), dtype=np.int32)
        self.setData(pos=pos, adj=adj, size=[], symbol='o', pxMode=False)
        
        # Select hitobjects within AR range of currently viewed timing
        ar_select = (t <= map_data['time']) & (map_data['time'] <= (t + ar_ms))
        hitobject_idxs = map_data[ar_select].index.get_level_values(0).drop_duplicates()
        points = map_data.loc[hitobject_idxs]

        num_points = len(points)
        if num_points == 0:
            return

        release_select = points['type'].values == StdMapData.TYPE_RELEASE
        press_select = points['type'].values == StdMapData.TYPE_PRESS

        pos = np.zeros((num_points, 2), dtype=np.float32)
        pos[:, 0] = points['x'].values
        pos[:, 1] = points['y'].values

        adj = np.zeros((num_points, 2), dtype=np.int32)
        adj[:, 0] = np.arange(num_points)
        adj[:, 1] = adj[:, 0] + 1
        adj[release_select, 1] = adj[release_select, 0]

        size = np.zeros((num_points, ), dtype=np.float32)
        size[press_select] = cs_px

        self.pen.setWidth(cs_px)
        self.setData(pos=pos, adj=adj, size=size, symbol='o', pxMode=False)
