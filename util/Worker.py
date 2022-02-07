from contextlib import closing
from PyQt5.QtCore import *
from util.HttpClient import HttpClient
import os
from util.ToolUtil import ToolUtil
import threading


# 子线程工作对象
class Worker(QThread):
    # 下载进度的在table中的列索引值 用以回调更新表格
    start_column_num = 6
    # 表格更新信号
    tableViewSign = pyqtSignal(list)
    # 开启新进程信号
    startSign = pyqtSignal()
    # 信息展示更新信号
    globalInfoSign = pyqtSignal(str)

    def __init__(self, info=None, save_path='', data_id='', is_proxies=True, proxy_path='127.0.0.1:1080',
                 is_author_prefix=False):
        super().__init__()
        # 视频信息
        self.info = info
        # 保存文件夹路径
        self.save_path = save_path
        # 表中生成的唯一id
        self.data_id = data_id
        # 是否开启代理
        self.is_proxies = is_proxies
        # 下载工具
        self.http_client = HttpClient(proxy_path=proxy_path)
        # 是否添加作者作为文件名前缀
        self.is_author_prefix = is_author_prefix
        # 声明计时器 用以定时更新表格
        self.timer = None
        # 初始化发送到表格的数据格式
        self.data = [
            self.data_id,
            self.start_column_num,
            "0.000%",
            0,
            "正在建立连接..."
        ]

    # 开启定时发送更新表格信号
    def __send_update_sign(self, n):
        # 发送信号
        self.tableViewSign.emit(self.data)
        # 第一个参数表示多长时间后调用后面第二个参数指明的函数。第二个参数注意是函数对象，进行参数传递，用函数名(如printTime)表示该对象，不能写成函数执行语句printTime()，不然会报错。可以用type查看出两者的区别
        self.timer = threading.Timer(n, self.__send_update_sign, (n,))
        self.timer.start()

    def run(self):
        # 若路径不存在 就创建
        if not os.path.lexists(self.save_path):
            os.mkdir(self.save_path)
        # 拼接文件地址
        original_file_name = self.info['title']
        if self.is_author_prefix:
            original_file_name = self.info['author'] + " - " + self.info['title']
        file_name = ToolUtil.replace_title(original_file_name)
        file_path = self.save_path + file_name + '.mp4'
        # 判断文件是否存在 若存在则证明之前已下载完成 无需下载
        if os.path.lexists(file_path):
            self.globalInfoSign.emit('文件已下载完成:' + file_path)
            args = [
                self.data_id,
                self.start_column_num,
                "100.000%",
                100,
                "文件已存在"
            ]
            # 更新表格
            self.tableViewSign.emit(args)
            # 开启新任务
            self.startSign.emit()
            return

        self.globalInfoSign.emit("下载任务开始")
        # 开启计时器 定时更新表格数据
        self.__send_update_sign(0.1)
        # 开启流式请求
        try:
            # 声明请求状态码
            status_code = None
            # 声明下载链接请求
            req = None
            # 声明msg
            args = None
            # 声明下载进度
            progress = 0
            # 声明最大重试次数
            num = 0
            # 是否为私人视频
            is_private = False
            while status_code != 200:
                # 以下while循环开始
                num = num + 1
                # 最大重试次数
                if num > 5:
                    break
                # 获取下载地址信息
                down_load_info = self.http_client.get_json(
                    'https://ecchi.iwara.tv/api/video/' + self.info['video_hash'],
                    is_proxies=self.is_proxies, timeout=5)
                if len(down_load_info) == 0:
                    self.timer.cancel()
                    args = [
                        self.data_id,
                        self.start_column_num,
                        "0.000%",
                        0,
                        "私人视频 无下载地址"
                    ]
                    # 确认为私人视频
                    is_private = True
                    self.tableViewSign.emit(args)
                    # 若是无法下载的视频则直接跳出循环
                    break
                else:
                    # 拼接下载地址
                    source_uri = 'https:' + down_load_info[0]['uri']
                    # 定义流式下载请求
                    req = self.http_client.get(source_uri, stream=True, is_proxies=self.is_proxies, timeout=5)
                    status_code = req.status_code
                    # 以上while循环结束
            # 判断成功获取了下载链接
            if req is not None and status_code == 200:
                with closing(req) as response:
                    chunk_size = 1024
                    content_size = int(response.headers['content-length'])
                    date_count = 0
                    # 若路径不存在 就创建
                    if not os.path.lexists(self.save_path):
                        os.mkdir(self.save_path)
                    try:
                        # 创建缓存文件
                        file_path_temp = self.save_path + file_name + '.mp4' + '.temp'
                        with open(file_path_temp, "wb") as file:
                            for data in response.iter_content(chunk_size=chunk_size):
                                # 将下载数据写入缓存
                                file.write(data)
                                # 已下载数据量
                                date_count = date_count + len(data)
                                # 计算下载进度
                                progress = (date_count / content_size) * 100
                                # 转换单位
                                date_count_str = ToolUtil.hum_convert(date_count)
                                content_size_str = ToolUtil.hum_convert(content_size)
                                args = [
                                    self.data_id, self.start_column_num, "%.3f%%" % progress,
                                                                         "%d" % progress,
                                                                         "%s/%s" % (date_count_str, content_size_str)
                                ]
                                # 将当前下载状态更新到data变量中，由定时器定时获取刷新表格
                                self.data = args
                        # 只有当文件大小符合要求才可重命名
                        if date_count == content_size:
                            # 文件重命名
                            os.rename(file_path_temp, file_path)
                        else:
                            # 删除缓存文件
                            os.remove(file_path_temp)
                        # 关闭定时器
                        self.timer.cancel()
                        # 手动发送最新的下载完成数据到表格 防止未及时更新数据
                        self.tableViewSign.emit(args)
                    except Exception as e:
                        self.timer.cancel()
                        args = [
                            self.data_id, self.start_column_num,
                            "下载出错" + str(e),
                            "%d" % progress,
                            ToolUtil.hum_convert(date_count) + "/" + ToolUtil.hum_convert(content_size)
                        ]
                        # 删除缓存文件
                        os.remove(file_path_temp)
                        self.tableViewSign.emit(args)
            elif is_private is False:
                self.timer.cancel()
                args = [
                    self.data_id,
                    self.start_column_num,
                    "0.000%",
                    0,
                    "获取下载连接失败 请求状态码:" + str(status_code)
                ]
                self.tableViewSign.emit(args)
        except Exception as e:
            self.timer.cancel()
            args = [
                self.data_id,
                self.start_column_num,
                "0.000%",
                0,
                str(e)
            ]
            self.tableViewSign.emit(args)
        print("任务完成 开启新任务")
        self.startSign.emit()
