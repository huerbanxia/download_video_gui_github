from HisUrlDialogView import Ui_Dialog
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from FormView import Ui_dialog
from util.HttpClient import HttpClient
from util.Worker import Worker
from util.ProgressDelegate import ProgressDelegate
import configparser
import os
from urllib import parse
import uuid
import re


class HisUrlDialog(QWidget, Ui_Dialog):
    # 确定选择信号
    selectItemSign = pyqtSignal(str)

    def __init__(self, icon: QIcon, title: str, his_url_file_path: str):
        super().__init__()
        # 设置图标
        self.icon = icon
        self.setWindowIcon(self.icon)
        # 标题
        self.setWindowTitle(title)
        # 数据集声明
        self.data = []
        # 历史url文件保存路径
        self.his_url_file_path = his_url_file_path

        self.listViewModel = None

    def init_list(self):
        # 实例化列表模型，添加数据
        self.listViewModel = QStringListModel()
        # 读取文件获取历史列表
        url_list = []
        if os.path.lexists(self.his_url_file_path):
            with open(file=self.his_url_file_path, mode='r', encoding='utf-8') as file:
                lines = file.readlines()
                for url in lines:
                    url_list.append(url.replace("\n", ""))
        self.data = url_list
        self.listViewModel.setStringList(self.data)
        # 初始化控件
        self.listView.setModel(self.listViewModel)

    # 确定按钮点击事件 发送信号并关闭对话框
    def ok_btn_click(self):
        selected = self.listView.selectedIndexes()
        if len(selected) == 0:
            QMessageBox.warning(self, "警告", "请选择一条数据!")
            return
        # 发送信号更新文本框
        self.selectItemSign.emit(self.data[selected[0].row()])
        # 关闭对话框
        self.close()

    # 取消按钮
    def cancel_btn_click(self):
        self.close()

    # 删除按钮点击事件
    def delete_row_btn_click(self):
        selected = self.listView.selectedIndexes()
        if len(selected) == 0:
            QMessageBox.warning(self, "警告", "请选择一条数据!")
            return
        index = selected[0].row()
        self.data.pop(index)
        self.listViewModel.removeRow(index)

    # 清空按钮点击事件
    def clear_rows_btn_click(self):
        self.data = []
        self.listViewModel.setStringList(self.data)

    # 保存按钮点击事件
    def save_data_to_file_btn_click(self):
        # 创建一个问答框，注意是Question
        box = QMessageBox(QMessageBox.Question, '保存数据', '确定要保存数据吗?')
        # 添加按钮，可用中文
        yes = box.addButton('确定', QMessageBox.YesRole)
        cancel = box.addButton('取消', QMessageBox.RejectRole)
        # 设置消息框中内容前面的图标
        box.setWindowIcon(self.icon)
        # 显示该问答框
        box.exec_()
        # 判断分支选择
        if box.clickedButton() == yes:
            file = open(self.his_url_file_path, 'w', encoding='utf-8')
            # 判断数据
            if len(self.data) == 0:
                # 清空文件
                file.seek(0)
                file.truncate()
            else:
                # 逐行写入数据
                for info in self.data:
                    file.write(info + '\n')
            # 关闭文件
            file.close()
            QMessageBox.information(self, "提示", "保存成功")
