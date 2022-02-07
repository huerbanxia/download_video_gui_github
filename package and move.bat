cd ./
rd/s/q .\dist\main
pyinstaller -FwD -i favicon.ico main.py
xcopy .\dist\main D:\Tools\main\ /e/h/Y
