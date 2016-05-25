# coding:utf-8
from application import Application

app = Application()

if __name__ == "__main__":
    app.run()
else:
    app = app.get_wsgi()
