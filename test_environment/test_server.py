from http.server import SimpleHTTPRequestHandler, HTTPServer
import os

class TestServerHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            post_data = post_data.decode('utf-8')

            # very simple parsing
            if 'username=admin' in post_data and 'password=password' in post_data:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Login successful!")
            else:
                self.send_response(401)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Login failed!")
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/':
            self.path = 'login.html'
        return SimpleHTTPRequestHandler.do_GET(self)

def run(server_class=HTTPServer, handler_class=TestServerHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd on port {port}...')
    # Change CWD to the directory where the script is located
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    httpd.serve_forever()

if __name__ == "__main__":
    run()
