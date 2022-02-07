import cgitb
import configparser
import os
import re
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib import parse

from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from FormView import Ui_dialog
from HisUrlDialog import HisUrlDialog
from util.HttpClient import HttpClient
from util.ProgressDelegate import ProgressDelegate
from util.Worker import Worker
from util.ToolUtil import ToolUtil
from queue import Queue


class MainForm(QWidget, Ui_dialog):
    # 配置文件位置
    config_file_path = 'config.ini'
    # 历史url文件保存路径
    his_url_file_path = 'his_url.txt'
    # 历史作者保存路径
    author_file_path = 'author.txt'

    # 当前活跃的tab页索引
    tab_index_active = 0
    # tab索引-根据url解析
    tab_index_url = 0
    # tab索引-根据作者解析
    tab_index_author = 1
    # tab索引-根据关注列表解析
    tab_index_attention = 2

    def __init__(self):
        # 视图处理
        super(MainForm, self).__init__()
        self.setupUi(self)
        self.icon = QIcon(':img/favicon_small.ico')
        # 设置图标
        self.setWindowIcon(self.icon)

        # ================================ 控件初始化赋值 ================================
        # 初始化配置文件
        self.conf_flag = False
        self.__init_config()
        # 解析url文本框
        if self.conf_flag:
            # url地址 fallback 为未获取到key值时的返回值
            self.lineEdit.setText(self.conf.get('global', 'url', fallback=None))
            # 代理地址文本框
            self.proxyPathEdit.setText(self.conf.get('global', 'proxy_path', fallback=None))
            # 下载线程数文本框
            self.downloadTaskNumSpinBox.setValue(self.conf.getint('global', 'download_task_num', fallback=None))
            # 存储位置文本框
            self.savePathEdit.setText(self.conf.get('global', 'save_path_edit', fallback=None))
            # cookie文本框
            self.cookieEdit.setText(self.conf.get('global', 'cookie', fallback=None))
            # 是否开启作者名称前缀
            self.authorCheckBox.setChecked(self.conf.getboolean('global', 'author_prefix', fallback=None))
            # 设置作者信息
            self.authorLineEdit.setText(self.conf.get('global', 'author', fallback=None))
            # 设置默认展示的tab页
            self.tabWidget.setCurrentIndex(self.conf.getint('global', 'tab_index_active', fallback=None))
            # 是否开启代理
            self.isOpenAgentCheckBox.setChecked(self.conf.getboolean('global', 'is_open_agent', fallback=None))
            # 帐号
            self.accountLineEdit.setText(self.conf.get('global', 'account', fallback=None))
            # 密码
            self.passwordLineEdit.setText(self.conf.get('global', 'password', fallback=None))
        else:
            # url地址
            self.lineEdit.setText('https://ecchi.iwara.tv/users/Dyson000/videos')
            # 代理地址文本框
            self.proxyPathEdit.setText('127.0.0.1:1080')
            # 下载线程数文本框
            self.downloadTaskNumSpinBox.setValue(1)
            # 存储位置文本框
            self.savePathEdit.setText('D:/test')
            # 是否开启作者名称前缀
            self.authorCheckBox.setChecked(True)
            # 设置作者信息
            self.authorLineEdit.setText('sien')
            # 设置默认展示的tab页
            self.tabWidget.setCurrentIndex(self.tab_index_active)
            # 是否开启代理
            self.isOpenAgentCheckBox.setChecked(False)
            # 帐号
            self.accountLineEdit.setText('')
            # 密码
            self.passwordLineEdit.setText('')
        # 初始化表格
        self.__init_table()

        # ================================ 数据初始化赋值 ================================
        # 列表页面url
        self.url = ''
        # 声明解析后的数据信息集合
        self.video_info_list = []

        self.task_queue = Queue(maxsize=0)
        self.task_list = []
        # 声明请求工具类
        self.http_client = None
        # 初始化解析线程池
        self.__parse_thread_pool = ThreadPoolExecutor(max_workers=20,
                                                      thread_name_prefix="python_comic_parse_")
        # 声明下载线程池
        self.__download_thread_pool = None
        # 声明线程锁
        self.lock = threading.Lock()
        # 上次打开的保存位置
        self.last_save_path = 'C:\\'
        # 提取url中的作者名正则表达式
        self.author_re = re.compile('(?<=users/).*?(?=/)', re.S)

        self.select_his_url_dialog = None
        self.select_his_author_dialog = None

        self.tabWidget.currentChanged.connect(self.__tab_widget_changed)

        self.is_open_agent = self.isOpenAgentCheckBox.isChecked()

        self.isOpenAgentCheckBox.stateChanged.connect(self.__change_is_open_agent_check_box)

    # ================================ 按钮点击事件重写 ================================
    # 登录按钮
    def login_btn_click(self):
        login_task = threading.Thread(target=self.__init_login())
        login_task.start()

    # 解析按钮
    def parsing_btn_click(self):
        # 解析中禁用下载按钮
        self.batchDownloadButton.setDisabled(True)
        self.downloadOneButton.setDisabled(True)
        self.__init_http_client()

        # 获取要解析的url
        if self.tab_index_active == self.tab_index_url:
            # 当前激活的url下载tab
            url = self.lineEdit.text().strip()
            # 拼接页数
            page_num = self.urlPageNumspinBox.value()
            if page_num > 1:
                url = url + '?page=' + str(page_num - 1)
        elif self.tab_index_active == self.tab_index_author:
            # 当前激活的是作者下载tab
            # https://ecchi.iwara.tv/users/Dyson000/videos
            # https://ecchi.iwara.tv/users/Dyson000
            author = self.authorLineEdit.text().strip()
            url = 'https://ecchi.iwara.tv/users/' + author + '/videos'
            # 拼接页数
            page_num = self.authorPageNumspinBox.value()
            if page_num > 1:
                url = url + '?page=' + str(page_num - 1)
        elif self.tab_index_active == self.tab_index_attention:
            url = self.lineEdit.text().strip()
        else:
            return
        # 拼接参数
        if "?" in url:
            url = url + "&language=zh-hans"
        else:
            url = url + "?language=zh-hans"
        # 清空视频信息
        self.video_info_list = []
        # 初始化表格
        self.__init_table()
        # 启用多线程解析视频信息并跟新视图
        task = threading.Thread(target=self.__get_list_info, args=[url])
        task.start()

    @pyqtSlot()
    def check_data_status(self):
        for info in self.video_info_list:
            # 处理文件名
            original_file_name = info['title']
            if self.authorCheckBox.isChecked():
                original_file_name = info['author'] + " - " + info['title']
            file_name = ToolUtil.replace_title(original_file_name)
            file_path = self.savePathEdit.text() + '/' + file_name + '.mp4'
            # 判断是否存在
            if os.path.lexists(file_path):
                item = [
                    info['id'],
                    6,
                    "100.000%",
                    100,
                    "文件已存在"
                ]
            else:
                item = [
                    info['id'],
                    6,
                    "0.000%",
                    0,
                    "未下载"
                ]
            self.__update_table_item(item)
        self.__global_info_label_update('检查完成')

    # 批量下载按钮
    def batch_download_btn_click(self):
        self.__init_http_client()
        # 清理之前的任务
        if len(self.task_list) > 0:
            for task in self.task_list:
                if task.isRunning():
                    task.quit()
                    task.wait()
        # 存储进程列表 防止局部变量覆盖后线程终止
        self.task_list = []
        # # 获取同时下载个数
        num = self.downloadTaskNumSpinBox.value()
        # 获取保存路径
        save_path = self.savePathEdit.text() + '/'
        # 遍历解析出的视频数据 向线程池提交下载任务
        if len(self.video_info_list) > 0:
            for index, info in enumerate(self.video_info_list):
                if index < int(num):
                    # 实例化多线程对象
                    thread = Worker(info=info, save_path=save_path, data_id=info['id'],
                                    is_proxies=self.is_open_agent,
                                    proxy_path=self.proxyPathEdit.text(),
                                    is_author_prefix=self.authorCheckBox.isChecked())
                    # 信号与槽函数的连接
                    thread.tableViewSign.connect(self.__update_table_item)
                    # 线程开启信号连接
                    thread.startSign.connect(self.__start_download)
                    # 信息更新连接
                    thread.globalInfoSign.connect(self.__global_info_label_update)
                    thread.start()
                    self.task_list.append(thread)
                else:
                    # 设置批量下载按钮可点击
                    self.batchDownloadButton.setDisabled(True)
                    info.setdefault('index', index)
                    self.task_queue.put(info)

    # 下载一个按钮
    def single_download_btn_click(self):
        self.__start_download()

    # 检查状态按钮
    def status_check_btn_click(self):
        self.__start_download()

    # 选择保存位置按钮
    def select_file_dir_btn(self):
        # 起始路径 上次选择的位置
        directory = QtWidgets.QFileDialog.getExistingDirectory(None, "请选择存储位置", self.last_save_path)
        if directory:
            print(directory)
            self.last_save_path = directory
        self.savePathEdit.setText(directory)

    # 关闭按钮执行方法
    def closeEvent(self, close_event):
        # 创建一个问答框，注意是Question
        box = QMessageBox(QMessageBox.Question, '退出', '确定保存配置并退出?')
        # 添加按钮，可用中文
        yes = box.addButton('保存配置并退出', QMessageBox.YesRole)
        no = box.addButton('直接退出', QMessageBox.NoRole)
        box.addButton('取消', QMessageBox.RejectRole)
        # 设置消息框中内容前面的图标
        box.setWindowIcon(self.icon)
        # 设置消息框的位置，大小无法设置
        # box.setGeometry(500, 500, 0, 0)
        # 显示该问答框
        box.exec_()
        # 判断分支选择
        if box.clickedButton() == yes:
            self._save_config_to_file()
            close_event.accept()
            # sys.exit(0)
            os._exit(0)
        elif box.clickedButton() == no:
            close_event.accept()
            os._exit(0)
            # sys.exit(0)
        else:
            close_event.ignore()

    # url文本框完成编辑
    def create_author_dir_btn(self):
        text = self.lineEdit.text()
        if 'users/' in text:
            author_arr = re.findall(self.author_re, text)
            if len(author_arr) > 0:
                author = parse.unquote(author_arr[0])
                save_path = self.savePathEdit.text()
                if author not in save_path:
                    self.savePathEdit.setText(save_path + '/' + author)

    def _save_config_to_file(self):
        # 确定关闭 写入当前配置
        if not self.conf.has_section("global"):
            self.conf.add_section("global")
        # 写入配置
        self.conf.set("global", "url", parse.unquote(self.lineEdit.text()))
        self.conf.set("global", "proxy_path", self.proxyPathEdit.text())
        self.conf.set("global", "download_task_num", str(self.downloadTaskNumSpinBox.value()))
        self.conf.set("global", "save_path_edit", self.savePathEdit.text())
        self.conf.set("global", "cookie", self.cookieEdit.text())
        self.conf.set("global", "author_prefix", str(self.authorCheckBox.isChecked()))
        self.conf.set("global", "author", self.authorLineEdit.text())
        self.conf.set("global", "tab_index_active", str(self.tab_index_active))
        self.conf.set("global", "is_open_agent", str(self.is_open_agent))
        self.conf.set("global", "account", str(self.accountLineEdit.text()))
        self.conf.set("global", "password", str(self.passwordLineEdit.text()))
        # 保存到文件
        self.conf.write(open(self.config_file_path, "w", encoding='utf-8'))

    # ================================ 内部调用方法 ================================
    # 初始化表格
    def __init_table(self):
        self.tableView.model = QStandardItemModel(0, 8)
        self.tableView.model.setHorizontalHeaderLabels(["主键", "标题", "发布顺序", "like数", "观看数", "作者", "下载进度", "进度条", "大小"])
        # 表头列宽自动分配
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        # 水平方向标签拓展剩下的窗口部分，填满表格
        self.tableView.horizontalHeader().setStretchLastSection(True)
        # 设置行号列宽度 对齐方式
        self.tableView.verticalHeader().setFixedWidth(30)
        self.tableView.verticalHeader().setDefaultAlignment(Qt.AlignCenter)
        # 更新表格
        self.tableView.setModel(self.tableView.model)
        # 设置标题宽度
        self.tableView.setColumnWidth(1, 400)
        # 设置发布顺序宽度
        self.tableView.setColumnWidth(2, 60)
        # 设置喜爱数宽度
        self.tableView.setColumnWidth(3, 65)
        # 设置观看数宽度
        self.tableView.setColumnWidth(4, 65)
        # 设置受欢迎宽度
        self.tableView.setColumnWidth(5, 65)
        # 隐藏id列
        self.tableView.setColumnHidden(0, True)
        # 设置可排序
        self.tableView.setSortingEnabled(True)
        # 委托进度条处理
        delegate = ProgressDelegate(self.tableView)
        # 指定进度条列
        self.tableView.setItemDelegateForColumn(7, delegate)

        # 初始化右键菜单
        self.tableView.customContextMenuRequested['QPoint'].connect(self.__show_table_right_menu)
        self.right_menu = QMenu()
        self.table_menu_action_del = self.right_menu.addAction("删除行")

        # self.table_menu_action_re_download = self.right_menu.addAction("重新下载")
        # self.table_menu_action_stop_download = self.right_menu.addAction("停止下载")

        self.table_menu_action_del.triggered.connect(self.__delete_table_rows)

    # 显示表格右键菜单
    @pyqtSlot()
    def __show_table_right_menu(self):
        # 在正确位置展示邮件菜单
        self.right_menu.move(QCursor.pos())
        self.right_menu.show()

    # 是否开启代理控件槽函数
    @pyqtSlot(int)
    def __change_is_open_agent_check_box(self, state):
        self.is_open_agent = state != 0

    # tab页切换槽函数
    @pyqtSlot(int)
    def __tab_widget_changed(self, tab_index):
        self.tab_index_active = tab_index

    # 删除表格数据
    @pyqtSlot()
    def __delete_table_rows(self):
        indexes = self.tableView.selectionModel().selectedRows()
        if len(indexes) > 0:
            # 创建一个问答框，注意是Question
            box = QMessageBox(QMessageBox.Question, '删除行', '当前选中[' + str(len(indexes)) + ']条数据,确定删除吗?')
            # 添加按钮，可用中文
            yes = box.addButton('删除', QMessageBox.YesRole)
            box.addButton('取消', QMessageBox.RejectRole)
            # 设置消息框中内容前面的图标
            box.setWindowIcon(self.icon)
            # 显示该问答框
            box.exec_()

            # 判断分支选择
            if box.clickedButton() == yes:
                # 要删除的id集合
                del_id_list = []
                # 要删除的索引集合
                row_index_list = []
                # 先获取数据
                for i in indexes:
                    data_id = i.model().data(i)
                    del_id_list.append(data_id)
                    # 获取要删除行的索引
                    row_index_list.append(i.row())
                # 索引值倒序 从后往前删
                row_index_list.reverse()
                for index in row_index_list:
                    # 删除表格行
                    self.tableView.model.removeRow(index)
                # 同步删除数据
                for data_id in del_id_list:
                    for info in self.video_info_list:
                        # 根据id是否相等进行删除
                        if info['id'] == data_id:
                            self.video_info_list.remove(info)
                            break

    # 初始化配置文件
    def __init_config(self):
        self.conf = configparser.ConfigParser()
        # 读取文件
        self.conf.read(self.config_file_path, encoding='utf-8')
        if os.path.lexists(self.config_file_path):
            self.conf_flag = True

    # 初始化
    def __init_http_client(self):
        # 声明请求工具类
        self.http_client = HttpClient(proxy_path=self.proxyPathEdit.text(),
                                      cookie=self.cookieEdit.text())

    # 登录方法 实现逻辑 根据用户名密码进行登录操作，并替换当前cookie
    def __init_login(self):
        self.__init_http_client()
        account = self.accountLineEdit.text()
        password = self.passwordLineEdit.text()
        if account == '' or password == '':
            # 弹出错误提示
            QMessageBox.information(self.window(), "提示", "请输入用户名和密码！！")
            return
        cookie = self.http_client.login(account, password)
        # 判断返回cookie值 若为空则说明登录失败
        if cookie == '':
            QMessageBox.information(self.window(), "提示", "用户名或密码错误 登录失败")
            return
        self.cookieEdit.setText(cookie)
        # 弹出成功提示
        QMessageBox.information(self.window(), "提示", "登录成功并替换cookie")

    # 获取列表页
    def __get_list_info(self, text):
        self.__global_info_label_update('正在解析列表...')
        # 1.获取列表页
        try:
            html_info = self.http_client.get_html_format(text, timeout=30, is_proxies=self.is_open_agent)
        except Exception as e:
            self.__global_info_label_update('解析失败!' + str(e))
            return
        self.__global_info_label_update('正在解析列表视频...')
        # 解析一页的信息
        item_info_div_list = html_info.find_all(
            attrs={'class': 'node node-video node-teaser node-teaser clearfix'})
        task_list = []
        # 获取
        for div_info in item_info_div_list:
            task_list.append(self.__parse_thread_pool.submit(self.__get_video_info, div_info))
        # 按顺序获取列表
        i = 0
        for task in task_list:
            i += 1
            try:
                # 获取解析信息
                video_info = task.result(timeout=10)
                # 设置发布顺序
                video_info.setdefault("release_order", str(i))
                # 放入集合
                self.video_info_list.append(video_info)
                # 更新数据表格
                self.__add_table_view_row(video_info)
                # 根据内容调整行高
                self.tableView.resizeRowsToContents()
            except Exception as e:
                self.__global_info_label_update("解析超时 跳过" + str(e))

        # 解析完成启用下载按钮
        self.batchDownloadButton.setDisabled(False)
        self.downloadOneButton.setDisabled(False)

        self.__global_info_label_update('解析地址完成')

    # 开启单个任务下载
    def __start_download(self):
        # 获取保存路径
        save_path = self.savePathEdit.text() + '/'
        if not self.task_queue.empty():
            info = self.task_queue.get()
            # 实例化多线程对象 是否添加作者前缀
            thread = Worker(info=info, save_path=save_path, data_id=info['id'],
                            is_proxies=self.is_open_agent,
                            proxy_path=self.proxyPathEdit.text(),
                            is_author_prefix=self.authorCheckBox.isChecked())
            # 信号与槽函数的连接
            thread.tableViewSign.connect(self.__update_table_item)
            thread.startSign.connect(self.__start_download)
            self.task_list.append(thread)
            thread.start()
        else:
            # 设置批量下载按钮可点击
            self.batchDownloadButton.setDisabled(False)

    # 解析视频信息
    @staticmethod
    def __get_video_info(div_info):
        # 解析视频哈希值
        video_hash = div_info.find('a')['href'][8:]
        # 解析作者
        username = div_info.find('a', attrs={'class': 'username'}).text
        # 解析视频标题
        video_title = div_info.find('img')['title']
        # 预览图片地址
        video_img_path = div_info.find('img')['src']
        # 解析like数
        video_like_num = div_info.find(attrs={'class': 'right-icon likes-icon'}).text.replace('\n', '').strip()
        # 解析观看数
        video_view_num = div_info.find(attrs={'class': 'left-icon likes-icon'}).text.replace('\n', '').strip()
        # 真实观看数
        if "k" in video_view_num:
            video_view = float(video_view_num.replace("k", "")) * 1000
        else:
            video_view = float(video_view_num)
        # 受欢迎度
        popular_num = float(video_like_num) / video_view * 100
        # 信息汇总
        video_info = {
            'id': str(uuid.uuid1()),
            'title': video_title,
            'like_num': video_like_num,
            'view_num': video_view_num,
            'popular_num': "%.3f" % popular_num,
            'img_path': 'https:' + video_img_path,
            'author': username,
            'video_hash': video_hash
        }
        # 更新视图
        return video_info

    # ================================ 视图更新方法 =======================================
    # 更新表格接收信号方法
    @pyqtSlot(list)
    def __update_table_item(self, args):
        # 进度
        process = QStandardItem(args[2])
        process.setTextAlignment(Qt.AlignCenter)
        # 进度条
        processBar = QStandardItem()
        processBar.setData(args[3], role=Qt.EditRole)
        # 大小
        size = QStandardItem(args[4])
        size.setTextAlignment(Qt.AlignCenter)
        # 设置搜索起始范围
        start = self.tableView.model.index(0, 0)
        # 查询对应单元格
        matches = self.tableView.model.match(start, Qt.DisplayRole, args[0], 1, Qt.MatchContains)
        # 找到匹配数据
        if matches:
            index = matches[0]
            # 行索引赋值
            self.tableView.model.setItem(index.row(), args[1], process)
            self.tableView.model.setItem(index.row(), args[1] + 1, processBar)
            self.tableView.model.setItem(index.row(), args[1] + 2, size)

    # 表格添加行
    def __add_table_view_row(self, video_info):
        title = QStandardItem(video_info['title'])
        release_order = QStandardItem(video_info['release_order'])
        like_num = QStandardItem(video_info['like_num'])
        view_num = QStandardItem(video_info['view_num'])
        author = QStandardItem(video_info['author'])
        process = QStandardItem('0.000%')
        processBar = QStandardItem()

        # 设置排序数据
        release_order.setData(int(video_info['release_order']), role=Qt.EditRole)
        like_num.setData(int(video_info['like_num']), role=Qt.EditRole)
        view_num.setData(float(video_info['view_num'].replace("k", "")), role=Qt.EditRole)
        # 设置data会覆盖原展示值 再次赋值
        view_num.setText(video_info['view_num'])
        processBar.setData(0, role=Qt.EditRole)

        title.setTextAlignment(Qt.AlignLeft | Qt.AlignBottom)
        release_order.setTextAlignment(Qt.AlignCenter)
        like_num.setTextAlignment(Qt.AlignCenter)
        view_num.setTextAlignment(Qt.AlignCenter)
        author.setTextAlignment(Qt.AlignCenter)
        process.setTextAlignment(Qt.AlignCenter)

        self.tableView.model.appendRow([
            QStandardItem(video_info['id']),
            title,
            release_order,
            like_num,
            view_num,
            author,
            process,
            processBar,
            QStandardItem()
        ])

    # 下方信息展示
    def __global_info_label_update(self, info):
        self.infoLabel.setText(info)

    # ================================ 子窗口部分 =======================================
    # 点击按钮展示自定义对话框
    def select_his_url_btn_click(self):
        # 创建对话框
        self.select_his_url_dialog = HisUrlDialog(self.icon, "请选择历史链接", his_url_file_path=self.his_url_file_path)
        # 组装控件
        self.select_his_url_dialog.setupUi(self.select_his_url_dialog)
        # 初始化
        self.select_his_url_dialog.init_list()
        # 连接自定义信号
        self.select_his_url_dialog.selectItemSign.connect(self.__update_url_edit)
        # 展示对话框
        self.select_his_url_dialog.show()

    def select_his_author_btn_click(self):
        # 创建对话框
        self.select_his_author_dialog = HisUrlDialog(self.icon, "请选择历史作者", his_url_file_path=self.author_file_path)
        # 组装控件
        self.select_his_author_dialog.setupUi(self.select_his_author_dialog)
        # 初始化
        self.select_his_author_dialog.init_list()
        # 连接自定义信号
        self.select_his_author_dialog.selectItemSign.connect(self.__update_author_edit)
        # 展示对话框
        self.select_his_author_dialog.show()

    # 更新解析地址文本框方法
    def __update_url_edit(self, info):
        self.lineEdit.setText(info)

    def __update_author_edit(self, info):
        self.authorLineEdit.setText(info)

    # 保存url信息
    def save_url_to_file(self):
        url = self.lineEdit.text()
        if url:
            self.__save_info_to_file(self.his_url_file_path, url)

    # 保存作者信息
    def save_author_to_file(self):
        url = self.authorLineEdit.text()
        if url:
            self.__save_info_to_file(self.author_file_path, url)

    def __save_info_to_file(self, file_path, info):
        file = open(file_path, 'a+', encoding='utf-8')
        # 移动文件指针到开头以读取
        file.seek(0)
        lines = file.readlines()
        if lines.count(info + '\n') == 0:
            file.write(info + '\n')
            QMessageBox.information(self.window(), "提示", "保存成功")
        else:
            QMessageBox.information(self.window(), "提示", "数据已存在")
        file.close()


# ================================ 程序入口 ================================
if __name__ == '__main__':
    # 全局异常处理 写入日志
    if not os.path.lexists('log'):
        os.makedirs('log')
    cgitb.enable(display=0, format='text', logdir='log')

    app = QtWidgets.QApplication(sys.argv)
    main_form = MainForm()

    # 下面这三行就是汉化的
    translator = QTranslator()
    translator.load(':/qm/static/qm/qt_zh_CN.qm')
    app.installTranslator(translator)

    # 显示窗口
    main_form.show()
    sys.exit(app.exec_())
