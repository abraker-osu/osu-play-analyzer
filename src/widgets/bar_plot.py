import numpy as np

import pyqtgraph
import PyQt6

__all__ = ['BarGraphItem']


class BarGraphItem(pyqtgraph.GraphicsObject):

    class __ConfigException(Exception):

        def __init__(self, msg):
            Exception.__init__(self, msg)


    def __init__(self, **opts):
        """
        Valid keyword options are:
        x, x0, x1, y, y0, y1, width, height, pen, brush

        x specifies the x-position of the center of the bar.
        x0, x1 specify left and right edges of the bar, respectively.
        width specifies distance from x0 to x1.
        You may specify any combination:

            x, width
            x0, width
            x1, width
            x0, x1

        Likewise y, y0, y1, and height.
        If only height is specified, then y0 will be set to 0

        Example uses:

            BarGraphItem(x=range(5), height=[1,5,2,4,3], width=0.5)
        """
        pyqtgraph.GraphicsObject.__init__(self)

        self.opts = dict(
            x=None,
            y=None,
            x0=None,
            y0=None,
            x1=None,
            y1=None,
            name=None,
            height=None,
            width=None,
            pen=None,
            brush=None,
            pens=None,
            brushes=None,
        )

        self._shape = None
        self.picture = None
        self.setOpts(**opts)


    def setOpts(self, **opts):
        self.opts.update(opts)

        self.picture = None
        self._shape  = None

        self.update()
        self.informViewBoundsChanged()


    def drawPicture(self):
        self.picture = PyQt6.QtGui.QPicture()
        self._shape = PyQt6.QtGui.QPainterPath()

        p = PyQt6.QtGui.QPainter(self.picture)

        pen  = self.opts['pen']
        pens = self.opts['pens']

        if pen is None and pens is None:
            pen = (128, 128, 128)

        brush   = self.opts['brush']
        brushes = self.opts['brushes']

        if brush is None and brushes is None:
            brush = (128, 128, 128)

        def asarray(x):
            if x is None or np.isscalar(x) or isinstance(x, np.ndarray):
                return x

            return np.array(x)

        x     = asarray(self.opts.get('x'))
        x0    = asarray(self.opts.get('x0'))
        x1    = asarray(self.opts.get('x1'))
        width = asarray(self.opts.get('width'))

        if x0 is None:
            if width is None:
                raise BarGraphItem.__ConfigException('must specify either x0 or width')

            if x1 is not None:
                x0 = x1 - width
            elif x is not None:
                x0 = x - width/2.
            else:
                raise BarGraphItem.__ConfigException('must specify at least one of x, x0, or x1')

        if width is None:
            if x1 is None:
                raise BarGraphItem.__ConfigException('must specify either x1 or width')

            width = x1 - x0

        y      = asarray(self.opts.get('y'))
        y0     = asarray(self.opts.get('y0'))
        y1     = asarray(self.opts.get('y1'))
        height = asarray(self.opts.get('height'))

        if y0 is None:
            if height is None:
                y0 = 0
            elif y1 is not None:
                y0 = y1 - height
            elif y is not None:
                y0 = y - height/2.
            else:
                y0 = 0

        if height is None:
            if y1 is None:
                raise BarGraphItem.__ConfigException('must specify either y1 or height')

            height = y1 - y0

        p.setPen(pyqtgraph.mkPen(pen))
        p.setBrush(pyqtgraph.mkBrush(brush))

        for i in range(len(x0 if not np.isscalar(x0) else y0)):
            if pens    is not None: p.setPen(pyqtgraph.mkPen(pens[min(i, len(pens) - 1)]))
            if brushes is not None: p.setBrush(pyqtgraph.mkBrush(brushes[min(i, len(brushes) - 1)]))

            x = x0     if np.isscalar(x0)     else x0[i]
            y = y0     if np.isscalar(y0)     else y0[i]
            w = width  if np.isscalar(width)  else width[i]
            h = height if np.isscalar(height) else height[i]

            rect = PyQt6.QtCore.QRectF(x + w/2, y, w, h)

            p.drawRect(rect)
            self._shape.addRect(rect)

        p.end()
        self.prepareGeometryChange()


    def setData(self, x, y, width=1, brush='r'):
        self.setOpts(x=x, height=y, width=width, brushes=brush)


    def paint(self, p, *args):
        try:
            if self.picture is None:
                self.drawPicture()

            self.picture.play(p)
        except BarGraphItem.__ConfigException as e:
            print(str(e))


    def boundingRect(self):
        try:
            if self.picture is None:
                self.drawPicture()
        except BarGraphItem.__ConfigException as e:
            print(str(e))

        return PyQt6.QtCore.QRectF(self.picture.boundingRect())



    def shape(self):
        try:
            if self.picture is None:
                self.drawPicture()
        except BarGraphItem.__ConfigException as e:
            print(str(e))

        return self._shape



    def implements(self, interface=None):
        ints = ['plotData']
        if interface is None:
            return ints

        return interface in ints


    def name(self):
        return self.opts.get('name', None)


    def getData(self):
        return self.opts.get('x'), self.opts.get('height')
