import multiprocessing
import threading

import pyqtgraph
from pyqtgraph import QtCore

import numpy as np

from misc.Logger import Logger


class PlaysGraph(pyqtgraph.PlotWidget):

    logger = Logger.get_logger(__name__)

    region_changed = QtCore.pyqtSignal(dict)

    def __init__(self):
        self.logger.debug(f'__init__ enter')

        pyqtgraph.PlotWidget.__init__(self, plotItem=pyqtgraph.PlotItem())
        self.setMaximumHeight(64)

        self.map_md5_strs = []
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

        self.logger.debug(f'__init__ exit')


    def plot_plays(self, timestamps):
        self.logger.debug(f'plot_plays - enter')

        self.plot.setData(timestamps, np.zeros(len(timestamps)), pen=None, symbol='o', symbolPen=None, symbolSize=4, symbolBrush='y')

        if len(timestamps) != 0:
            self.__reset_plot_range(timestamps)


    def __reset_plot_range(self, timestamps):
        # Calculate view
        xMin = min(timestamps) - 1  # -1 minute
        xMax = max(timestamps) + 1  # +1 minute

        view_center = 0.5*(xMin + xMax)    # Center of view (50% of max)
        half_range  = xMax - view_center   # Space between center of view and max

        self.logger.debug(f'plot_plays - xMin: {xMin} xMax: {xMax} view_center: {view_center} half_range: {half_range}')

        # Get current range
        xRange = self.graph.getViewBox().viewRange()[0]
        xRegion = self.__region_plot.getRegion()

        # If current view is not in range, set it
        if (xMin < xRange[0]) or (xRange[1] < xMax):
            left_center  = view_center - 1.5*half_range
            right_center = view_center + 1.5*half_range

            self.setLimits(xMin=left_center, xMax=right_center)
            self.setRange(xRange=(left_center, right_center))

        # If current region is not in range, set it
        if (xMin < xRegion[0]) or (xRegion[1] < xMax):
            left_center  = view_center - 1.1*half_range
            right_center = view_center + 1.1*half_range

            # Blocks the `sigRegionChangeFinished` signal
            self.__region_plot.blockSignals(True)
            self.__region_plot.setBounds([ left_center, right_center ])
            self.__region_plot.setRegion([ left_center, right_center ])
            self.__region_plot.blockSignals(False)


    def __region_changed_event(self, data):
        self.logger.debug('__region_changed_event')
        self.region_changed.emit({
            #'md5_strs'   : self.map_md5_strs,
            'timestamps' : self.get_selected()
        })


    def get_selected(self):
        region = self.__region_plot.getRegion()
        timestamps = self.plot.getData()[0]

        select = ((region[0] < timestamps) & (timestamps < region[1]))
        return timestamps[select]
