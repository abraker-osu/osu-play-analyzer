import pyqtgraph
from pyqtgraph import QtGui, QtCore

import numpy as np
import pandas as pd

from osu_analysis import StdScoreData

from app.misc.Logger import Logger
from app.data_recording.data import DiffNpyData, ScoreNpyData
from app.file_managers import MapsDB, score_data_obj


class CompositionViewer(QtGui.QWidget):

    logger = Logger.get_logger(__name__)
    region_changed = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        # Displayed xy scatter plot data
        self.xy_data = np.zeros((0, 2))

        # Stored data is already filtered by map, mod, and time of play
        # It is used to select the data to display in the scatter plot
        self.score_data = np.empty((0, ScoreNpyData.NUM_COLS))
        self.diff_data = np.empty((0, DiffNpyData.NUM_COLS))

        self.main_layout = QtGui.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.plot_widget = pyqtgraph.PlotWidget(plotItem=pyqtgraph.PlotItem())
        self.grid_plot_item = pyqtgraph.GridItem()
        self.data_plot = pyqtgraph.ScatterPlotItem(
            size        = 2,
            pen         = pyqtgraph.mkPen(None),
            brush       = pyqtgraph.mkBrush(255, 0, 0, 150),
            hoverable   = True,
            symbol      ='o',
            hoverSymbol ='o',
            hoverSize   = 10,
            hoverPen    = pyqtgraph.mkPen((0, 255, 0, 255), width=0.5),
            hoverBrush  = pyqtgraph.mkBrush(255, 0, 0, 150),
        )

        self.plot_widget.hideAxis('left')
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.addItem(self.grid_plot_item)
        self.plot_widget.addItem(self.data_plot)

        self.data_type_selection = QtGui.QListWidget()
        self.data_type_selection.setSelectionMode(QtGui.QAbstractItemView.NoSelection)

        self.num_data_points_label = QtGui.QLabel('Num data points selected: 0')
        self.reset_roi_selections_button = QtGui.QPushButton('Reset selections')
        self.reset_roi_selections_button.setToolTip('Resets selections to select all data')

        self.x_axis_selection = QtGui.QButtonGroup()
        self.x_axis_selection.setExclusive(True)

        self.y_axis_selection = QtGui.QButtonGroup()
        self.y_axis_selection.setExclusive(True)

        # MUST BE CONTIGUOUS
        self.__ID_CS           = 0   # CS of map
        self.__ID_AR           = 1   # AR of map
        self.__ID_T_PRESS_DIFF = 2   # Time of press difference
        self.__ID_T_PRESS_RATE = 3   # Time of press difference across 3 notes
        self.__ID_T_BPM        = 4   # BPM of map
        self.__ID_T_PRESS_INC  = 5   # Time since last increase between scorepoint press timing
        self.__ID_T_PRESS_DEC  = 6   # Time since last decrease between scorepoint press timing
        self.__ID_T_PRESS_RHM  = 7   # Scorepoint press's relative spacing compared to other scorepoint presses
        self.__ID_T_HOLD_DUR   = 8   # Time duration of hold
        self.__ID_XY_DIST      = 9   # Distance between every scorepoint
        self.__ID_XY_ANGLE     = 10   # Angle between every scorepoint
        self.__ID_XY_LIN_VEL   = 11  # Linear velocity between every scorepoint
        self.__ID_XY_ANG_VEL   = 12  # Angular velocity between every scorepoint
        self.__ID_VIS_VISIBLE  = 13  # Number of notes visible
        self.__NUM_IDS         = 14

        self.__id_x = None
        self.__id_y = None

        selections = {
            'CS':           self.__ID_CS,
            'AR':           self.__ID_AR,
            'T_PRESS_DIFF': self.__ID_T_PRESS_DIFF,
            'T_PRESS_RATE': self.__ID_T_PRESS_RATE,
            'T_PRESS_BPM':  self.__ID_T_BPM,
            'T_PRESS_INC':  self.__ID_T_PRESS_INC,
            'T_PRESS_DEC':  self.__ID_T_PRESS_DEC,
            'T_PRESS_RHM':  self.__ID_T_PRESS_RHM,
            'T_HOLD_DUR':   self.__ID_T_HOLD_DUR,
            'XY_DIST':      self.__ID_XY_DIST,
            'XY_ANGLE':     self.__ID_XY_ANGLE,
            'XY_LIN_VEL':   self.__ID_XY_LIN_VEL,
            'XY_ANG_VEL':   self.__ID_XY_ANG_VEL,
            'VIS_VISIBLE':  self.__ID_VIS_VISIBLE,
        }
        self.num_selections = len(selections)

        self.roi_selections = {}
        for id_y in range(self.num_selections):
            for id_x in range(self.num_selections):
                if id_x == id_y:
                    continue

                roi_id = self.__get_roi_id(id_x, id_y)
                self.roi_selections[roi_id] = {
                    'roi' : pyqtgraph.PolyLineROI(
                        [[0, 0], [0, 100], [100, 100], [100, 0]], 
                        pen=pyqtgraph.mkPen((0, 255, 0, 255), width=0.5), 
                        closed=True
                    ),
                    'select' : np.empty(0, dtype=np.bool),
                }

                self.roi_selections[roi_id]['roi'].sigRegionChanged.connect(lambda _: self.__roi_selection_event(emit_data=False))
                self.roi_selections[roi_id]['roi'].sigRegionChangeFinished.connect(lambda _: self.__roi_selection_event(emit_data=True))

        self.data_type_selection.addItem('x-axis                                 y-axis')

        for select_text, select_id in selections.items():
            widget = QtGui.QWidget()
            layout = QtGui.QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)

            x_axis_radio = QtGui.QRadioButton(select_text)
            y_axis_radio = QtGui.QRadioButton(select_text)

            self.x_axis_selection.addButton(x_axis_radio, id=select_id)
            self.y_axis_selection.addButton(y_axis_radio, id=select_id)

            layout.addWidget(x_axis_radio)
            layout.addWidget(y_axis_radio)

            widget_item = QtGui.QListWidgetItem()
            widget_item.setSizeHint(widget.sizeHint())    

            self.data_type_selection.addItem(widget_item)
            self.data_type_selection.setItemWidget(widget_item, widget)

        self.right_side_layout = QtGui.QVBoxLayout()
        self.right_side_layout.setContentsMargins(0, 0, 0, 0)
        self.right_side_layout.addWidget(self.data_type_selection)
        self.right_side_layout.addWidget(self.num_data_points_label)
        self.right_side_layout.addWidget(self.reset_roi_selections_button)

        self.main_layout.addWidget(self.plot_widget)
        self.main_layout.addLayout(self.right_side_layout)

        self.reset_roi_selections_button.clicked.connect(self.reset_roi_selections)

        self.x_axis_selection.idPressed.connect(self.__x_axis_selection_event)
        self.y_axis_selection.idPressed.connect(self.__y_axis_selection_event)

        self.x_axis_selection.button(self.__ID_CS).setChecked(True)
        self.y_axis_selection.button(self.__ID_AR).setChecked(True)
        self.__set_composition_data(id_x=self.__ID_CS, id_y=self.__ID_AR)
        

    def set_composition_from_score_data(self, map_md5_strs, timestamps):
        '''
        Called whenever different maps or time of plays are selected in
        the overview window. Updates the play data used to display the composition,
        and then proceeds to update everything else.

        At this point the supplied `score_data` is already filtered by map, mod, and time of play
        '''
        self.logger.debug('set_composition_from_score_data')

        if len(map_md5_strs) == 0:
            return

        if len(timestamps) == 0:
            return

        score_datas = [ score_data_obj.data(map_md5_str) for map_md5_str in map_md5_strs ]
        score_data = pd.concat(score_datas)
        score_data = score_data.loc[timestamps]

        # Save filtered score data for play_data compilation when ROI selections are made
        self.score_data = score_data
        self.update_diff_data()


    def update_diff_data(self):
        '''
        Called when there is a new score data selection or diff data gets recalculated
        '''
        self.logger.debug('update_diff_data')

        if self.score_data.shape[0] == 0:
            return

        # Get filtered diff data based on score data
        #self.diff_data = DiffNpyData.get_data_score(diff_data_obj.data, self.score_data)

        self.xy_data = np.zeros((self.score_data.shape[0], 2))
        self.__set_composition_data(id_x=self.__id_x, id_y=self.__id_y, force_update=True)

        # Update all selection masks
        xy_data = np.zeros((self.score_data.shape[0], 2))

        for id_y in range(self.num_selections):
            for id_x in range(self.num_selections):
                if id_y == id_x:
                    continue
                
                xy_data[:, 0] = self.__id_to_data(id_x)
                xy_data[:, 1] = self.__id_to_data(id_y)

                roi_id = self.__get_roi_id(id_x, id_y)
                self.__update_roi_selection(roi_id, xy_data)

        if self.score_data.shape[0] < 10000:
            self.__process_master_selection(emit_data=True)


    def get_selected(self):
        '''
        Composes the selections in all planes together, and returns the resulting selected play data.
        '''
        if type(self.score_data) == type(None):
            return

        # Calculate master selection across all multidimensional planes
        select = np.ones((self.score_data.shape[0]), dtype=np.bool)
        for roi_selection in self.roi_selections.values():
            select &= roi_selection['select']

        #play_data_out = np.zeros((np.count_nonzero(select), self.score_data.shape[1] + self.diff_data.shape[1]), dtype=np.int64)
        #play_data_out[:, :self.score_data.shape[1]] = self.score_data[select]
        #play_data_out[:, self.score_data.shape[1]:] = self.diff_data[select]

        # From https://github.com/ppy/osu/blob/master/osu.Game.Rulesets.Osu/Objects/OsuHitObject.cs#L137
        #play_data_out[:, PlayNpyData.CS] = (108.8 - 8.96*play_data_out[:, PlayNpyData.CS])/2
        #play_data_out[:, PlayNpyData.AR] /= 100

        self.num_data_points_label.setText(f'Num data points selected: {np.count_nonzero(select)}')
        return self.score_data[select]


    def __get_roi_id(self, id_x, id_y):
        '''
        Used to generate a unique ID for a given pair of axes.
        '''
        return id_y*self.num_selections + id_x


    def __update_roi_selection(self, roi_id, xy_data):
        '''
        Updates the cached selection mask
        '''
        if type(xy_data) == type(None):
            return

        roi_plot = self.roi_selections[roi_id]['roi']
        inv_filter = ~(np.isnan(xy_data).any(axis=1))
        
        self.roi_selections[roi_id]['select'] = np.zeros((xy_data.shape[0]), dtype=np.bool)
        self.roi_selections[roi_id]['select'][~inv_filter] = True
        self.roi_selections[roi_id]['select'][ inv_filter] = self.__select_data_in_roi(roi_plot, xy_data[inv_filter])


    def reset_roi_selections(self):
        '''
        Resets ROI selections to fit the entire displayed data
        '''
        if type(self.score_data) == type(None):
            return

        data = np.zeros((self.score_data.shape[0], 2))

        for id_y in range(self.num_selections):
            for id_x in range(self.num_selections):
                if id_y == id_x:
                    continue

                data[:, 0] = self.__id_to_data(id_x)
                data[:, 1] = self.__id_to_data(id_y)
            
                inv_filter = ~(np.isnan(data).any(axis=1))
                filtered_data = data[inv_filter]

                if filtered_data.shape[0] == 0:
                    continue

                x0, x1 = np.min(filtered_data[:, 0]), np.max(filtered_data[:, 0])
                y0, y1 = np.min(filtered_data[:, 1]), np.max(filtered_data[:, 1])

                # Have some margin around the ROI
                x0 -= 1; x1 += 1
                y0 -= 1; y1 += 1

                roi_id = self.__get_roi_id(id_x, id_y)
                roi_plot = self.roi_selections[roi_id]['roi']

                is_already_displayed = (roi_plot.scene() != None)
                if not is_already_displayed:
                    self.plot_widget.addItem(roi_plot)

                roi_plot.blockSignals(True)
                roi_plot.setState({
                    'closed' : True,
                    'angle'  : 0.0,
                    'size'   : [1, 1],
                    'pos'    : [0, 0],
                    'points' : [ [x0, y0], [x1, y0], [x1, y1], [x0, y1] ],
                })
                roi_plot.blockSignals(False)

                if not is_already_displayed:
                    self.plot_widget.removeItem(roi_plot)

                self.__update_roi_selection(roi_id, data)

        self.__process_master_selection(emit_data=True)


    def __roi_selection_event(self, emit_data):
        '''
        This function is called whenever the user interacts with the ROI.
        The function updates the selection cache of the displayed data 
        (the current multidimensional plane), then composes the selections
        in all planes together, and emits the resulting selected play data.
        '''
        self.logger.debug('__roi_selection_event')

        # Update selection mask for the current plane
        roi_id_xy = self.__get_roi_id(self.__id_x, self.__id_y)
        roi_plot_xy = self.roi_selections[roi_id_xy]['roi']
        self.__update_roi_selection(roi_id_xy, self.xy_data)

        roi_id_yx = self.__get_roi_id(self.__id_y, self.__id_x)
        roi_plot_yx = self.roi_selections[roi_id_yx]['roi']

        # Flip points for the counterpart (x,y) -> (y,x) ROI along xy-axis diagonal
        state = roi_plot_xy.getState()
        for i in range(len(state['points'])):
            point = state['points'][i]
            state['points'][i] = pyqtgraph.Point(point[1], point[0])
        
        pos = state['pos']
        state['pos'] = pyqtgraph.Point(pos[1], pos[0])

        # ROI plots don't like it when you set state while not being displayed
        # because it makes calls to `self.scene()` to remove stuff being displayed
        # As a workaround, the ROI is temporarily added to the plot, then removed
        #
        # Applies the mirroring to the displayed ROI's counterpart
        self.plot_widget.addItem(roi_plot_yx)
        roi_plot_yx.blockSignals(True)
        roi_plot_yx.setState(state)
        roi_plot_yx.blockSignals(False)
        self.plot_widget.removeItem(roi_plot_yx)

        self.__process_master_selection(emit_data)
        

    def __process_master_selection(self, emit_data):
        '''
        Composes the selections in all planes together, and emits the resulting selected play data.
        '''
        play_data_out = self.get_selected()
        if type(play_data_out) == type(None):
            return

        if emit_data:
            self.logger.debug('region_changed.emit ->')
            self.region_changed.emit(play_data_out)
            self.logger.debug('region_changed.emit <-')


    def __select_data_in_roi(self, roi_plot, data):
        '''
        Returns a mask array selecting displayed data points that are 
        located within the given ROI.

        Invalid values (NaN and Inf) must not be passed to this function.

        # Thanks https://stackoverflow.com/a/2922778
        '''
        handles = [ pyqtgraph.Point(h.pos()) + roi_plot.pos() for h in roi_plot.getHandles() ]

        is_in_roi = np.zeros((data.shape[0]), dtype=np.bool)
        iters = list(range(len(handles)))

        for i in iters:
            _i = iters[i]
            _j = iters[i - 1]

            test1 = ((handles[_i].y() > data[:, 1]) != (handles[_j].y() > data[:, 1]))

            if handles[_j].y() == handles[_i].y():
                test2 = False
            else:
                test2 = (data[:, 0] < (handles[_j].x() - handles[_i].x()) * (data[:, 1] - handles[_i].y()) / (handles[_j].y() - handles[_i].y()) + handles[_i].x())

            select = test1 & test2
            is_in_roi[select] = ~is_in_roi[select]

        return is_in_roi


    def __set_composition_data(self, id_x=None, id_y=None, force_update=False):
        '''
        This is called whenever the user changes the data being displayed. Updates
        the displayed ROI, displayed data, plane selection, and all selection
        masks.

        NOTE: Currently does not cause emission of play data
        '''
        self.logger.debug('__set_composition_data')

        update_x = force_update
        update_y = force_update
 
        can_update_x = (id_x != None) and (self.__id_x != id_x)
        can_update_y = (id_y != None) and (self.__id_y != id_y)
        prev_xy_exists = (self.__id_x != None) and (self.__id_y != None)

        if can_update_x:
            if prev_xy_exists:
                self.plot_widget.removeItem(self.roi_selections[self.__get_roi_id(self.__id_x, self.__id_y)]['roi'])
            
            if self.__id_y != None:
                self.plot_widget.addItem(self.roi_selections[self.__get_roi_id(id_x, self.__id_y)]['roi'])
                update_x = True

            if self.__id_x != None:
                self.y_axis_selection.button(self.__id_x).setEnabled(True)
            self.y_axis_selection.button(id_x).setEnabled(False)

            self.__id_x = id_x

        if can_update_y:
            if prev_xy_exists:
                self.plot_widget.removeItem(self.roi_selections[self.__get_roi_id(self.__id_x, self.__id_y)]['roi'])
            
            if self.__id_x != None:
                self.plot_widget.addItem(self.roi_selections[self.__get_roi_id(self.__id_x, id_y)]['roi'])
                update_y = True

            if self.__id_y != None:
                self.x_axis_selection.button(self.__id_y).setEnabled(True)
            self.x_axis_selection.button(id_y).setEnabled(False)

            self.__id_y = id_y
            
        if self.score_data.shape[0] == 0:
            return

        if update_x:
            self.xy_data[:, 0] = self.__id_to_data(self.__id_x)
            self.plot_widget.setLabel('bottom', self.__get_selection_string(self.__id_x))

        if update_y:
            self.xy_data[:, 1] = self.__id_to_data(self.__id_y)
            self.plot_widget.setLabel('left', self.__get_selection_string(self.__id_y))

        ''''
        # Prepare dictionary of md5-to-map names to apply to each data point
        unique_md5s = ScoreNpyData.get_unique_md5s(self.score_data)
        md5_to_name = {}
        
        for unique_md5 in unique_md5s:
            md5_str = ScoreNpyData.get_md5_str(*unique_md5)
            md5_to_name[md5_str] = MapsDB.get_map_file_name(md5_str, filename=False)[0]
        '''

        # Add information that would be displayed when user hover over data point
        def score_data_to_str(score_data):
            '''
            md5_str  = ScoreNpyData.get_md5_str(*score_data[[ScoreNpyData.MAP_MD5_LH, ScoreNpyData.MAP_MD5_UH]].astype(np.uint64))
            
            map_name = md5_to_name[md5_str]
            time     = score_data[ScoreNpyData.T_MAP]
            t_offset = score_data[ScoreNpyData.T_HIT] - score_data[ScoreNpyData.T_MAP]
            x_offset = score_data[ScoreNpyData.X_HIT] - score_data[ScoreNpyData.X_MAP]
            y_offset = score_data[ScoreNpyData.Y_HIT] - score_data[ScoreNpyData.Y_MAP]

            ret = f'\n' \
                f'    map:      {map_name}\n' \
                f'    time:     {time}\n' \
                f'    t offset: {t_offset}\n' \
                f'    x offset: {x_offset}\n' \
                f'    y offset: {y_offset}'

            return ret
            '''
            return ''

        if update_x or update_y:
            #i_data = np.apply_along_axis(score_data_to_str, 1, self.score_data)

            # Make sure no invalid values are passed to display or it will won't 
            # display points due to innability to compute bounds
            inv_filter = ~(np.isnan(self.xy_data).any(axis=1))

            #self.data_plot.setData(self.xy_data[inv_filter, 0], self.xy_data[inv_filter, 1], data=i_data[inv_filter])
            self.data_plot.setData(self.xy_data[inv_filter, 0], self.xy_data[inv_filter, 1])


    def __id_to_data(self, id_):
        if id_ == self.__ID_CS:
            return self.score_data['CS'].values

        if id_ == self.__ID_AR:
            return self.score_data['AR'].values

        if id_ == self.__ID_T_PRESS_DIFF:
            return self.score_data['DIFF_T_PRESS_DIFF'].values

        if id_ == self.__ID_T_PRESS_RATE:
            return self.score_data['DIFF_T_PRESS_RATE'].values

        if id_ == self.__ID_T_BPM:
            # Convert 1/ms -> BPM then put it in terms of 1/4 snap
            return 15000/self.score_data['DIFF_T_PRESS_DIFF'].values

        if id_ == self.__ID_T_PRESS_INC:
            return self.score_data['DIFF_T_PRESS_INC'].values

        if id_ == self.__ID_T_PRESS_DEC:
            return self.score_data['DIFF_T_PRESS_DEC'].values

        if id_ == self.__ID_T_HOLD_DUR:
            return self.score_data['DIFF_T_HOLD_DUR'].values

        if id_ == self.__ID_T_PRESS_RHM:
            return self.score_data['DIFF_T_PRESS_RHM'].values

        #if id_ == self.__ID_DT_RHYTM_D:
        #    return [ 0 ] #self.score_data['DIFF_DT_RHYM_D'].values

        if id_ == self.__ID_XY_DIST:
            return self.score_data['DIFF_XY_DIST'].values

        if id_ == self.__ID_XY_ANGLE:
            return self.score_data['DIFF_XY_ANGLE'].values

        if id_ == self.__ID_XY_LIN_VEL:
            return 1000*self.score_data['DIFF_XY_LIN_VEL'].values

        if id_ == self.__ID_XY_ANG_VEL:
            return self.score_data['DIFF_XY_ANG_VEL'].values

        if id_ == self.__ID_VIS_VISIBLE:
            return self.score_data['DIFF_VIS_VISIBLE'].values

        raise Exception(f'Unknown id: {id_}')


    def __get_selection_string(self, id_):
        if id_ == self.__ID_CS:            return 'Beatmap CS'
        if id_ == self.__ID_AR:            return 'Beatmap AR'
        if id_ == self.__ID_T_PRESS_DIFF:  return 'Time interval between presses (ms)'
        if id_ == self.__ID_T_PRESS_RATE:  return 'Time interval across 3 presses (ms)'
        if id_ == self.__ID_T_BPM:         return 'BPM @ 1/4 meter (60/s)'
        if id_ == self.__ID_T_PRESS_INC:   return 'BPM Increase Time (ms)'
        if id_ == self.__ID_T_PRESS_DEC:   return 'BPM Decrease Time (ms)'
        if id_ == self.__ID_T_PRESS_RHM:   return '% the note is from previous note to next note (% of tn[2] - tn[0])'
        #if id_ == self.__ID_DT_RHYTM_D:   return 'Normalized rate (%)'
        if id_ == self.__ID_T_HOLD_DUR:    return 'Hold duration (ms)'
        if id_ == self.__ID_XY_DIST:       return 'Distance (osu!px)'
        if id_ == self.__ID_XY_ANGLE:      return 'Angle (deg)'
        if id_ == self.__ID_XY_LIN_VEL:    return 'Linear Velocity (osu!px/s)'
        if id_ == self.__ID_XY_ANG_VEL:    return 'Angular Velocity (RPM)'
        if id_ == self.__ID_VIS_VISIBLE:   return 'Number of notes visible (#)'

        raise Exception(f'Unknown id: {id_}')


    def __x_axis_selection_event(self, id_x):
        self.logger.debug('__x_axis_selection_event')
        self.__set_composition_data(id_x=id_x)


    def __y_axis_selection_event(self, id_y):
        self.logger.debug('__y_axis_selection_event')
        self.__set_composition_data(id_y=id_y)
