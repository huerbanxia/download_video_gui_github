import json
import random
import requests
import requests.utils
from bs4 import BeautifulSoup


class HttpClient(object):

    def __init__(self, proxy_path='127.0.0.1:1080', cookie=None):
        # 初始化请求session
        self.session = requests.session()
        # 全局超时时间
        self.timeout = 30
        # 代理地址
        self.proxy_path = proxy_path
        # 代理对象
        self.proxies = {
            "http": "http://%(proxy)s/" % {'proxy': self.proxy_path},
            "https": "http://%(proxy)s/" % {'proxy': self.proxy_path}
        }
        self.cookie = cookie
        # 设置cookie项 展示成人内容
        # self.session.cookies['show_adult'] = '1'
        self.user_agent_pc = [
            # 谷歌
            'Mozilla/5.0.html (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.html.2171.71 Safari/537.36',
            'Mozilla/5.0.html (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.html.1271.64 Safari/537.11',
            'Mozilla/5.0.html (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.html.648.133 Safari/534.16',
            # 'Mozilla/5.0 (Windows NT 6.1; WOW64)AppleWebKit/537.36(KHTML,likeGecko)Chrome/39.0.2171.71 Safari/537.36',
            # 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko)Chrome/23.0.1271.64 Safari/537.11',
            # 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16',
            # 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11',
            # 火狐`
            'Mozilla/5.0.html (Windows NT 6.1; WOW64; rv:34.0.html) Gecko/20100101 Firefox/34.0.html',
            'Mozilla/5.0.html (X11; U; Linux x86_64; zh-CN; rv:1.9.2.10) Gecko/20100922 Ubuntu/10.10 (maverick) Firefox/3.6.10',
            # opera
            'Mozilla/5.0.html (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.html.2171.95 Safari/537.36 OPR/26.0.html.1656.60',
            # qq浏览器
            'Mozilla/5.0.html (compatible; MSIE 9.0.html; Windows NT 6.1; WOW64; Trident/5.0.html; SLCC2; .NET CLR 2.0.html.50727; .NET CLR 3.5.30729; .NET CLR 3.0.html.30729; Media Center PC 6.0.html; .NET4.0C; .NET4.0E; QQBrowser/7.0.html.3698.400)',
            # 搜狗浏览器
            'Mozilla/5.0.html (Windows NT 5.1) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.html.963.84 Safari/535.11 SE 2.X MetaSr 1.0.html',
            # 360浏览器
            # 'Mozilla/5.0.html (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.html.1599.101 Safari/537.36',
            'Mozilla/5.0.html (Windows NT 6.1; WOW64; Trident/7.0.html; rv:11.0.html) like Gecko',
            # uc浏览器
            'Mozilla/5.0.html (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.html.2125.122 UBrowser/4.0.html.3214.0.html Safari/537.36',
        ]

    def __get_random_headers(self):
        return {
            "User-Agent": random.choice(self.user_agent_pc),
            "Referer": "https://www.iwara.tv",
            'Cookie': self.cookie
        }

    # 使用同一会话发起请求方法
    def get(self, url: str, params=None, referer=None, is_proxies=False, timeout=None, stream=False):
        if params is None:
            params = {}
        headers = self.__get_random_headers()
        if referer is not None:
            headers['Referer'] = referer
        if is_proxies:
            proxies = self.proxies
        else:
            proxies = {}
        if timeout is None:
            timeout = self.timeout
        return self.session.get(url, timeout=timeout, proxies=proxies, headers=headers, params=params, stream=stream)

    def reset(self):
        self.session.close()
        self.session = requests.session()
        # 设置简体
        self.session.cookies['mangabz_lang'] = '2'

    def get_html_format(self, url: str, params=None, referer=None, is_proxies=False, timeout=None):
        res = self.get(url, params, referer, is_proxies, timeout)
        soup = BeautifulSoup(res.content, "lxml")
        return soup

    def get_json(self, url: str, params=None, referer=None, is_proxies=False, timeout=None):
        res = self.get(url, params, referer, is_proxies, timeout)
        return json.loads(res.content)

    # 登录方法
    def login(self, username: str, password: str):
        # 根据用户输入的数据构建登录数据
        data = {
            'name': username,
            'pass': password,
            'form_id': 'user_login',
            'form_build_id': 'form-ZZ6KGg8LNw3Gkwl3ikNDKt8quKvULW6nBoK9c7_E6eA',
            'antibot_key': '13ac4273dc853636a2413f2d70b438ff',
        }
        cookie = ''
        try:
            # 发起登录请求
            self.session.post('https://www.iwara.tv/user/login?language=zh-hans', data)
            # 解析cookies
            cookies = requests.utils.dict_from_cookiejar(self.session.cookies)
            # 判断是否登录成功 若失败则直接返回None
            if cookies.keys().len() != 0:
                # 拼接cookie并返回
                for key in cookies.keys():
                    cookie = cookie + key + '=' + cookies[key] + ';'
                cookie = cookie + 'show_adult=1;'
        except Exception:
            pass
        return cookie
