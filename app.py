from http.server import SimpleHTTPRequestHandler, HTTPServer

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h1>Hello World! O fluxo esta funcionando.</h1>")

server = HTTPServer(("0.0.0.0", 8080), Handler)
server.serve_forever()
