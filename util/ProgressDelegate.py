from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt


# 进度条委托工具类
class ProgressDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        progress = index.data(Qt.EditRole)
        opt = QtWidgets.QStyleOptionProgressBar()
        opt.rect = option.rect
        opt.minimum = 0
        opt.maximum = 100
        opt.progress = int(progress)
        # opt.text = "%.3f" % progress
        # 隐藏文本展示
        opt.textVisible = False
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ProgressBar, opt, painter)
