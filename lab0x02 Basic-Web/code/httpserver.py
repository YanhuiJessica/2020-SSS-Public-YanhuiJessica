# -*- coding: utf-8 -*-

import sys
import cgi
from http.server import HTTPServer, BaseHTTPRequestHandler
import sqlite3

class MyHTTPRequestHandler(BaseHTTPRequestHandler):
    field_name = 'a'
    form_html = \
        '''
        <html>
        <body>
        <form method='post' enctype='multipart/form-data'>
        <input type='text' name='%s'>
        <input type='submit'>
        </form>
        </body>
        </html>
        ''' % field_name

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        try:
            file = open("." + self.path, "rb")
            # self.path 为请求的路径
            # e.g. http://127.0.0.1:8080/a.html
            # /a.html 为路径
        except FileNotFoundError as e:
            print(e)
            self.wfile.write(self.form_html.encode())
        else:
            content = file.read()
            self.wfile.write(content)

    def do_POST(self):
        ans = "OK"
        form_data = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': self.headers['Content-Type'],
            })
        fields = form_data.keys()
        if self.field_name in fields:
            input_data = form_data[self.field_name].value
            file = open("."+self.path, "wb")
            file.write(input_data.encode())

        elif 'res' in fields: # 当前为录入成绩
            cid = form_data['cid'].value
            sid = form_data['sid'].value
            res = form_data['res'].value
            conn = sqlite3.connect('edu.db')
            c = conn.cursor()
            sql = "insert into results values (%s, %s, %s)"%(cid, sid, res)
            c.execute(sql)
            conn.commit()
            conn.close()
        else:   # 当前为查询
            cid = form_data['cid'].value
            sid = form_data['sid'].value
            conn = sqlite3.connect('edu.db')
            c = conn.cursor()
            sql = "select res from results where cid=%s and sid=%s"%(cid, sid)
            c.execute(sql)
            ans = "%s 同学 %s 课程的成绩为 " % (sid, cid) + str(c.fetchone()[0])
            conn.close()

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes(str("<html lang='zh-CN'><head><meta charset='utf-8'></head><body>%s</body></html>"%(ans)), 'utf-8'))


class MyHTTPServer(HTTPServer):
    def __init__(self, host, port):
        print("run app server by python!")
        HTTPServer.__init__(self,  (host, port), MyHTTPRequestHandler)


if '__main__' == __name__:
    server_ip = "0.0.0.0"
    server_port = 8080
    if len(sys.argv) == 2:
        server_port = int(sys.argv[1])
    if len(sys.argv) == 3:
        server_ip = sys.argv[1]
        server_port = int(sys.argv[2])
    print("App server is running on http://%s:%s " % (server_ip, server_port))

    server = MyHTTPServer(server_ip, server_port)
    server.serve_forever()
