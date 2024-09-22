from pyngrok import ngrok
import http.server
import socketserver
import os
import threading


class SimpleFileServer:
    def __init__(self, port: int = 8000):
        self.port = port
        self.handler = http.server.SimpleHTTPRequestHandler
        self.url = None

    def start(self, directory: str, ngrok_auth_token: str):
        os.chdir(directory)
        httpd = socketserver.TCPServer(("", self.port), self.handler)
        ngrok.set_auth_token(ngrok_auth_token)
        public_url = ngrok.connect(str(self.port), "http")
        self.url = public_url.public_url
        httpd.serve_forever()


def start_server(server: SimpleFileServer,directory: str, ngrok_auth_token: str):
    thread = threading.Thread(target=server.start, args=(directory, ngrok_auth_token))
    thread.daemon = True
    thread.start()
    return server, thread
