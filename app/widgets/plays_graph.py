import pyqtgraph
from pyqtgraph import QtCore

import numpy as np

from app.data_recording.data import RecData



class PlaysGraph(pyqtgraph.PlotWidget):

    region_changed = QtCore.pyqtSignal(object)

    def __init__(self):
        pyqtgraph.PlotWidget.__init__(self, plotItem=pyqtgraph.PlotItem())
        self.setMaximumHeight(64)

        self.play_data = np.empty(shape=(0, RecData.NUM_COLS))
        self.graph = self.getPlotItem()
        self.plot = self.graph.plot()

        self.graph.setAxisItems({ 'bottom' : pyqtgraph.DateAxisItem(orientation='bottom') })
        self.graph.getAxis('left').hide()
        self.graph.getAxis('bottom').enableAutoSIPrefix(False)
        self.graph.getViewBox().setMouseEnabled(y=False)
        self.setLimits(yMin=-200, yMax=200)

        # Interactive region item
        self.__region_plot = pyqtgraph.LinearRegionItem([0, 1], 'vertical', swapMode='block', pen='r')
        self.__region_plot.sigRegionChangeFinished.connect(self.__region_changed_event)
        self.addItem(self.__region_plot)


    def plot_plays(self, play_data):
        self.play_data = play_data
        if play_data.size == 0:
            return
            
        hit_timestamps = np.unique(play_data[:, RecData.TIMESTAMP]).astype(np.uint64)

        # Calculate view
        xMin = min(hit_timestamps) - 86400  # -1 day
        xMax = max(hit_timestamps) + 86400  # +1 day

        view_center = 0.5*(xMin + xMax)    # Center of view (50% of max)
        half_range  = xMax - view_center   # Space between center of view and max

        # Set plot data
        self.plot.setData(hit_timestamps, np.zeros(hit_timestamps.shape[0]), pen=None, symbol='o', symbolPen=None, symbolSize=4, symbolBrush='y')
    
        # Get current range
        xRange = self.graph.getViewBox().viewRange()[0]
        xRegion = self.__region_plot.getRegion()

        # If current view is not in range, set it
        if xMin < xRange[0] or xRange[1] < xMax:
            left_center  = view_center - 1.5*half_range
            right_center = view_center + 1.5*half_range

            self.setLimits(xMin=left_center, xMax=right_center)
            self.setRange(xRange=(left_center, right_center))

        # If current region is not in range, set it
        if xMin < xRegion[0] or xRegion[1] < xMax:
            left_center  = view_center - 1.1*half_range
            right_center = view_center + 1.1*half_range

            self.__region_plot.setBounds([left_center, right_center])
            self.__region_plot.setRegion([left_center, right_center])


    def __region_changed_event(self, region):
        region = region.getRegion()
        select = (region[0] <= self.play_data[:, RecData.TIMESTAMP]) & (self.play_data[:, RecData.TIMESTAMP] <= region[1])
        self.region_changed.emit(self.play_data[select])
    

    def get_selected(self):
        region = self.__region_plot.getRegion()

        select = (region[0] <= self.play_data[:, RecData.TIMESTAMP]) & (self.play_data[:, RecData.TIMESTAMP] <= region[1])
        return self.play_data[select]
