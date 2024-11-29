# TC2008B Modelación de Sistemas Multiagentes con gráficas computacionales
# Python server to interact with Unity via POST
# Sergio Ruiz-Loza, Ph.D. March 2021

from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import json


class Server(BaseHTTPRequestHandler):
    
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
    def do_GET(self):
        self._set_response()
        self.wfile.write("Get".format(0).encode('utf-8'))

    def do_POST(self):

        infoModel = './simulation_data.json'

        # Intentamos abrir y leer el archivo JSON
        try:
            with open(infoModel, 'r') as file:
                simulation_data = json.load(file)  # Leer el contenido del archivo JSON

            # Establecer la respuesta como JSON
            self._set_response(content_type='application/json')

            # Convertimos el contenido del archivo a JSON y lo enviamos como respuesta
            self.wfile.write(json.dumps(simulation_data).encode('utf-8'))
        
        except Exception as e:
            # Si hay un error (por ejemplo, el archivo no existe), enviamos un error 500
            self.send_error(500, f"Error al leer el archivo JSON: {str(e)}")



def run(server_class=HTTPServer, handler_class=Server, port=8585):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info("Starting httpd...\n") # HTTPD is HTTP Daemon!
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:   # CTRL+C stops the server
        pass
    httpd.server_close()
    logging.info("Stopping httpd...\n")

if __name__ == '__main__':
    from sys import argv
    
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()


