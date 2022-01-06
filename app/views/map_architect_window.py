"""
Provides a way to generate maps for data collection. This is nowhere close to a beatmap editor and provides basic functionality
to generate repeating patterns and alter maps.

Features:
- Inserts a repeating pattern given BPM, spacing and angle, number of notes, and rotation
- Allows BPM, spacing and angle to be changed throughout generated pattern based on modulation
- Allows to change map rate
"""
from pyqtgraph.Qt import QtGui


class MapArchitectWindow(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.setWindowTitle('Map architect')

        self.data_loaded = False
        self.layout = QtGui.QVBoxLayout(self)


    def notify_data_loaded(self):
        # To keep track of whether or not data has been loaded in the map display window
        # If data is loaded, the user will be warned; They will need to agree for it to be displayed in the map display window
        self.data_loaded = True