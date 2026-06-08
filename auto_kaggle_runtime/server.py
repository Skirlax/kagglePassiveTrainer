from __future__ import annotations

import functools
import http.server
import socketserver
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType


class ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


@dataclass
class SimpleFileServer:
    """Serve a local directory and expose it through an ngrok HTTP tunnel."""

    port: int = 8000
    host: str = ''
    url: str | None = None
    _httpd: ReusableThreadingTCPServer | None = field(default=None, init=False, repr=False)
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)

    def start(self, directory: str, ngrok_auth_token: str) -> None:
        self._configure(directory, ngrok_auth_token)
        assert self._httpd is not None
        self._httpd.serve_forever()

    def start_in_background(self, directory: str, ngrok_auth_token: str) -> threading.Thread:
        self._configure(directory, ngrok_auth_token)
        assert self._httpd is not None
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self._thread

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self.url is not None:
            self._disconnect_ngrok(self.url)
            self.url = None

    def __enter__(self) -> SimpleFileServer:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()

    def _configure(self, directory: str, ngrok_auth_token: str) -> None:
        if self._httpd is not None:
            raise RuntimeError('file server is already running')

        directory_path = Path(directory).resolve()
        if not directory_path.is_dir():
            raise NotADirectoryError(directory)

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory_path))
        self._httpd = ReusableThreadingTCPServer((self.host, self.port), handler)
        self.url = self._connect_ngrok(ngrok_auth_token)

    def _connect_ngrok(self, ngrok_auth_token: str) -> str:
        from pyngrok import ngrok

        ngrok.set_auth_token(ngrok_auth_token)
        public_url = ngrok.connect(str(self.port), 'http')
        return public_url.public_url

    @staticmethod
    def _disconnect_ngrok(url: str) -> None:
        from pyngrok import ngrok

        ngrok.disconnect(url)


def start_server(
    server: SimpleFileServer,
    directory: str,
    ngrok_auth_token: str,
) -> tuple[SimpleFileServer, threading.Thread]:
    thread = server.start_in_background(directory, ngrok_auth_token)
    return server, thread
