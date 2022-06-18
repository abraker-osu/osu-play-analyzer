import threading

import pyqtgraph
from pyqtgraph import QtCore

import numpy as np

from app.misc.Logger import Logger
from app.file_managers import score_data_obj



class PlaysGraph(pyqtgraph.PlotWidget):

    logger = Logger.get_logger(__name__)

    region_changed = QtCore.pyqtSignal(list, object)

    __timestamps_load_done = QtCore.pyqtSignal(object)

    def __init__(self):
        self.logger.debug(f'__init__ enter')

        pyqtgraph.PlotWidget.__init__(self, plotItem=pyqtgraph.PlotItem())
        self.setMaximumHeight(64)

        #self.play_data = np.empty(shape=(0, ScoreNpyData.NUM_COLS))
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

        self.__timestamps_mutex = threading.Lock()
        self.__timestamps_load_done.connect(self.__plot_timestamps)

        self.logger.debug(f'__init__ exit')


    def plot_plays(self, map_md5_strs):
        if len(map_md5_strs) == 0:
            self.logger.debug(f'plot_plays - No data to plot')
            return

        if self.__timestamps_mutex.locked():
            self.logger.debug(f'plot_plays - __timestamps_mutex locked')
            return

        self.logger.debug(f'plot_plays - ')

        # Mutex required to ensure multiple calls don't attempt to access
        # an outdated `self.map_md5_strs`. This mutex is acquired with the
        # assumption all code paths end with `__plot_timestamps`, where
        # this mutex is then released.
        self.__timestamps_mutex.acquire()
        self.map_md5_strs = map_md5_strs

        # Thread gets list of timestamps
        thread = threading.Thread(target=self.__load_timestamps)
        thread.start()
            

    def __load_timestamps(self):
        
        def do_get_timestamps(map_md5_str):
            score_data = score_data_obj.data(map_md5_str)
            return np.asarray([ timestamp for timestamp, _ in score_data.groupby(level=0) ], dtype=np.uint64)

        hit_timestamps = map(do_get_timestamps, self.map_md5_strs)
        hit_timestamps = list(hit_timestamps)
        hit_timestamps = np.hstack(hit_timestamps)

        # Calls __plot_timestamps
        self.__timestamps_load_done.emit(hit_timestamps)


    def __plot_timestamps(self, hit_timestamps):
        # Calculate view
        xMin = min(hit_timestamps) - 1  # -1 minute
        xMax = max(hit_timestamps) + 1  # +1 minute

        view_center = 0.5*(xMin + xMax)    # Center of view (50% of max)
        half_range  = xMax - view_center   # Space between center of view and max

        self.logger.debug(f'plot_plays - xMin: {xMin} xMax: {xMax} view_center: {view_center} half_range: {half_range}')

        # Set plot data
        self.plot.setData(hit_timestamps, np.zeros(len(hit_timestamps)), pen=None, symbol='o', symbolPen=None, symbolSize=4, symbolBrush='y')
    
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

            # Calls __region_changed_event
            self.__region_plot.setBounds([left_center, right_center])
            self.__region_plot.setRegion([left_center, right_center])
        else:
            # Otherwise, still need to notify other components of the data change
            self.__region_changed_event()

        self.__timestamps_mutex.release()


    def __region_changed_event(self):
        self.logger.debug('__region_changed_event')
        self.region_changed.emit(self.map_md5_strs, self.get_selected())
    

    def get_selected(self):
        region = self.__region_plot.getRegion()
        timestamps = self.plot.getData()[0]

        select = ((region[0] < timestamps) & (timestamps < region[1]))
        return timestamps[select]
