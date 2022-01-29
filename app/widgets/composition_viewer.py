import pyqtgraph
from pyqtgraph import QtGui, QtCore

import numpy as np

from osu_analysis import StdScoreData

from app.data_recording.data import RecData



class CompositionViewer(QtGui.QWidget):

    region_changed = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.data = np.zeros((0, 2))
        self.play_data = None

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
        self.__ID_BPM          = 0
        self.__ID_DT_NOTE      = 1
        self.__ID_DT_RHYTM     = 2
        self.__ID_ANGLE        = 3
        self.__ID_DISTANCE     = 4
        self.__ID_VELOCITY     = 5
        self.__ID_BPM_INC_TIME = 6
        self.__ID_BPM_DEC_TIME = 7
        self.__CS              = 8
        self.__AR              = 9

        self.__id_x = None
        self.__id_y = None

        selections = {
             'BPM'          : self.__ID_BPM, 
             'DT_NOTE'      : self.__ID_DT_NOTE,
             'DT_RHYTM'     : self.__ID_DT_RHYTM,
             'ANGLE'        : self.__ID_ANGLE, 
             'DISTANCE'     : self.__ID_DISTANCE, 
             'VELOCITY'     : self.__ID_VELOCITY, 
             'BPM INC TIME' : self.__ID_BPM_INC_TIME,
             'BPM DEC TIME' : self.__ID_BPM_DEC_TIME,
             'CS'           : self.__CS,
             'AR'           : self.__AR,
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

        self.reset_roi_selections_button.clicked.connect(self.__reset_roi_selections)

        self.x_axis_selection.idPressed.connect(self.__x_axis_selection_event)
        self.y_axis_selection.idPressed.connect(self.__y_axis_selection_event)

        self.x_axis_selection.button(self.__ID_BPM).setChecked(True)
        self.y_axis_selection.button(self.__ID_ANGLE).setChecked(True)
        self.__set_composition_data(id_x=self.__ID_BPM, id_y=self.__ID_ANGLE)
        

    def set_composition_from_play_data(self, play_data):
        '''
        Called whenever different maps or time of plays are selected in
        the overview window. Updates the play data used to display the composition,
        and then proceeds to update everything else.
        '''
        if play_data.shape[0] == 0:
            return

        # Set displayed data
        self.play_data = play_data
        self.data = np.zeros((play_data.shape[0], 2))
        self.__set_composition_data(id_x=self.__id_x, id_y=self.__id_y, force_update=True)

        # Update all selection masks
        data = np.zeros((self.play_data.shape[0], 2))

        for id_y in range(self.num_selections):
            for id_x in range(self.num_selections):
                if id_y == id_x:
                    continue
                
                data[:, 0] = self.__id_to_data(id_x, self.play_data)
                data[:, 1] = self.__id_to_data(id_y, self.play_data)

                roi_id = self.__get_roi_id(id_x, id_y)
                self.__update_roi_selection(roi_id, data)

        if self.play_data.shape[0] < 10000:
            self.__process_master_selection(emit_data=True)


    def get_selected(self):
        '''
        Composes the selections in all planes together, and returns the resulting selected play data.
        '''
        if type(self.play_data) == type(None):
            return

        # Calculate master selection across all multidimensional planes
        select = np.ones((self.play_data.shape[0]), dtype=np.bool)
        for roi_selection in self.roi_selections.values():
            select &= roi_selection['select']

        play_data_out = self.play_data[select]
        self.num_data_points_label.setText(f'Num data points selected: {play_data_out.shape[0]}')

        return play_data_out


    def __get_roi_id(self, id_x, id_y):
        '''
        Used to generate a unique ID for a given pair of axes.
        '''
        return id_y*self.num_selections + id_x


    def __update_roi_selection(self, roi_id, data):
        '''
        Updates the cached selection mask
        '''
        if type(self.play_data) == type(None):
            return

        roi_plot = self.roi_selections[roi_id]['roi']
        self.roi_selections[roi_id]['select'] = self.__select_data_in_roi(roi_plot, data)
        self.roi_selections[roi_id]['select'] |= np.isnan(data).any(axis=1)


    def __reset_roi_selections(self):
        '''
        Resets ROI selections to fit the entire displayed data
        '''
        if type(self.play_data) == type(None):
            return

        data = np.zeros((self.play_data.shape[0], 2))

        for id_y in range(self.num_selections):
            for id_x in range(self.num_selections):
                if id_y == id_x:
                    continue

                data[:, 0] = self.__id_to_data(id_x, self.play_data)
                data[:, 1] = self.__id_to_data(id_y, self.play_data)
                
                nan_filter = ~np.isnan(data).any(axis=1)
                filtered_data = data[nan_filter]

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
        # Update selection mask for the current plane
        roi_id_xy = self.__get_roi_id(self.__id_x, self.__id_y)
        roi_plot_xy = self.roi_selections[roi_id_xy]['roi']
        self.__update_roi_selection(roi_id_xy, self.data)

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
        if type(self.play_data) == type(None):
            return

        # Calculate master selection across all multidimensional planes
        select = np.ones((self.play_data.shape[0]), dtype=np.bool)
        for roi_selection in self.roi_selections.values():
            select &= roi_selection['select']

        play_data_out = self.play_data[select]
        self.num_data_points_label.setText(f'Num data points selected: {play_data_out.shape[0]}')

        if emit_data:
            self.region_changed.emit(play_data_out)


    def __select_data_in_roi(self, roi_plot, data):
        '''
        Returns a mask array selecting displayed data points that are 
        located within the given ROI.

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
            
        if type(self.play_data) == type(None):
            return

        if update_x:
            self.data[:, 0] = self.__id_to_data(self.__id_x, self.play_data)
            self.plot_widget.setLabel('bottom', self.__get_selection_string(self.__id_x))

        if update_y:
            self.data[:, 1] = self.__id_to_data(self.__id_y, self.play_data)
            self.plot_widget.setLabel('left', self.__get_selection_string(self.__id_y))

        def score_data_to_str(data):
            ret = f'\n' \
                f'    t offset: {data[RecData.T_OFFSETS]:.2f}\n' \
                f'    x offset: {data[RecData.X_OFFSETS]:.2f}\n' \
                f'    y offset: {data[RecData.Y_OFFSETS]:.2f}'

            return ret

        if update_x or update_y:
            i_data = np.apply_along_axis(lambda data: score_data_to_str(data), 1, self.play_data)
            self.data_plot.setData(self.data[:, 0], self.data[:, 1], data=i_data)


    def __id_to_data(self, id_, play_data):
        if id_ == self.__ID_BPM:
            # Convert 1/ms -> BPM then put it in terms of 1/4 snap
            return 15000/play_data[:, RecData.DT]

        if id_ == self.__ID_DT_NOTE:
            return play_data[:, RecData.DT_NOTES]

        if id_ == self.__ID_DT_RHYTM:
            return play_data[:, RecData.DT_RHYM]

        if id_ == self.__ID_ANGLE:
            return play_data[:, RecData.ANGLE]

        if id_ == self.__ID_DISTANCE:
            return play_data[:, RecData.DS]

        if id_ == self.__ID_VELOCITY:
            return 1000*play_data[:, RecData.DS]/play_data[:, RecData.DT]

        if id_ == self.__ID_BPM_DEC_TIME:
            return play_data[:, RecData.DT_DEC]

        if id_ == self.__ID_BPM_INC_TIME:
            return play_data[:, RecData.DT_INC]

        if id_ == self.__CS:
            return play_data[:, RecData.CS]

        if id_ == self.__AR:
            return play_data[:, RecData.AR]

        raise Exception(f'Unknown id: {id_}')


    def __get_selection_string(self, id_):
        if id_ == self.__ID_BPM:
            return 'BPM @ 1/4 meter (60/s)'

        if id_ == self.__ID_DT_NOTE:
            return 'Time interval across 3 notes (ms)'

        if id_ == self.__ID_DT_RHYTM:
            return '% the note is from previous note to next note (% of tn[2] - tn[0])'

        if id_ == self.__ID_ANGLE:
            return 'Angle (deg)'

        if id_ == self.__ID_DISTANCE:
            return 'Distance (osu!px)'

        if id_ == self.__ID_VELOCITY:
            return 'Velocity (osu!px/s)'

        if id_ == self.__ID_BPM_DEC_TIME:
            return 'BPM Decrease Time (ms)'

        if id_ == self.__ID_BPM_INC_TIME:
            return 'BPM Increase Time (ms)'

        if id_ == self.__CS:
            return 'CS'

        if id_ == self.__AR:
            return 'AR'

        raise Exception(f'Unknown id: {id_}')


    def __x_axis_selection_event(self, id_x):
        self.__set_composition_data(id_x=id_x)


    def __y_axis_selection_event(self, id_y):
        self.__set_composition_data(id_y=id_y)
