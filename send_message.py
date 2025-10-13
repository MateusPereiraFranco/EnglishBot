import requests
import json
import logging
from utils import BASE_URL, INSTANCIA_TOKEN 

log = logging.getLogger(__name__)
log.setLevel(logging.INFO) 

ENDPOINT_SEND_TEXT = "/send/text"
ENDPOINT_SEND_MENU = "/send/menu"


def send_whatsapp_message(to_number_jid: str, text_content: str):
    if not INSTANCIA_TOKEN or not BASE_URL:
        log.error("ERRO: Configurações BASE_URL ou INSTANCIA_TOKEN ausentes. Verifique o arquivo .env.")
        return None
        
    url_completa = BASE_URL + ENDPOINT_SEND_TEXT
    
    payload = {
        "number": to_number_jid,
        "text": text_content,
        "readchat": True,
        "delay": 1000
    }

    headers = {
        "token": INSTANCIA_TOKEN,
        "Content-Type": "application/json" 
    }

    try:
        response = requests.post(url_completa, headers=headers, json=payload)
        
        if response.status_code == 200:
            log.info("Mensagem enviada com sucesso para %s", to_number_jid)
            return response.json()
        else:
            log.error("Falha ao enviar mensagem. Status: %s. Detalhes: %s", 
                      response.status_code, response.text)
            return None

    except requests.exceptions.RequestException as e:
        log.error("Erro de conexão ao enviar mensagem: %s", e)
        return None


def send_button_menu(to_number_jid: str, text_content: str, choices: list):
    
    if not INSTANCIA_TOKEN or not BASE_URL:
        log.error("ERRO: Configurações ausentes no .env para envio de menu.")
        return None
        
    url_completa = BASE_URL + ENDPOINT_SEND_MENU
    
    payload = {
        "number": to_number_jid,
        "type": "button",
        "text": text_content,
        "choices": choices,
        "footerText": "Clique para responder. Sua escolha não aparecerá como texto digitado.",
        "readchat": True,
        "delay": 500
    }

    headers = {
        "token": INSTANCIA_TOKEN,
        "Content-Type": "application/json" 
    }

    try:
        response = requests.post(url_completa, headers=headers, json=payload)
        
        if response.status_code == 200:
            log.info("Menu de botões enviado com sucesso para %s", to_number_jid)
            return response.json()
        else:
            log.error("Falha ao enviar menu. Status: %s. Detalhes: %s", 
                      response.status_code, response.text)
            return None

    except requests.exceptions.RequestException as e:
        log.error("Erro de conexão ao enviar menu: %s", e)
        return None


if __name__ == '__main__':
    print("Módulo de envio carregado com sucesso.")