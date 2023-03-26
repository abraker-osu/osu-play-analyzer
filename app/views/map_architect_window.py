import keyword
import os
import re
import threading
import sys
import time
import ctypes

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import pyqtgraph as pg


class MainUI(QtWidgets.QWidget):

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.resize(846, 552)

        self.gridLayout_2 = QtWidgets.QGridLayout(self)

        self.splitter = QtWidgets.QSplitter(self)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)

        self.layoutWidget = QtWidgets.QWidget(self.splitter)

        self.gridLayout = QtWidgets.QGridLayout(self.layoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)

        self.code_selection = QtWidgets.QTreeWidget(self.layoutWidget)
        self.code_selection.headerItem().setText(0, '1')
        self.code_selection.header().setVisible(False)
        self.gridLayout.addWidget(self.code_selection, 3, 0, 1, 2)

        self.script_filter = QtWidgets.QLineEdit(self.layoutWidget)
        self.gridLayout.addWidget(self.script_filter, 0, 0, 1, 2)

        self.search_mode = QtWidgets.QComboBox(self.layoutWidget)
        self.search_mode.addItem('')
        self.search_mode.addItem('')
        self.gridLayout.addWidget(self.search_mode, 1, 0, 1, 2)

        self.layoutWidget1 = QtWidgets.QWidget(self.splitter)

        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget1)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)

        self.title_editor = QtWidgets.QLineEdit()
        self.title_editor.setPlaceholderText('Script name')

        self.code_editor = QtWidgets.QPlainTextEdit(self.layoutWidget1)
        font = QtGui.QFont()
        font.setFamily('Courier New')
        self.code_editor.setFont(font)

        self.verticalLayout.addWidget(self.title_editor)
        self.verticalLayout.addWidget(self.code_editor)

        self.gridLayout_2.addWidget(self.splitter, 1, 0, 1, 1)

        self.setWindowTitle('PyQtGraph')
        self.script_filter.setPlaceholderText('Type to filter...')
        self.search_mode.setItemText(0, 'Title Search')
        self.search_mode.setItemText(1, 'Content Search')

        QtCore.QMetaObject.connectSlotsByName(self)


# based on https://github.com/art1415926535/PyQt5-syntax-highlighting


def charFormat(color, style='', background=None):
    """
    Return a QTextCharFormat with the given attributes.
    """
    _color = QtGui.QColor()
    
    if type(color) is not str:
        _color.setRgb(color[0], color[1], color[2])
    else:
        _color.setNamedColor(color)

    _format = QtGui.QTextCharFormat()
    _format.setForeground(_color)

    if 'bold'   in style: _format.setFontWeight(QtGui.QFont.Weight.Bold)
    if 'italic' in style: _format.setFontItalic(True)
    if background is not None:
        _format.setBackground(pg.mkColor(background))

    return _format


class DarkThemeColors:
    Red        = '#F44336'
    Pink       = '#F48FB1'
    Purple     = '#CE93D8'
    DeepPurple = '#B39DDB'
    Indigo     = '#9FA8DA'
    Blue       = '#90CAF9'
    LightBlue  = '#81D4FA'
    Cyan       = '#80DEEA'
    Teal       = '#80CBC4'
    Green      = '#A5D6A7'
    LightGreen = '#C5E1A5'
    Lime       = '#E6EE9C'
    Yellow     = '#FFF59D'
    Amber      = '#FFE082'
    Orange     = '#FFCC80'
    DeepOrange = '#FFAB91'
    Brown      = '#BCAAA4'
    Grey       = '#EEEEEE'
    BlueGrey   = '#B0BEC5'

DARK_STYLES = {
    'keyword'  : charFormat(DarkThemeColors.Blue,   'bold'),
    'operator' : charFormat(DarkThemeColors.Red,    'bold'),
    'brace'    : charFormat(DarkThemeColors.Purple),
    'defclass' : charFormat(DarkThemeColors.Indigo, 'bold'),
    'string'   : charFormat(DarkThemeColors.Amber),
    'string2'  : charFormat(DarkThemeColors.DeepPurple),
    'comment'  : charFormat(DarkThemeColors.Green,  'italic'),
    'self'     : charFormat(DarkThemeColors.Blue,   'bold'),
    'numbers'  : charFormat(DarkThemeColors.Teal),
}


