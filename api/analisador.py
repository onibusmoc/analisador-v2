# api/analisador.py - VERSÃO "TESTE DE FUMAÇA"

from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    
    # Responde à "ligação de verificação" (OPTIONS)
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()

    # Responde à "ligação principal" (POST)
    def do_POST(self):
        self.send_response(200) # Responde com SUCESSO
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # Cria uma mensagem de resposta simples
        resposta = {
            'analise': '✅ SUCESSO! A comunicação com o servidor está funcionando perfeitamente.'
        }
        
        # Envia a resposta de volta
        self.wfile.write(json.dumps(resposta).encode('utf-8'))
        return
