
# download_video_gui

#### 一、介绍
爬取视频python工具


#### 二、依赖管理
    1.  导出依赖 pip freeze > requirements.txt
        报错解决：https://blog.csdn.net/weixin_44546342/article/details/105229575
    2.  安装依赖 pip install -r requirements.txt
    3.  源文件编译命令 pyrcc5 res.qrc -o res_rc.py

#### 三、发布说明
    1.  在项目主目录运行 pip install pyinstaller 安装打包工具
    2.1.  打包单文件:在项目主目录运行 pyinstaller -Fw -i favicon.ico main.py
    2.2.  打包程序: pyinstaller -FwD -i favicon.ico main.py
    3.  main.exe 即可执行文件

#### 四、后续功能

1、关注列表下载

~~2、使用帐号密码登录自动登录功能~~(已实现)

#### 五、软件截图

![](img\微信截图_20210224163158.png)