class PythonHighlighter(QtGui.QSyntaxHighlighter):
    """
    Syntax highlighter for the Python language.
    """
    # Python keywords
    keywords = keyword.kwlist

    # Python operators
    operators = [
        r'=',
        # Comparison
        r'==', r'!=', r'<', r'<=', r'>', r'>=',
        # Arithmetic
        r'\+', r'-', r'\*', r'/', r'//', r'%', r'\*\*',
        # In-place
        r'\+=', r'-=', r'\*=', r'/=', r'\%=',
        # Bitwise
        r'\^', r'\|', r'&', r'~', r'>>', r'<<',
    ]

    # Python braces
    braces = [ r'\{', r'\}', r'\(', r'\)', r'\[', r'\]', ]

    def __init__(self, document):
        super().__init__(document)

        # Multi-line strings (expression, flag, style)
        self.tri_single = (QtCore.QRegularExpression("'''"), 1, 'string2')
        self.tri_double = (QtCore.QRegularExpression('"""'), 2, 'string2')

        self.rules = []

        # Keyword, operator, and brace rules
        self.rules += [ (r'\b%s\b' % w, 0, 'keyword') for w in PythonHighlighter.keywords ]
        self.rules += [ (o, 0, 'operator') for o in PythonHighlighter.operators ]
        self.rules += [ (b, 0, 'brace') for b in PythonHighlighter.braces ]

        # All other rules
        self.rules += [
            # 'self'
            (r'\bself\b', 0, 'self'),

            # 'def' followed by an identifier
            (r'\bdef\b\s*(\w+)', 1, 'defclass'),
            # 'class' followed by an identifier
            (r'\bclass\b\s*(\w+)', 1, 'defclass'),

            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', 0, 'numbers'),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, 'numbers'),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, 'numbers'),

            # Double-quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, 'string'),

            # Single-quoted string, possibly containing escape sequences
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, 'string'),

            # From '#' until a newline
            (r'#[^\n]*', 0, 'comment'),
        ]

        self.searchText = None


    def highlightBlock(self, text):
        """
        Apply syntax highlighting to the given block of text.
        """
        # Do other syntax formatting
        for expression, nth, format in self.rules.copy():
            format = DARK_STYLES[format]

            for n, match in enumerate(re.finditer(expression, text)):
                if n < nth: continue
                
                start  = match.start()
                length = match.end() - start
                self.setFormat(start, length, format)

        self.applySearchHighlight(text)
        self.setCurrentBlockState(0)

        # Do multi-line strings
        in_multiline = self.match_multiline(text, *self.tri_single)
        if not in_multiline:
            in_multiline = self.match_multiline(text, *self.tri_double)


    def match_multiline(self, text, delimiter, in_state, style):
        """
        Do highlighting of multi-line strings. 
        
        =========== ==========================================================
        delimiter   (QRegularExpression) for triple-single-quotes or 
                    triple-double-quotes
        in_state    (int) to represent the corresponding state changes when 
                    inside those strings. Returns True if we're still inside a
                    multi-line string when this function is finished.
        style       (str) representation of the kind of style to use
        =========== ==========================================================
        """
        # If inside triple-single quotes, start at 0
        if self.previousBlockState() == in_state:
            start = 0
            add   = 0
        # Otherwise, look for the delimiter on this line
        else:
            match = delimiter.match(text)
            start = match.capturedStart()

            # Move past this match
            add = match.capturedLength()

        # As long as there's a delimiter match on this line...
        while start >= 0:
            # Look for the ending delimiter
            match = delimiter.match(text, start + add)
            end   = match.capturedEnd()
            
            # Ending delimiter on this line?
            if end >= add:
                length = end - start + add + match.capturedLength()
                self.setCurrentBlockState(0)
            # No; multi-line string
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            
            # Apply formatting
            self.setFormat(start, length, DARK_STYLES[style])
            
            # Highlighting sits on top of this formatting
            # Look for the next match
            match = delimiter.match(text, start + length)
            start = match.capturedStart()

        self.applySearchHighlight(text)

        # Return True if still inside a multi-line string, False otherwise
        return (self.currentBlockState() == in_state)


    def applySearchHighlight(self, text):
        if not self.searchText:
            return
            
        palette    = QtWidgets.QApplication.instance().palette()
        fgnd_color = palette.color(palette.ColorGroup.Current, palette.ColorRole.Text).name()
        bgnd_color = palette.highlight().color().name()
        style = charFormat(fgnd_color, background=bgnd_color)

        for match in re.finditer(f'(?i){self.searchText}', text):
            start  = match.start()
            length = match.end() - start
            self.setFormat(start, length, style)


