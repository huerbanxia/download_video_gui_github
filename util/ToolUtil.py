import re


class ToolUtil:

    # 计算数字单位工具
    @staticmethod
    def hum_convert(value):
        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        size = 1024.0
        for i in range(len(units)):
            if (value / size) < 1:
                return "%.2f%s" % (value, units[i])
            value = value / size

    # 替换掉特殊字符以符合文件名称格式
    @staticmethod
    def replace_title(title):
        rep = r"[/\:*?\"<>|']"  # / \ : * ? " < > | '
        # 替换为下划线
        new_title = re.sub(rep, "_", title)
        # 限制文件名长度
        if len(new_title) > 150:
            # 截取前多少位
            new_title = new_title[:150]
        return new_title
