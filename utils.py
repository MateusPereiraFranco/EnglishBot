import requests
import json
import logging
from dotenv import load_dotenv
import os

# Carrega as variáveis do arquivo .env
load_dotenv()

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# ===============================================
# 1. CONFIGURAÇÕES GERAIS (Centralizadas no .env)
# ===============================================

BASE_URL = os.getenv("BASE_URL")
INSTANCIA_TOKEN = os.getenv("INSTANCIA_TOKEN")
NGROK_URL = os.getenv("NGROK_URL")


# ===============================================
# 2. FUNÇÃO: VERIFICAR STATUS DA INSTÂNCIA
# ===============================================

def get_instance_status() -> str:
    """
    Faz uma requisição GET para /instance/status e retorna o estado da conexão.
    
    :return: Uma string contendo o status ('connected', 'disconnected', 'ERROR', etc.).
    """
    if not INSTANCIA_TOKEN or not BASE_URL:
        return "ERROR: Token ou Base URL ausentes no .env."

    url_completa = BASE_URL + "/instance/status"
    
    headers = {
        "token": INSTANCIA_TOKEN
    }

    try:
        response = requests.get(url_completa, headers=headers)
        
        if response.status_code == 200:
            dados = response.json()
            # Acessa o status dentro da estrutura da resposta da uazapiGO
            status_atual = dados.get("instance", {}).get("status")
            return status_atual.upper() if status_atual else "STATUS NOT FOUND"
        
        else:
            return f"API ERROR: HTTP {response.status_code} - Verifique o token."

    except requests.exceptions.RequestException as e:
        return f"CONNECTION ERROR: {e}"


# ===============================================
# 3. FUNÇÃO: CONFIGURAR WEBHOOK
# ===============================================

def configure_webhook(webhook_url: str) -> bool:
    """
    Configura o Webhook na API uazapiGO usando as variáveis de ambiente.
    ... [Código da função configure_webhook permanece o mesmo] ...
    """
    if not INSTANCIA_TOKEN:
        log.error("🚨 ERRO: INSTANCIA_TOKEN não está configurado. Verifique o arquivo .env.")
        return False
        
    if not webhook_url:
        log.error("🚨 ERRO: O URL do Webhook está vazio.")
        return False

    url_completa = BASE_URL + "/webhook"
    
    payload = {
        "enabled": True,
        "url": webhook_url,
        "events": ["messages", "connection"],
        "excludeMessages": ["wasSentByApi"] 
    }

    headers = {
        "token": INSTANCIA_TOKEN,
        "Content-Type": "application/json" 
    }

    print(f"Tentando configurar Webhook no endpoint: {url_completa}")
    print(f"Com o URL: {webhook_url}")

    try:
        response = requests.post(url_completa, headers=headers, json=payload)

        if response.status_code == 200:
            log.info("✅ Webhook configurado com sucesso! Status Code: 200")
            return True
        else:
            log.error("❌ Erro ao configurar Webhook. Status: %s. Detalhes: %s", 
                      response.status_code, response.text)
            return False

    except requests.exceptions.RequestException as e:
        log.error("🚨 Erro de conexão ao configurar Webhook: %s", e)
        return False


# ===============================================
# 4. EXEMPLO DE USO
# ===============================================

if __name__ == '__main__':
    # Este bloco demonstra como usar as funções
    
    # 1. Checagem de Status
    current_status = get_instance_status()
    print(f"\n--- Status Atual da Instância ---")
    print(f"Status: {current_status}")
    
    # 2. Reconfiguração do Webhook (se a URL do ngrok estiver no .env)
    if NGROK_URL:
        print("\n--- Reconfiguração do Webhook ---")
        if configure_webhook(NGROK_URL):
            print("STATUS: Configuração de Webhook realizada com sucesso.")
        else:
            print("STATUS: Falha na configuração do Webhook.")
    else:
        print("\n⚠️ NGROK_URL não definida no .env. Ignorando reconfiguração de webhook.")