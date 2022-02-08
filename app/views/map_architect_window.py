"""
Provides a way to generate maps for data collection. This is nowhere close to a beatmap editor and provides basic functionality
to generate repeating patterns and alter maps.

Features:
- Inserts a repeating pattern given BPM, spacing and angle, number of notes, and rotation
- Allows BPM, spacing and angle to be changed throughout generated pattern based on modulation
- Allows to change map rate
"""
import os
import json
import time
import datetime
import shutil
import hashlib
import math
import numpy as np
import textwrap

from pyqtgraph.Qt import QtCore, QtGui

from osu_analysis import BeatmapIO
from app.misc.osu_utils import OsuUtils
from app.file_managers import AppConfig



class _ValueLineEdit(QtGui.QLineEdit):

    broadcast_event = QtCore.pyqtSignal(int, object)
    value_enter_event = QtCore.pyqtSignal()

    APPLY_DELTA = 0
    APPLY_VALUE = 1

    def __init__(self, *args, **kwargs):
        QtGui.QLineEdit.__init__(self, *args, **kwargs)

        # Broadcast is a feature that allows the user to modify the value of other controls proportionally 
        # to the one being actively modified while holding down the shift key. For example, if the user
        # enters a value while holding down the shift key, the value will be applied to all other
        # controls as well. If the user scrolls the mouse wheel while holding down the shift key,
        # the respective values in other controls will be incremented/decremented as well.
        

    def keyPressEvent(self, event):
        if event.key() in [ QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            event.accept()
            self.apply_value(apply=self.APPLY_VALUE)

            shift_is_pressed = QtGui.QGuiApplication.queryKeyboardModifiers() & QtCore.Qt.ShiftModifier
            if shift_is_pressed:
                self.broadcast_event.emit(self.APPLY_VALUE, self.__get_val())

            self.value_enter_event.emit()
        
        QtGui.QLineEdit.keyPressEvent(self, event)


    def wheelEvent(self, event):
        event.accept()

        # Figure out if the value is an int or float
        StrToVal = int if type(self.validator()) is QtGui.QIntValidator else float
        
        # Done through QGuiApplication instead of keyEvent to allow ctrl modifier to work when window is unfocused
        ctrl_is_pressed = QtGui.QGuiApplication.queryKeyboardModifiers() & QtCore.Qt.ControlModifier
        shift_is_pressed = QtGui.QGuiApplication.queryKeyboardModifiers() & QtCore.Qt.ShiftModifier

        # Int -> +/- 1,  Float -> +/- 0.1
        delta_mul = 10 if ctrl_is_pressed else 1
        delta_mul *= 1 if StrToVal == int else 0.1

        delta = 1*delta_mul if event.angleDelta().y() > 0 else -1*delta_mul

        self.apply_value(apply=self.APPLY_DELTA, value=delta)

        # If shift key is being held down, broadcast modification to other controls
        if shift_is_pressed:
            self.broadcast_event.emit(self.APPLY_DELTA, delta)

        self.value_enter_event.emit()


    def apply_value(self, apply, value=None):
        if type(value) not in [ int, float, type(None) ]:
            raise ValueError(f'Value must be a float or int, not {type(value)}')

        if value != None:
            if apply == self.APPLY_VALUE:
                self.setText(str(value))
            elif apply == self.APPLY_DELTA:
                self.setText(str(round(self.__get_val() + value, 1)))
            else:
                raise ValueError(f'Invalid apply value: {apply}')

        old_value = self.__get_val()
        new_value = self.__validate(old_value)

        if old_value == new_value:
            return
        
        self.setText(str(new_value))
        

    def __validate(self, value):
        validator = self.validator()
        value = min(validator.top(), max(validator.bottom(), value))
        return value


    def __get_val(self):
        StrToVal = int if type(self.validator()) is QtGui.QIntValidator else float
        return StrToVal(self.text())



class MapArchitectWindow(QtGui.QMainWindow):

    gen_map_event = QtCore.pyqtSignal(object, float, float)

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Map Architect')

        self.OBJ_WIDTH   = 90
        self.OBJ_HEIGHT  = 25
        self.OBJ_MARGIN  = 11

        self.OBJ_SPACING_SMALL = 5
        self.OBJ_SPACING_LARGE = 22

        self.__controls = {}
        self.__id = 0

        self.__init_components()
        self.__build_layout()
        self.__configure_components()
        self.__connect_signals()

        self.__add_control()


    def __init_components(self):
        self.menu_bar  = QtGui.QMenuBar()
        self.file_menu = QtGui.QMenu("&File")

        self.save_config_action = QtGui.QAction("&Save config", self.file_menu, triggered=lambda: self.__save_config_dialog())
        self.open_config_action = QtGui.QAction("&Open config", self.file_menu, triggered=lambda: self.__open_config_dialog())

        # Labels on the left side: https://i.imgur.com/ACZkQ2n.png
        self.spacing_label = QtGui.QLabel('Spacings:')
        self.angles_label  = QtGui.QLabel('Angles:')
        self.bpm_label     = QtGui.QLabel('BPMs:')
        self.label_layout  = QtGui.QVBoxLayout()

        # Inputs on bottom: https://i.imgur.com/xvZnhHe.png
        self.num_notes_txtbx  = _ValueLineEdit()
        self.num_notes_label  = QtGui.QLabel('Num Notes')
        self.num_notes_layout = QtGui.QVBoxLayout()

        self.rotation_txtbx  = _ValueLineEdit()
        self.rotation_label  = QtGui.QLabel('Rotation')
        self.rotation_layout = QtGui.QVBoxLayout()

        self.cs_txtbx  = _ValueLineEdit()
        self.cs_label  = QtGui.QLabel('CS')
        self.cs_layout = QtGui.QVBoxLayout()

        self.ar_txtbx  = _ValueLineEdit()
        self.ar_label  = QtGui.QLabel('AR')
        self.ar_layout = QtGui.QVBoxLayout()

        self.spacer = QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        # Control area: https://i.imgur.com/hxMYN8M.png
        self.ctrl_area = QtGui.QWidget()
        self.ctrl_scroll_area = QtGui.QScrollArea()
        self.note_ctrl_layout = QtGui.QHBoxLayout()
        self.map_ctrl_layout = QtGui.QHBoxLayout()

        self.ctrl_layout = QtGui.QHBoxLayout()

        # Buttons below input on bottom: https://i.imgur.com/dl3WtZH.png
        self.btn_layout = QtGui.QHBoxLayout()
        self.add_btn = QtGui.QPushButton('Add Control')
        self.gen_btn = QtGui.QPushButton('Generate Map')

        self.architect_widget = QtGui.QWidget()
        self.architect_layout = QtGui.QVBoxLayout(self.architect_widget)

        self.splitter = QtGui.QSplitter()
        
        self.name_label = QtGui.QLabel('Map Name:')
        self.name_txtbx = QtGui.QLineEdit()

        self.description_label = QtGui.QLabel('Map Description:')
        self.description_txtbx = QtGui.QTextEdit()

        self.name_layout = QtGui.QVBoxLayout()
        self.description_layout = QtGui.QVBoxLayout()

        self.metadata_widget = QtGui.QWidget()
        self.metadata_layout = QtGui.QVBoxLayout(self.metadata_widget)

        self.main_widget = QtGui.QWidget()
        self.main_layout = QtGui.QVBoxLayout(self.main_widget)


    def __build_layout(self):
        self.menu_bar.addMenu(self.file_menu)
        self.file_menu.addAction(self.save_config_action)
        self.file_menu.addAction(self.open_config_action)

        self.label_layout.addWidget(self.spacing_label)
        self.label_layout.addWidget(self.angles_label)
        self.label_layout.addWidget(self.bpm_label)
        self.label_layout.addStretch()

        self.num_notes_layout.addWidget(self.num_notes_txtbx)
        self.num_notes_layout.addWidget(self.num_notes_label)

        self.rotation_layout.addWidget(self.rotation_txtbx)
        self.rotation_layout.addWidget(self.rotation_label)

        self.cs_layout.addWidget(self.cs_txtbx)
        self.cs_layout.addWidget(self.cs_label)
        
        self.ar_layout.addWidget(self.ar_txtbx)
        self.ar_layout.addWidget(self.ar_label)
        
        self.map_ctrl_layout.addLayout(self.num_notes_layout)
        self.map_ctrl_layout.addLayout(self.rotation_layout)
        self.map_ctrl_layout.addLayout(self.cs_layout)
        self.map_ctrl_layout.addLayout(self.ar_layout)
        
        self.ctrl_area.setLayout(self.note_ctrl_layout)
        self.ctrl_scroll_area.setWidget(self.ctrl_area)

        self.note_ctrl_layout.addItem(self.spacer)

        self.ctrl_layout.addLayout(self.label_layout)
        self.ctrl_layout.addWidget(self.ctrl_scroll_area)
        
        self.btn_layout.addWidget(self.add_btn)
        self.btn_layout.addWidget(self.gen_btn)

        self.architect_layout.addLayout(self.ctrl_layout)
        self.architect_layout.addLayout(self.map_ctrl_layout)
        self.architect_layout.addLayout(self.btn_layout)

        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.name_txtbx)

        self.description_layout.addWidget(self.description_label)
        self.description_layout.addWidget(self.description_txtbx)

        self.metadata_layout.addLayout(self.name_layout)
        self.metadata_layout.addLayout(self.description_layout)

        self.splitter.addWidget(self.architect_widget)
        self.splitter.addWidget(self.metadata_widget)

        self.main_layout.addWidget(self.menu_bar)
        self.main_layout.addWidget(self.splitter)

        self.setCentralWidget(self.main_widget)


    def __configure_components(self):
        self.num_notes_txtbx.setValidator(QtGui.QIntValidator(3, 500))
        self.rotation_txtbx.setValidator(QtGui.QIntValidator(0, 180))
        self.cs_txtbx.setValidator(QtGui.QDoubleValidator(0, 10, 1))
        self.ar_txtbx.setValidator(QtGui.QDoubleValidator(0, 11, 1))

        self.num_notes_txtbx.setText('60')
        self.rotation_txtbx.setText('0')
        self.cs_txtbx.setText('4')
        self.ar_txtbx.setText('8')

        self.num_notes_layout.setAlignment(self.num_notes_txtbx, QtCore.Qt.AlignHCenter)
        self.num_notes_layout.setAlignment(self.num_notes_label, QtCore.Qt.AlignHCenter)

        self.rotation_layout.setAlignment(self.rotation_txtbx, QtCore.Qt.AlignHCenter)
        self.rotation_layout.setAlignment(self.rotation_label, QtCore.Qt.AlignHCenter)

        self.cs_layout.setAlignment(self.cs_txtbx, QtCore.Qt.AlignHCenter)
        self.cs_layout.setAlignment(self.cs_label, QtCore.Qt.AlignHCenter)

        self.ar_layout.setAlignment(self.ar_txtbx, QtCore.Qt.AlignHCenter)
        self.ar_layout.setAlignment(self.ar_label, QtCore.Qt.AlignHCenter)

        self.num_notes_txtbx.setFixedSize(self.OBJ_WIDTH, self.OBJ_HEIGHT)
        self.rotation_txtbx.setFixedSize(self.OBJ_WIDTH, self.OBJ_HEIGHT)
        self.cs_txtbx.setFixedSize(self.OBJ_WIDTH, self.OBJ_HEIGHT)
        self.ar_txtbx.setFixedSize(self.OBJ_WIDTH, self.OBJ_HEIGHT)

        self.map_ctrl_layout.setSpacing(self.OBJ_SPACING_LARGE)
        self.note_ctrl_layout.setSpacing(self.OBJ_SPACING_LARGE)

        self.num_notes_layout.setSpacing(self.OBJ_SPACING_SMALL)
        self.rotation_layout.setSpacing(self.OBJ_SPACING_SMALL)
        self.cs_layout.setSpacing(self.OBJ_SPACING_SMALL)
        self.ar_layout.setSpacing(self.OBJ_SPACING_SMALL)

        self.label_layout.setContentsMargins(self.OBJ_MARGIN, self.OBJ_MARGIN, self.OBJ_MARGIN, self.OBJ_MARGIN)
        self.label_layout.setSpacing(self.OBJ_HEIGHT + self.OBJ_MARGIN)
        self.label_layout.setAlignment(self.spacing_label, QtCore.Qt.AlignTop | QtCore.Qt.AlignRight)
        self.label_layout.setAlignment(self.angles_label, QtCore.Qt.AlignTop | QtCore.Qt.AlignRight)
        self.label_layout.setAlignment(self.bpm_label, QtCore.Qt.AlignTop | QtCore.Qt.AlignRight)

        self.ctrl_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.ctrl_scroll_area.setWidgetResizable(True)
        self.ctrl_scroll_area.setMinimumHeight((self.OBJ_HEIGHT + self.OBJ_SPACING_LARGE)*4 + self.OBJ_MARGIN*2)

        self.map_ctrl_layout.setContentsMargins(100, self.OBJ_MARGIN, self.OBJ_MARGIN, self.OBJ_MARGIN)

        self.name_layout.setContentsMargins(0, 0, 0, 0)
        self.name_layout.setSpacing(self.OBJ_SPACING_SMALL)
        self.name_layout.setSizeConstraint(QtGui.QLayout.SetNoConstraint)
        
        self.name_txtbx.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Fixed)
        self.name_txtbx.setFixedHeight(self.OBJ_HEIGHT)
        self.name_txtbx.setMaximumWidth(self.name_txtbx.parent().maximumSize().width())

        self.description_layout.setContentsMargins(0, 0, 0, 0)
        self.description_layout.setSpacing(self.OBJ_SPACING_SMALL)

        self.metadata_layout.setContentsMargins(self.OBJ_MARGIN, 0, self.OBJ_MARGIN, self.OBJ_MARGIN)
        self.metadata_layout.setSpacing(self.OBJ_SPACING_LARGE)

        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setMaximumHeight(0)


    def __connect_signals(self):
        self.add_btn.clicked.connect(lambda: self.__add_control())
        self.gen_btn.clicked.connect(self.__generate_map)

        self.num_notes_txtbx.value_enter_event.connect(self.__update_gen_map)
        self.rotation_txtbx.value_enter_event.connect(self.__update_gen_map)
        self.cs_txtbx.value_enter_event.connect(self.__update_gen_map)
        self.ar_txtbx.value_enter_event.connect(self.__update_gen_map)


    def __save_config_dialog(self):
        file_name, _ = QtGui.QFileDialog.getSaveFileName(self, 'Save Configuration', '', '*.json')
        if not file_name:
            return
        
        data = self.__get_data()
        with open(file_name, 'w') as f:
            json.dump(data, f)
        

    def __open_config_dialog(self):
        file_name, _ = QtGui.QFileDialog.getOpenFileName(self, 'Open Configuration', '', '*.json')
        if not file_name:
            return
        
        with open(file_name, 'r') as f:
            data = json.load(f)

        if 0 in [ len(data['spacings']), len(data['angles']), len(data['bpms']) ]:
            QtGui.QMessageBox.error('Invalid Configuration File', 'Bad configuration file! Number of spacings, angles, and times must must not be 0.')
            return

        if not (len(data['spacings']) == len(data['angles']) == len(data['bpms'])):
            QtGui.QMessageBox.error(self, 'Error', 'Bad configuration file! Number of spacings, angles, and times must be equal.')
            return
        
        if 'name' in data:
            self.name_txtbx.setText(data['name'])
        
        if 'description' in data:
            self.description_txtbx.setText(data['description'])

        num_ctrls_now = len(list(self.__controls.keys()))
        num_ctrls_req = len(data['spacings'])

        num_to_rmv = max(0, num_ctrls_now - num_ctrls_req)
        num_to_add = max(0, num_ctrls_req - num_ctrls_now)

        for _ in range(num_to_rmv):
            self.__remove_control(list(self.__controls)[-1])

        for _ in range(num_to_add):
            self.__add_control()

        for spacing, angle, bpm, btn in zip(data['spacings'], data['angles'], data['bpms'], self.__controls.keys()):
            self.__controls[btn]['spacing_txtbx'].apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=spacing)
            self.__controls[btn]['angles_txtbx'].apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=angle)
            self.__controls[btn]['bpm_txtbx'].apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=bpm)

        self.num_notes_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=data['num_notes'])
        self.rotation_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=data['rotation'])
        self.cs_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=data['cs'])
        self.ar_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=data['ar'])


    def __get_data(self):
        # Validate the data before returning the values
        for btn in self.__controls.keys():
            self.__controls[btn]['spacing_txtbx'].apply_value(apply=_ValueLineEdit.APPLY_VALUE)
            self.__controls[btn]['angles_txtbx'].apply_value(apply=_ValueLineEdit.APPLY_VALUE)
            self.__controls[btn]['bpm_txtbx'].apply_value(apply=_ValueLineEdit.APPLY_VALUE)

        self.num_notes_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE)
        self.rotation_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE)
        self.cs_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE)
        self.ar_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE)

        return {
            'spacings'   : list([ int(self.__controls[btn]['spacing_txtbx'].text()) for btn in self.__controls ]),
            'angles'     : list([ int(self.__controls[btn]['angles_txtbx'].text()) for btn in self.__controls ]),
            'bpms'       : list([ int(self.__controls[btn]['bpm_txtbx'].text()) for btn in self.__controls ]),
            'num_notes'  : int(self.num_notes_txtbx.text()),
            'rotation'   : int(self.rotation_txtbx.text()),
            'cs'         : int(self.cs_txtbx.text()),
            'ar'         : int(self.ar_txtbx.text()),
            'name'       : self.name_txtbx.text(),
            'description': self.description_txtbx.toPlainText(),
        }


    def __add_control(self, spacing=None, angle=None, bpm=None):
        spacing_txtbx = _ValueLineEdit()
        angles_txtbx  = _ValueLineEdit()
        bpm_txtbx     = _ValueLineEdit()
        remove_btn    = QtGui.QPushButton('Remove')

        spacing_txtbx.setValidator(QtGui.QIntValidator(0, 512))
        angles_txtbx.setValidator(QtGui.QIntValidator(-180, 180))
        bpm_txtbx.setValidator(QtGui.QIntValidator(1, 1000))

        if spacing is not None: spacing_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=spacing)
        else:                   spacing_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=100)

        if angle is not None:   angles_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=angle)
        else:                   angles_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=90)

        if bpm is not None:     bpm_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=bpm)
        else:                   bpm_txtbx.apply_value(apply=_ValueLineEdit.APPLY_VALUE, value=60)

        ctrl_layout = QtGui.QVBoxLayout()
        ctrl_layout.addWidget(spacing_txtbx)
        ctrl_layout.addWidget(angles_txtbx)
        ctrl_layout.addWidget(bpm_txtbx)
        ctrl_layout.addWidget(remove_btn)
        ctrl_layout.addStretch()

        ctrl_layout.setAlignment(spacing_txtbx, QtCore.Qt.AlignCenter)
        ctrl_layout.setAlignment(angles_txtbx, QtCore.Qt.AlignCenter)
        ctrl_layout.setAlignment(bpm_txtbx, QtCore.Qt.AlignCenter)
        ctrl_layout.setAlignment(remove_btn, QtCore.Qt.AlignCenter)

        spacing_txtbx.setFixedSize(self.OBJ_WIDTH, self.OBJ_HEIGHT)
        angles_txtbx.setFixedSize(self.OBJ_WIDTH, self.OBJ_HEIGHT)
        bpm_txtbx.setFixedSize(self.OBJ_WIDTH, self.OBJ_HEIGHT)
        remove_btn.setFixedSize(self.OBJ_WIDTH, self.OBJ_HEIGHT)

        self.note_ctrl_layout.removeItem(self.spacer)
        self.note_ctrl_layout.addLayout(ctrl_layout)
        self.note_ctrl_layout.addItem(self.spacer)
        self.note_ctrl_layout.setAlignment(ctrl_layout, QtCore.Qt.AlignLeft)

        remove_btn.clicked.connect(lambda _, btn=remove_btn: self.__remove_control(btn))

        spacing_txtbx.value_enter_event.connect(self.__update_gen_map)
        spacing_txtbx.broadcast_event.connect(lambda apply, value, txtbx=spacing_txtbx: self.__spacing_broadcast_event(apply, value, txtbx))

        angles_txtbx.value_enter_event.connect(self.__update_gen_map)
        angles_txtbx.broadcast_event.connect(lambda apply, value, txtbx=angles_txtbx: self.__angles_broadcast_event(apply, value, txtbx))

        bpm_txtbx.value_enter_event.connect(self.__update_gen_map)
        bpm_txtbx.broadcast_event.connect(lambda apply, value, txtbx=bpm_txtbx: self.__bpm_broadcast_event(apply, value, txtbx))

        self.__controls[remove_btn] = {
            'layout'        : ctrl_layout,
            'spacing_txtbx' : spacing_txtbx,
            'angles_txtbx'  : angles_txtbx,
            'bpm_txtbx'     : bpm_txtbx,
        }

        self.__update_gen_map()
        return remove_btn


    def __remove_control(self, btn):
        if len(self.__controls) == 1:
            return

        self.__controls[btn]['spacing_txtbx'].value_enter_event.disconnect()
        self.__controls[btn]['spacing_txtbx'].broadcast_event.disconnect()

        self.__controls[btn]['angles_txtbx'].value_enter_event.disconnect()
        self.__controls[btn]['angles_txtbx'].broadcast_event.disconnect()

        self.__controls[btn]['bpm_txtbx'].value_enter_event.disconnect()
        self.__controls[btn]['bpm_txtbx'].broadcast_event.disconnect()

        self.note_ctrl_layout.removeItem(self.__controls[btn]['layout'])
        self.__del_layout(self.__controls[btn]['layout'])
        del self.__controls[btn]

        self.__update_gen_map()


    def __del_layout(self, layout):
        for i in reversed(range(layout.count())):
            child = layout.itemAt(i)
            layout.removeItem(child)

            child_layout = child.layout()
            child_widget = child.widget()

            if child_layout is not None:
                self.__del_layout(child_layout)
                child_layout.deleteLater()

            elif child_widget is not None:
                child_widget.deleteLater()
                
                
    def __spacing_broadcast_event(self, apply, value, txtbx):
        for btn in self.__controls:
            if self.__controls[btn]['spacing_txtbx'] == txtbx:
                continue
            
            self.__controls[btn]['spacing_txtbx'].apply_value(apply, value)


    def __angles_broadcast_event(self, apply, value, txtbx):
        for btn in self.__controls:
            if self.__controls[btn]['angles_txtbx'] == txtbx:
                continue
            
            self.__controls[btn]['angles_txtbx'].apply_value(apply, value)


    def __bpm_broadcast_event(self, apply, value, txtbx):
        for btn in self.__controls:
            if self.__controls[btn]['bpm_txtbx'] == txtbx:
                continue
            
            self.__controls[btn]['bpm_txtbx'].apply_value(apply, value)


    def __update_gen_map(self):
        cs        = float(self.cs_txtbx.text())
        ar        = float(self.ar_txtbx.text())

        # Handle DT/NC vs nomod setting
        rate_multiplier = 1.0 if (ar <= 10) else 1.5

        spacings  = np.asarray([ int(self.__controls[btn]['spacing_txtbx'].text()) for btn in self.__controls ])
        angles    = np.asarray([ int(self.__controls[btn]['angles_txtbx'].text()) for btn in self.__controls ])*math.pi/180
        times     = 15000/np.asarray([ int(self.__controls[btn]['bpm_txtbx'].text()) for btn in self.__controls ])*rate_multiplier
        num_notes = int(self.num_notes_txtbx.text())
        rotation  = int(self.rotation_txtbx.text())*math.pi/180

        gen_map, _ = OsuUtils.generate_pattern(rotation, spacings, times, angles, num_notes, 1)
        self.gen_map_event.emit(gen_map, cs, ar)

    
    def __generate_map(self):
        cs        = float(self.cs_txtbx.text())
        ar        = float(self.ar_txtbx.text())

        # Handle DT/NC vs nomod setting
        rate_multiplier = 1.0 if (ar <= 10) else 1.5

        spacings  = np.asarray([ int(self.__controls[btn]['spacing_txtbx'].text()) for btn in self.__controls ])
        angles    = np.asarray([ int(self.__controls[btn]['angles_txtbx'].text()) for btn in self.__controls ])*math.pi/180
        times     = 15000/np.asarray([ int(self.__controls[btn]['bpm_txtbx'].text()) for btn in self.__controls ])*rate_multiplier
        num_notes = int(self.num_notes_txtbx.text())
        rotation  = int(self.rotation_txtbx.text())*math.pi/180

        gen_map, _ = OsuUtils.generate_pattern(rotation, spacings, times, angles, num_notes, 1)
        ar = min(ar, 10) if (ar <= 10) else OsuUtils.ms_to_ar(OsuUtils.ar_to_ms(ar)*rate_multiplier)

        date = datetime.datetime.now()

        beatmap_data = textwrap.dedent(
            f"""\
            osu file format v14

            [General]
            AudioFilename: blank.mp3
            AudioLeadIn: 0
            PreviewTime: -1
            Countdown: 0
            SampleSet: Normal
            StackLeniency: 0
            Mode: 0
            LetterboxInBreaks: 1
            WidescreenStoryboard: 1

            [Editor]
            DistanceSpacing: 0.9
            BeatDivisor: 1
            GridSize: 32
            TimelineZoom: 0.2000059

            [Metadata]
            Title:unknown
            TitleUnicode:unknown
            Artist:abraker
            ArtistUnicode:abraker
            Creator:abraker
            Version:generated_{time.time()}
            Source:
            Tags:
            BeatmapID:0
            BeatmapSetID:0

            [Difficulty]
            HPDrainRate:8
            CircleSize:{cs}
            OverallDifficulty:10
            ApproachRate:{ar}
            SliderMultiplier:1.4
            SliderTickRate:1

            [Events]\
            """
        )

        # Generate notes
        audio_offset = -48  # ms

        for note in gen_map:
            beatmap_data += textwrap.dedent(
                f"""
                Sample,{int(note[0] + audio_offset*rate_multiplier)},3,"pluck.wav",100\
                """
            )

        beatmap_data += textwrap.dedent(
            f"""

            [TimingPoints]
            0,1000,4,1,1,100,1,0

            [HitObjects]\
            """
        )

        for note in gen_map:
            beatmap_data += textwrap.dedent(
                f"""
                {int(note[1])},{int(note[2])},{int(note[0] + audio_offset*rate_multiplier)},1,0,0:0:0:0:\
                """
            )

        # Remove leading whitespace
        beatmap_data = beatmap_data.split('\n')
        for i in range(len(beatmap_data)):
            beatmap_data[i] = beatmap_data[i].strip()
        self.beatmap_data = '\n'.join(beatmap_data)

        map_path = f'{AppConfig.cfg["osu_dir"]}/Songs/osu_play_analyzer'

        # Write to beatmap file
        os.makedirs(map_path, exist_ok=True)
        BeatmapIO.save_beatmap(self.beatmap_data, 'res/tmp.osu')
        map_md5 = hashlib.md5(open('res/tmp.osu', 'rb').read()).hexdigest()

        if not os.path.isfile(f'{map_path}/{map_md5}.osu'):
            shutil.copy2('res/tmp.osu', f'{map_path}/{map_md5}.osu')
        os.remove('res/tmp.osu')

        if not os.path.isfile(f'{map_path}/pluck.wav'):
            shutil.copy2('res/pluck.wav', f'{map_path}/pluck.wav')

        if not os.path.isfile(f'{map_path}/normal-hitnormal.wav'):
            shutil.copy2('res/blank.wav', f'{map_path}/normal-hitnormal.wav')


