"""
Provides a way to generate maps for data collection. This is nowhere close to a beatmap editor and provides basic functionality
to generate repeating patterns and alter maps.

Features:
- Inserts a repeating pattern given BPM, spacing and angle, number of notes, and rotation
- Allows BPM, spacing and angle to be changed throughout generated pattern based on modulation
- Allows to change map rate
"""
import math
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui

from app.misc.osu_utils import OsuUtils



class _ValueLineEdit(QtGui.QLineEdit):

    def __init__(self, *args, **kwargs):
        QtGui.QLineEdit.__init__(self, *args, **kwargs)
        

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Enter and event.key() == QtCore.Qt.Key_Return:
            event.accept()

            StrToVal = int if type(self.validator()) is QtGui.QIntValidator else float
            
            value = StrToVal(self.text())
            value = self.validate(value)

            if value == StrToVal(self.text()):
                return
            
            self.setText(str(value))
            self.returnPressed.emit()
            return
        
        QtGui.QLineEdit.keyPressEvent(self, event)


    def wheelEvent(self, event):
        event.accept()

        StrToVal = int if type(self.validator()) is QtGui.QIntValidator else float
        
        # Done through QGuiApplication instead of keyEvent to allow ctrl modifier to work when window is unfocused
        ctrl_is_pressed = QtGui.QGuiApplication.queryKeyboardModifiers() & QtCore.Qt.ControlModifier

        delta_mul = 10 if ctrl_is_pressed else 1
        delta_mul *= 1 if StrToVal == int else 0.1

        delta = 1*delta_mul if event.angleDelta().y() > 0 else -1*delta_mul

        value = round(StrToVal(self.text()) + delta, 1)
        value = self.validate(value)

        if value == StrToVal(self.text()):
            return
        
        self.setText(str(value))
        self.returnPressed.emit()
        

    def validate(self, value):
        validator = self.validator()
        value = min(validator.top(), max(validator.bottom(), value))
        return value



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

        self.data_loaded = False
        self.controls = {}

        self.__init_components()
        self.__build_layout()
        self.__configure_components()
        self.__connect_signals()

        self.__add_control()


    def __init_components(self):        
        self.spacing_label = QtGui.QLabel('Spacings:')
        self.angles_label  = QtGui.QLabel('Angles:')
        self.bpm_label     = QtGui.QLabel('BPMs:')
        self.label_layout  = QtGui.QVBoxLayout()

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

        self.ctrl_area = QtGui.QWidget()
        self.ctrl_scroll_area = QtGui.QScrollArea()
        self.note_ctrl_layout = QtGui.QHBoxLayout()
        self.map_ctrl_layout = QtGui.QHBoxLayout()

        self.ctrl_layout = QtGui.QHBoxLayout()
        self.add_btn = QtGui.QPushButton('Add')

        self.main_widget = QtGui.QWidget()
        self.main_layout = QtGui.QVBoxLayout(self.main_widget)


    def __build_layout(self):        
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
        
        self.main_layout.addLayout(self.ctrl_layout)
        self.main_layout.addLayout(self.map_ctrl_layout)
        self.main_layout.addWidget(self.add_btn)

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


    def __connect_signals(self):
        self.add_btn.clicked.connect(self.__add_control)

        self.num_notes_txtbx.returnPressed.connect(lambda txtbx=self.num_notes_txtbx: self.__num_notes_enter_event(txtbx))
        self.rotation_txtbx.returnPressed.connect(lambda txtbx=self.rotation_txtbx: self.__rotation_enter_event(txtbx))
        self.cs_txtbx.returnPressed.connect(lambda txtbx=self.cs_txtbx: self.__cs_enter_event(txtbx))
        self.ar_txtbx.returnPressed.connect(lambda txtbx=self.ar_txtbx: self.__ar_enter_event(txtbx))


    def notify_data_loaded(self):
        # To keep track of whether or not data has been loaded in the map display window
        # If data is loaded, the user will be warned; They will need to agree for it to be displayed in the map display window
        self.data_loaded = True


    def __add_control(self):
        spacing_txtbx = _ValueLineEdit()
        angles_txtbx  = _ValueLineEdit()
        bpm_txtbx     = _ValueLineEdit()
        remove_btn    = QtGui.QPushButton('Remove')

        spacing_txtbx.setValidator(QtGui.QIntValidator(0, 512))
        angles_txtbx.setValidator(QtGui.QIntValidator(-180, 180))
        bpm_txtbx.setValidator(QtGui.QIntValidator(0, 1000))

        spacing_txtbx.setText('100')
        angles_txtbx.setText('90')
        bpm_txtbx.setText('180')

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

        spacing_txtbx.returnPressed.connect(lambda txtbx=spacing_txtbx: self.__spacing_enter_event(txtbx))
        angles_txtbx.returnPressed.connect(lambda txtbx=angles_txtbx: self.__angles_enter_event(txtbx))
        bpm_txtbx.returnPressed.connect(lambda txtbx=bpm_txtbx: self.__bpm_enter_event(txtbx))

        self.controls[remove_btn] = ctrl_layout

        self.__update_gen_map()


    def __remove_control(self, btn):
        if len(self.controls) == 1:
            return

        self.note_ctrl_layout.removeItem(self.controls[btn])
        self.__del_layout(self.controls[btn])
        del self.controls[btn]

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


    def __num_notes_enter_event(self, txtbx):
        num_notes = int(txtbx.text())
        print(f'Num notes entered: {num_notes}')
        self.__update_gen_map()

    
    def __rotation_enter_event(self, txtbx):
        rotation = int(txtbx.text())
        print(f'Rotation entered: {rotation}')
        self.__update_gen_map()


    def __cs_enter_event(self, txtbx):
        cs = float(txtbx.text())
        print(f'CS entered: {cs}')
        self.__update_gen_map()


    def __ar_enter_event(self, txtbx):
        ar = float(txtbx.text())
        print(f'AR entered: {ar}')
        self.__update_gen_map()


    def __spacing_enter_event(self, txtbx):
        spacing = int(txtbx.text())
        print(f'Spacing entered: {spacing}')
        self.__update_gen_map()


    def __angles_enter_event(self, txtbx):
        angles = int(txtbx.text())
        print(f'Angles entered: {angles}')
        self.__update_gen_map()

    
    def __bpm_enter_event(self, txtbx):
        bpm = int(txtbx.text())
        print(f'BPM entered: {bpm}')
        self.__update_gen_map()


    def __update_gen_map(self):
        cs        = float(self.cs_txtbx.text())
        ar        = float(self.ar_txtbx.text())

        # Handle DT/NC vs nomod setting
        rate_multiplier = 1.0 if (ar <= 10) else 1.5

        spacings  = np.asarray([ int(self.controls[btn].itemAt(0).widget().text()) for btn in self.controls ])
        angles    = np.asarray([ int(self.controls[btn].itemAt(1).widget().text()) for btn in self.controls ])*math.pi/180
        times     = 15000/np.asarray([ int(self.controls[btn].itemAt(2).widget().text()) for btn in self.controls ])*rate_multiplier
        num_notes = int(self.num_notes_txtbx.text())
        rotation  = int(self.rotation_txtbx.text())*math.pi/180

        gen_map, _ = OsuUtils.generate_pattern(rotation, spacings, times, angles, num_notes, 1)
        self.gen_map_event.emit(gen_map, cs, ar)

        ar = min(ar, 10) if (ar <= 10) else OsuUtils.ms_to_ar(OsuUtils.ar_to_ms(ar)*rate_multiplier)
