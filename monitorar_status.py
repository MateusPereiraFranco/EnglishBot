import requests
import json
import time

# ===============================================
# 1. DOCUMENTAÇÃO: Variáveis de Configuração
#    -> Use os mesmos valores do script anterior.
# ===============================================

# Base URL do seu servidor
BASE_URL = "https://free.uazapi.com" 

# O token da instância que VOCÊ usou no script anterior.
INSTANCIA_TOKEN = "01ec2309-28b3-42d4-84f0-ffeea6dc04d2" 
# (Substitua acima caso o token real seja diferente do que foi impresso, por segurança)

# Endpoint para verificar o status da instância
ENDPOINT_STATUS = "/instance/status" 

# ===============================================
# 2. DOCUMENTAÇÃO: Preparação da Requisição
# ===============================================

url_completa = BASE_URL + ENDPOINT_STATUS

# O cabeçalho (header) é o mesmo, requerendo o token de autenticação.
headers = {
    "token": INSTANCIA_TOKEN
}

# ===============================================
# 3. DOCUMENTAÇÃO: Função de Monitoramento
# ===============================================

def verificar_status():
    """Faz a requisição GET para obter o status da instância."""
    try:
        # Faz a requisição GET. Não é necessário enviar 'payload' no GET.
        response = requests.get(url_completa, headers=headers)
        
        if response.status_code == 200:
            dados = response.json()
            status_atual = dados.get("instance", {}).get("status")
            
            print(f"\nStatus atual da instância: {status_atual}")
            
            # Se o status for 'connecting', podemos ter o QR code agora.
            if status_atual == "connecting":
                paircode = dados.get("instance", {}).get("paircode")
                qrcode_base64 = dados.get("instance", {}).get("qrcode")

                if paircode:
                     print(f"**Pareamento:** Use o código {paircode} no seu WhatsApp para conectar.")
                
                # Se a API enviar um QR code (em base64), ele aparecerá aqui.
                if qrcode_base64:
                    print("QR Code disponível. Escaneie-o no seu celular.")
                
                print("Aguardando conexão...")
                return False # Não conectado
            
            elif status_atual == "connected":
                print("🥳 **CONECTADO!** Sua instância está pronta para enviar e receber mensagens.")
                return True # Conectado
            
            else: # Ex: disconnected
                print(f"⚠️ A instância está no estado: {status_atual}. Pode ser necessário reconectar.")
                return False

        else:
            print(f"❌ Erro ao verificar status. Status Code: {response.status_code}")
            print(response.text)
            return True # Paramos em caso de erro

    except requests.exceptions.RequestException as e:
        print(f"🚨 Erro de conexão (RequestException): {e}")
        return True # Paramos em caso de erro de conexão

# ===============================================
# 4. DOCUMENTAÇÃO: Loop de Execução
# ===============================================

print("Iniciando monitoramento. Pressione Ctrl+C para sair.")
conectado = False
while not conectado:
    conectado = verificar_status()
    if not conectado:
        # Espera 5 segundos antes de verificar novamente para não sobrecarregar a API
        time.sleep(5)