import numpy as np

import PyQt6
import pyqtgraph

from osu_interfaces import Mod
from osu_analysis import StdScoreData

from misc.utils import Utils


class AimGraph(PyQt6.QtWidgets.QWidget):

    SCALE = 3.0
    SIZE = 140*SCALE
    DEV_WIDTH = 64 + 4*SCALE

    # Construct a unit radius circle for a graph
    class HitCircle(PyQt6.QtWidgets.QGraphicsObject):
        def __init__(self, center=(0.0, 0.0), radius=1.0, pen=pyqtgraph.mkPen(color=(255, 255, 255, 255), width=0.5)):
            PyQt6.QtWidgets.QGraphicsObject.__init__(self)
            self.center = center
            self.radius = radius
            self.pen = pen


        def boundingRect(self):
            rect = PyQt6.QtCore.QRectF(0, 0, 2*self.radius, 2*self.radius)
            rect.moveCenter(PyQt6.QtCore.QPointF(*self.center))
            return rect


        def paint(self, painter, option, widget):
            painter.setPen(self.pen)
            painter.drawEllipse(self.boundingRect())


    def __init__(self, parent=None):
        PyQt6.QtWidgets.QWidget.__init__(self, parent)

        self.setWindowTitle('Aim visualization')
        #self.setSizePolicy(QtGui.QSizePolicy.Policy.Minimum, QtGui.QSizePolicy.Policy.Minimum)
        self.setMaximumSize(PyQt6.QtCore.QSize(int(AimGraph.SIZE + AimGraph.DEV_WIDTH + 1), int(AimGraph.SIZE + AimGraph.DEV_WIDTH + 32 + 1)))

        self.main_layout = PyQt6.QtWidgets.QGridLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(1)

        self.win_hits = pyqtgraph.PlotWidget(show=False, title='Hit visualization')
        self.win_hits.setWindowTitle('osu! Aim Tool Hit Visualization')
        self.win_hits.setFixedSize(int(AimGraph.SIZE), int(AimGraph.SIZE + 32))

        # Scatter plot for aim data
        self.plot_hits = self.win_hits.plot(title='Hit scatter')
        self.plot_misses = self.win_hits.plot(title='Miss scatter')
        self.win_hits.hideAxis('left')
        self.win_hits.hideAxis('bottom')
        self.win_hits.setXRange(-AimGraph.SIZE/2, AimGraph.SIZE/2)
        self.win_hits.setYRange(-AimGraph.SIZE/2, AimGraph.SIZE/2)
        self.win_hits.getViewBox().setMouseEnabled(x=False, y=False)
        self.win_hits.enableAutoRange(axis='x', enable=False)
        self.win_hits.enableAutoRange(axis='y', enable=False)

        # Hit circle visualization
        self.circle_item = AimGraph.HitCircle((0, 0))
        self.win_hits.addItem(self.circle_item)

        # X-axis deviation histogram
        self.dev_x = pyqtgraph.PlotWidget(show=False)
        self.dev_x.getViewBox().setMouseEnabled(x=False, y=False)
        self.dev_x.enableAutoRange(axis='x', enable=False)
        self.dev_x.enableAutoRange(axis='y', enable=True)
        self.dev_x.hideAxis('left')
        self.dev_x.showAxis('bottom')
        self.dev_x.setFixedHeight(int(64 + 4*AimGraph.SCALE))
        self.dev_x.setXRange(-AimGraph.SIZE/2, AimGraph.SIZE/2)

        # Y-axis deviation histogram
        self.dev_y = pyqtgraph.PlotWidget(show=False)
        self.dev_y.getViewBox().setMouseEnabled(x=False, y=False)
        self.dev_y.enableAutoRange(axis='x', enable=True)
        self.dev_y.enableAutoRange(axis='y', enable=False)
        self.dev_y.hideAxis('bottom')
        self.dev_y.hideAxis('left')
        self.dev_y.showAxis('right')
        self.dev_y.setFixedWidth(int(64 + 4*AimGraph.SCALE))
        self.dev_y.setYRange(-AimGraph.SIZE/2, AimGraph.SIZE/2)

        '''
        # Covariance vectors scaled to 95% confidence interval
        self.lambda1 = pyqtgraph.ArrowItem(tailWidth=1.5, headLen=15, pxMode=False, pen=None, brush=(255, 255, 0, 100))
        self.lambda2 = pyqtgraph.ArrowItem(tailWidth=1.5, headLen=15, pxMode=False, pen=None, brush=(255, 255, 0, 100))
        self.lambda1.setPos(0, 0)
        self.lambda2.setPos(0, 0)
        self.win_hits.addItem(self.lambda1)
        self.win_hits.addItem(self.lambda2)

        # Deviation covariance area scaled to 95% confidence interval
        self.cov_area = pyqtgraph.QtGui.QGraphicsEllipseItem(0, 0, 0, 0)
        self.cov_area.setPen(pyqtgraph.mkPen((0, 0, 0, 0)))
        self.cov_area.setBrush(pyqtgraph.mkBrush((133, 245, 255, 50)))
        self.win_hits.addItem(self.cov_area)
        '''

        # Cov area metrics
        self.cov_area_metrics = pyqtgraph.TextItem('', anchor=(0, 0), )
        self.cov_area_metrics.setPos(int(-AimGraph.SIZE/2), int(AimGraph.SIZE/2))
        self.win_hits.addItem(self.cov_area_metrics)

        self.main_layout.addWidget(self.win_hits, 0, 0)
        self.main_layout.addWidget(self.dev_x, 1, 0)
        self.main_layout.addWidget(self.dev_y, 0, 1)


    def set_cs(self, cs):
        # From https://github.com/ppy/osu/blob/master/osu.Game.Rulesets.Osu/Objects/OsuHitObject.cs#L137
        cs_px = (108.8 - 8.96*cs)/2

        self.circle_item.radius = cs_px*AimGraph.SCALE
        self.win_hits.update()


    def calc_cov_area(self, x, y):
        # Plot covariance vectors
        # ||lambda1|| = x-dev', ||lambda2|| = y-dev'
        cov_matrix = np.cov(x, y)
        eigen_values, eigen_vectors = np.linalg.eig(cov_matrix)

        angle_lambda1 = np.arctan2(eigen_vectors[0, 1], eigen_vectors[0, 0])*180/np.pi
        angle_lambda2 = np.arctan2(eigen_vectors[1, 1], eigen_vectors[1, 0])*180/np.pi

        x_dev = 2*eigen_values[0]**0.5  # 95% confidence interval
        y_dev = 2*eigen_values[1]**0.5  # 95% confidence interval

        return angle_lambda1, angle_lambda2, x_dev, y_dev


    @Utils.benchmark(__name__)
    def plot_data(self, play_data):
        if play_data.shape[0] == 0:
            return

        cs = play_data['CS'].values[0]

        mods = Mod(int(play_data.index.get_level_values(2)[0]))
        if mods.has_mod(Mod.HardRock): cs *= 1.3
        if mods.has_mod(Mod.Easy):     cs *= 0.5

        cs = min(cs, 10)
        self.set_cs(cs)

        data_filter = (play_data['TYPE_HIT'] == StdScoreData.TYPE_HITP)
        data_hits = play_data[data_filter]

        data_filter = \
            (play_data['TYPE_HIT'] == StdScoreData.TYPE_MISS) & \
            (play_data['TYPE_MAP'] == StdScoreData.ACTION_PRESS)
        data_misses = play_data[data_filter]

        offsets_hits  = data_hits[[ 'X_HIT', 'Y_HIT' ]].values - data_hits[[ 'X_MAP', 'Y_MAP' ]].values
        offsets_misses = data_misses[[ 'X_HIT', 'Y_HIT' ]].values - data_misses[[ 'X_MAP', 'Y_MAP' ]].values

        self.plot_xy_data(offsets_hits, offsets_misses)


    def plot_xy_data(self, offsets_hits, offsets_misses):
        scaled_aim_x_offsets = offsets_misses[:, 0]*AimGraph.SCALE
        scaled_aim_y_offsets = offsets_misses[:, 1]*AimGraph.SCALE
        self.plot_misses.setData(scaled_aim_x_offsets, scaled_aim_y_offsets, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=(200, 50, 50, 200))

        scaled_aim_x_offsets = offsets_hits[:, 0]*AimGraph.SCALE
        scaled_aim_y_offsets = offsets_hits[:, 1]*AimGraph.SCALE
        self.plot_hits.setData(scaled_aim_x_offsets, scaled_aim_y_offsets, pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush=(100, 100, 255, 200))

        '''
        angle_lambda1, angle_lambda2, scaled_x_dev, scaled_y_dev = self.calc_cov_area(scaled_aim_x_offsets, scaled_aim_y_offsets)

        self.lambda1.setStyle(angle=(-angle_lambda1 - 180), tailLen=scaled_x_dev)
        self.lambda2.setStyle(angle=(-angle_lambda2 - 180), tailLen=scaled_y_dev)

        lambda1_len = self.lambda1.opts['tailLen'] + self.lambda1.opts['headLen']
        lambda2_len = self.lambda2.opts['tailLen'] + self.lambda2.opts['headLen']

        self.lambda1.setPos(
            -lambda1_len*math.cos(self.lambda1.opts['angle'] * math.pi/180),
            -lambda1_len*math.sin(self.lambda1.opts['angle'] * math.pi/180)
        )

        self.lambda2.setPos(
            -lambda2_len*math.cos(self.lambda2.opts['angle'] * math.pi/180),
            -lambda2_len*math.sin(self.lambda2.opts['angle'] * math.pi/180),
        )


        # Plot covariance area
        self.cov_area.setRect(-scaled_x_dev, -scaled_y_dev, 2*scaled_x_dev, 2*scaled_y_dev)
        self.cov_area.setRotation(-angle_lambda1)
        '''

        # Plot a histogram for x-dev
        y, x = np.histogram(scaled_aim_x_offsets, bins=np.linspace(-AimGraph.SIZE/2, AimGraph.SIZE/2, int(AimGraph.SIZE/5)))
        self.dev_x.clearPlots()
        self.dev_x.plot(x, y, stepMode='center', fillLevel=0, fillOutline=True, brush=(0, 0, 255, 150))

        # Plot a histogram for y-dev
        y, x = np.histogram(scaled_aim_y_offsets, bins=np.linspace(-AimGraph.SIZE/2, AimGraph.SIZE/2, int(AimGraph.SIZE/5)))
        self.dev_y.clearPlots()
        plot = self.dev_y.plot(x, y, stepMode='center', fillLevel=0, fillOutline=True, brush=(0, 0, 255, 150))
        plot.setRotation(90)

        '''
        # Update metrics
        angle_lambda1, angle_lambda2, x_dev, y_dev = self.calc_cov_area(offsets_hits[:, 0], offsets_hits[:, 1])
        '''

        #fc_conf_lvl = 1 - 1/offsets_hits[:, 0].shape[0]
        #conf_interval = math.sqrt(2)*scipy.special.erfinv(fc_conf_lvl)

        self.cov_area_metrics.setText(
            #f'θx-dev span: {2*x_dev:.2f} o!px @ 95% conf\n'
            #f'θy-dev span: {2*y_dev:.2f} o!px @ 95% conf\n'
            #f'θ-dev: {angle_lambda1:.2f}°\n'
            #f'\n'
            f'x-dev span: {2*2*np.std(offsets_hits[:, 0]):.2f} o!px @ 95% conf\n'
            f'y-dev span: {2*2*np.std(offsets_hits[:, 1]):.2f} o!px @ 95% conf\n'
            #f'x-dev span: {2*conf_interval*np.std(offsets_hits[:, 0]):.2f} o!px @ FC conf\n'
            #f'y-dev span: {2*conf_interval*np.std(offsets_hits[:, 1]):.2f} o!px @ FC conf\n'
            f'cs_px: {2*self.circle_item.radius/AimGraph.SCALE:.2f} o!px'
        )
