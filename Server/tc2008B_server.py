# TC2008B Modelación de Sistemas Multiagentes con gráficas computacionales
# Python server to interact with Unity via POST
# Sergio Ruiz-Loza, Ph.D. March 2021

from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import json

import firerescue

class Server(BaseHTTPRequestHandler):
    
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')  # Cambiado a application/json
        self.end_headers()
        
    def do_GET(self):
        self._set_response()
        self.wfile.write(json.dumps({"message": "Server is running"}).encode('utf-8'))

    def do_POST(self):
        try:
            # Ejecuta un paso de la simulación
            firerescue.model.step()
            
            # Recoge los datos de agentes y modelo
            json_agent = firerescue.model.datacollector.get_agent_vars_dataframe().to_dict()  # Usa .to_dict() para JSON anidado
            json_model = firerescue.model.datacollector.get_model_vars_dataframe().to_dict()

            # Construye la respuesta
            response_data = {
                "agents": json_agent,
                "model": json_model
            }

            pretty_response = json.dumps(response_data, indent=4).encode('utf-8')
            
            # Envía la respuesta
            self._set_response()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        
        except Exception as e:
            # Maneja errores y responde con un mensaje JSON
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_message = {"error": str(e)}
            self.wfile.write(json.dumps(error_message).encode('utf-8'))

# Configuración del servidor
def run(server_class=HTTPServer, handler_class=Server, port=8585):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f"Starting server on port {port}...\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Stopping server...\n")

if __name__ == '__main__':
    run()