def unnestedDict(exDict):
    """
    Converts a dict-of-dicts to a singly nested dict for non-recursive parsing
    """
    out = {}
    for key, val in exDict.items():
        if isinstance(val, dict):
            out.update(unnestedDict(val))
        else:
            out[key] = val

    return out



class MapArchitectWindow(QtWidgets.QMainWindow):

    FOLDER_LOCATION = 'map_gen_scripts'

    gen_map_event = QtCore.pyqtSignal(str)

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.setWindowTitle('Map Architect')
        
        self.__ui = MainUI()
        self.setCentralWidget(self.__ui)
        
        self.__btn_save_code = QtWidgets.QPushButton('Save script')
        self.__btn_run_code  = QtWidgets.QPushButton('Run script')
        self.__code_layout   = QtWidgets.QGridLayout()
        self.__ui.code_editor.setLayout(self.__code_layout)

        self.__py_highlighter = PythonHighlighter(self.__ui.code_editor.document())
        
        app = QtWidgets.QApplication.instance()
        app.paletteChanged.connect(self.__update_theme)
        
        policy = QtWidgets.QSizePolicy.Policy.Expanding
        self.__code_layout.addItem(QtWidgets.QSpacerItem(100, 100, policy, policy), 0, 0)
        self.__code_layout.addWidget(self.__btn_run_code, 2, 2)
        self.__code_layout.addWidget(self.__btn_save_code, 2, 1)
        
        self.__old_text = self.__ui.code_editor.toPlainText()
        self.__cur_listener = None
        
        self.__item_cache  = []
        self.__script_list = self.__get_script_list()

        self.__setup_gui()


    def __setup_gui(self):
        self.__ui.code_selection.expandAll()

        self.resize(1000, 500)
        self.__ui.splitter.setSizes([ 250, 750 ])

        self.__ui.code_selection.currentItemChanged.connect(self.__show_file)
        self.__ui.code_editor.textChanged.connect(self.__on_text_change)
        self.__ui.search_mode.currentTextChanged.connect(self.__on_combo_changed)
        self.__btn_run_code.clicked.connect(lambda: self.__run_script())
        self.__btn_save_code.clicked.connect(lambda: self.__save_file())

        self.__ui.script_filter.setFocus()
        self.__ui.code_selection.setCurrentIndex(self.__ui.code_selection.model().index(0, 0))
        self.__on_combo_changed(self.__ui.search_mode.currentText())

        self.__load_script_list(self.__ui.code_selection.invisibleRootItem(), self.__script_list)

    
    def __on_combo_changed(self, search_type):
        if self.__cur_listener is not None:
            self.__cur_listener.disconnect()

        self.__cur_listener = self.__ui.script_filter.textChanged

        if search_type == 'Content Search':
            self.__cur_listener.connect(self.__filter_by_content)
        else:
            self.__py_highlighter.searchText = None
            self.__cur_listener.connect(self.__filter_by_title)

        # Fire on current text, too
        self.__cur_listener.emit(self.__ui.script_filter.text())


    def __on_text_change(self):
        """
        textChanged fires when the highlighter is reassigned the same document.
        Prevent this from showing "run edited code" by checking for actual
        content change
        """
        new_text = self.__ui.code_editor.toPlainText()
        if new_text != self.__old_text:
            self.__old_text = new_text


    def __filter_by_title(self, text):
        self.__show_examples_by_title(self.__get_matching_titles(text))
        self.__py_highlighter.setDocument(self.__ui.code_editor.document())


    def __filter_by_content(self, text=None):
        self.__py_highlighter.searchText = text
        
        # Need to reapply to current document
        self.__py_highlighter.setDocument(self.__ui.code_editor.document())

        text   = text.lower()
        titles = []
        
        # Don't filter very short strings
        for name, filepath in unnestedDict(self.__script_list).items():
            contents = self.__get_code_content(f'{MapArchitectWindow.FOLDER_LOCATION}\\{filepath}').lower()
            
            if text in contents:
                titles.append(name)
        
        self.__show_examples_by_title(titles)


    def __get_matching_titles(self, text, exDict=None, acceptAll=False):
        if exDict is None:
            exDict = self.__script_list

        text   = text.lower()
        titles = []

        for key, val in exDict.items():
            matched = acceptAll or text in key.lower()

            if isinstance(val, dict):
                titles.extend(self.__get_matching_titles(text, val, acceptAll=matched))
            elif matched:
                titles.append(key)

        return titles


    def __show_examples_by_title(self, titles):
        flag = QtWidgets.QTreeWidgetItemIterator.IteratorFlag.NoChildren
        tree_iter = QtWidgets.QTreeWidgetItemIterator(self.__ui.code_selection, flag)
        item = tree_iter.value()

        while item is not None:
            parent = item.parent()
            item.setHidden(not (item.childCount() or item.text(0) in titles))

            # If all children of a parent are gone, hide it
            if parent:
                hide_parent = True
                for ii in range(parent.childCount()):
                    if not parent.child(ii).isHidden():
                        hide_parent = False
                        break

                parent.setHidden(hide_parent)

            tree_iter += 1
            item = tree_iter.value()


    def __update_theme(self):
        self.__py_highlighter = PythonHighlighter(self.__ui.code_editor.document())


    def __get_script_list(self):
        data = { }

        results = os.walk(MapArchitectWindow.FOLDER_LOCATION, topdown=True, onerror=None, followlinks=False)
        for dirpath, _, filenames in results:
            dirpath = os.path.normpath(dirpath)

            # Take out the root folder name
            dirpath = dirpath.split('\\')
            dirpath = '\\'.join(dirpath[1:])

            data_nest = data
            for dir in dirpath.split('\\'):
                if not dir: continue
                if not dir in data_nest:
                    data_nest[dir] = { }

                data_nest = data_nest[dir]
                dirpath += '\\'

            for filename in filenames:
                data_nest[filename.split('.')[0]] = f'{dirpath}{filename}'

        return data


    def __load_script_list(self, root, scripts):
        item  = self.__ui.code_selection.currentItem()
        index = None

        if item is not None:
            index = self.__ui.code_selection.indexFromItem(item)
            item  = None

        for key, val in scripts.items():
            item = QtWidgets.QTreeWidgetItem([ key ])

            # PyQt 4.9.6 no longer keeps references to these wrappers,
            # so we need to make an explicit reference or else the .file
            # attribute will disappear.
            self.__item_cache.append(item)
           
            if isinstance(val, dict):
                self.__load_script_list(item, val)
            else:
                item.path = val

            # Add only if the name does not exist
            if not any([ root.child(i).text(0) == key for i in range(root.childCount()) ]):
                root.addChild(item)

        if index is not None:
            item = self.__ui.code_selection.itemFromIndex(index)
            self.__ui.code_selection.setCurrentItem(item)


    def __current_filepath(self):
        item = self.__ui.code_selection.currentItem()

        try: return item.path
        except AttributeError:
            # This happens if the user clicks on a folder in the QTreeWidget
            return None

 
    def __show_file(self):
        script_pathname = self.__current_filepath()
        if script_pathname is None:
            # This happens if the user clicks on a folder in the QTreeWidget
            return

        file_pathname = f'{MapArchitectWindow.FOLDER_LOCATION}\\{script_pathname}'
        
        self.__ui.code_editor.setPlainText(self.__get_code_content(file_pathname))
        self.__ui.title_editor.setText(script_pathname)


    def __save_file(self):
        script_pathname = self.__ui.title_editor.text()
        file_pathname   = f'{MapArchitectWindow.FOLDER_LOCATION}/{script_pathname}'
        file_path       = os.path.dirname(file_pathname)

        if not os.path.exists(file_path):
            os.makedirs(file_path)

        if len(script_pathname) == 0:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msg.setText('Unable to save: Please name the script!\nUse the "Script name" edit box above')
            msg.setWindowTitle('Error saving file')
            msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
            msg.exec_()
            return

        try: 
            with open(file_pathname, 'w') as f:
                f.write(self.__ui.code_editor.toPlainText())
        except PermissionError:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            msg.setText('Unable to save: Permission error!')
            msg.setWindowTitle('Error saving file')
            msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
            msg.exec_()
            return

        self.__script_list = self.__get_script_list()
        self.__load_script_list(self.__ui.code_selection.invisibleRootItem(), self.__script_list)


    def __run_script(self):
        # Add paths to utilities for map generation
        add_paths = []

        if getattr(sys, 'frozen', False):
            # Indication that this is being run via the pyinstaller exe
            add_paths.append(os.getcwd().replace("\\", "/"))
        else:
            # Indication that this is being run via python directly
            script_path = os.path.abspath(os.path.dirname(__file__))
            path        = os.path.dirname(os.path.dirname(script_path)).replace('\\', '/')

            add_paths.append(f'{path}/map_generator')
            add_paths.append(f'{path}/app/misc')

        add_paths = ''.join([ f'sys.path.append("{add_path}")\n' for add_path in add_paths ])

        code = \
        'import sys\n' \
        f'{add_paths}' \
        f'{self.__ui.code_editor.toPlainText()}'

        # Need to to insert `gen_map_event` so that there is a way
        # to display the generated map in Map Display > Generated
        tmp_globals = dict(globals())
        tmp_globals['gen_map_event'] = self.gen_map_event

        # Set a timeout of 5 seconds
        thread = threading.Thread(target=lambda: exec(code, tmp_globals))
        thread.setDaemon(True)
        thread.start()

        # Wait 5 seconds or until thread finishes
        start = time.time()
        while thread.is_alive():
            time.sleep(0.001)
            if time.time() - start >= 5:
                break

        if thread.is_alive():
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msg.setWindowTitle('Warning')
            msg.setText('Script timed out')
            msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
            msg.exec_()
            
            # Thanks https://docs.python.org/3/c-api/init.html?highlight=pythreadstate_setasyncexc#c.PyThreadState_SetAsyncExc
            # Thanks https://stackoverflow.com/questions/65089503/raising-exceptions-in-a-thread
            # Allows to force terminate a thread by causing it to raise an exception
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), ctypes.py_object(Exception))
            return


    def __get_code_content(self, pathname):
        if pathname is None:
            self.__ui.code_editor.clear()
            return

        with open(pathname, 'r') as f:
            text = f.read()

        return text


    def keyPressEvent(self, event):
        ret = super().keyPressEvent(event)
        if not QtCore.Qt.KeyboardModifier.ControlModifier & event.modifiers():
            return ret
        
        key = event.key()

        # Allow quick navigate to search
        if key == QtCore.Qt.Key.Key_F:
            self.__ui.script_filter.setFocus()
            event.accept()
            return

        if key == QtCore.Qt.Key.Key_S:
            self.__save_file()
            event.accept()
            return
       
        font = self.__ui.code_editor.font()
        old_size = font.pointSize()
        
        if key == QtCore.Qt.Key.Key_Plus or key == QtCore.Qt.Key.Key_Equal:
            font.setPointSize(int(old_size + max(old_size*.15, 1)))
        elif key == QtCore.Qt.Key.Key_Minus or key == QtCore.Qt.Key.Key_Underscore:
            newSize = old_size - max(old_size*.15, 1)
            font.setPointSize(int(max(newSize, 1)))
        elif key == QtCore.Qt.Key.Key_0:
            # Reset to original size
            font.setPointSize(10)
        else:
            return ret
       
        self.__ui.code_editor.setFont(font)

        event.accept()


if __name__ == '__main__':
    app = pg.mkQApp()
    window = MapArchitectWindow()
    pg.exec()
