# api/analisador.py - VERSÃO FINAL DE DEPURAÇÃO

from http.server import BaseHTTPRequestHandler
import json
import os
import requests
import fitz  # PyMuPDF
import pypdf
import google.generativeai as genai
from io import BytesIO
import time

# --- CONFIGURAÇÃO E VERIFICAÇÃO CRÍTICA DA IA ---
API_KEY = os.environ.get("API_KEY") 

# LINHA DE DEPURAÇÃO: Se a chave não for encontrada, o programa quebra aqui com uma mensagem clara.
if not API_KEY:
    raise ValueError("ERRO CRÍTICO DE CONFIGURAÇÃO: A variável de ambiente API_KEY não foi encontrada ou está vazia no servidor. Verifique as configurações do Vercel.")

# Se a linha acima passar, significa que a chave FOI encontrada.
genai.configure(api_key=API_KEY)
MODELO_VISION = genai.GenerativeModel('gemini-pro-vision')
MODELO_ANALISE = genai.GenerativeModel('gemini-pro')

PROMPT_ANALISE_JURIDICA = """
Você é um especialista em direito imobiliário e sua função é realizar uma análise de risco em uma matrícula de imóvel para um leigo.
Seu objetivo é identificar e listar de forma simples e direta quaisquer riscos, dívidas ou problemas que impeçam ou atrapalhem a compra do imóvel.
Use uma linguagem clara, evite jargões jurídicos.

Concentre-se em encontrar: Penhoras, Hipotecas, Alienação Fiduciária, Indisponibilidade, Ações Judiciais, Dívidas de IPTU ou Condomínio.

Formate sua resposta em MARKDOWN, da seguinte maneira:

### 🕵️ Análise de Risco do Imóvel

**Resumo:**
(Diga em uma frase se o imóvel tem problemas sérios, moderados ou se parece limpo.)

---

**Pontos de Atenção Encontrados:**

*   **✅ [NOME DO PROBLEMA]:** (Ex: Penhora por Dívida Trabalhista).
    *   **O que significa?** (Explique de forma simples o que é e qual o risco para quem compra).
    *   **Detalhes:** (Cite o credor, valor ou número do processo se houver).

*   **⚠️ [OUTRO PROBLEMA]**
    *   **O que significa?** ...
    *   **Detalhes:** ...

**Conclusão e Próximo Passo:**
(Dê uma recomendação final. Ex: "Foram encontrados problemas sérios. É altamente recomendável consultar um advogado antes de prosseguir." ou "Aparentemente não há impedimentos, mas a análise de um profissional é sempre o mais seguro.")

Se NENHUM problema for encontrado, responda:

### ✅ Análise de Risco do Imóvel

**Resumo:**
Aparentemente, este imóvel não possui pendências ou ônus graves registrados na matrícula.

---

**Pontos de Atenção Encontrados:**
Nenhum ponto de atenção foi identificado neste documento.

**Conclusão e Próximo Passo:**
Esta análise preliminar não apontou riscos. Para total segurança, é sempre recomendável a consulta a um advogado especialista.
"""

def extrair_texto_pdf(pdf_bytes):
    try:
        texto = ""
        leitor = pypdf.PdfReader(BytesIO(pdf_bytes))
        for pagina in leitor.pages:
            texto_pagina = pagina.extract_text()
            if texto_pagina:
                texto += texto_pagina + "\n"
        if len(texto.strip()) > 100:
            return texto, "Extração Direta"
    except Exception:
        pass

    texto_ia = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for i, pagina in enumerate(doc):
        pix = pagina.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        response = MODELO_VISION.generate_content([
            "Transcreva todo o texto desta imagem de uma matrícula de imóvel.",
            {'mime_type': 'image/png', 'data': img_bytes}
        ])
        texto_ia.append(response.text)
        time.sleep(1) 
    return "\n\n".join(texto_ia), "OCR com IA"

def analisar_com_gemini(texto):
    if not texto or not texto.strip():
        return "Não foi possível extrair texto do documento para análise. O documento pode estar em branco ou corrompido."
    prompt_final = f"{PROMPT_ANALISE_JURIDICA}\n\n--- TEXTO DA MATRÍCULA ---\n\n{texto}"
    resposta = MODELO_ANALISE.generate_content(prompt_final)
    return resposta.text

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()

    def do_POST(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        pdf_url = data.get('url_do_pdf')

        if not pdf_url:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'erro': 'URL do PDF não fornecida.'}).encode())
            return

        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(pdf_url, headers=headers, timeout=60)
            response.raise_for_status()
            
            texto_extraido, _ = extrair_texto_pdf(response.content)
            relatorio = analisar_com_gemini(texto_extraido)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'analise': relatorio}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'erro': str(e)}).encode())
        return
