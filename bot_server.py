from fastapi import FastAPI, Request, HTTPException
import logging
import os
from dotenv import load_dotenv
from send_message import send_whatsapp_message, send_button_menu
from utils import get_instance_status
from datetime import datetime

from database import init_db, get_db, Usuario, Licao
from sqlalchemy.orm import Session
from typing import Annotated
from fastapi import Depends
from ai_service import get_ai_response 

load_dotenv()

logging.getLogger('werkzeug').setLevel(logging.ERROR)
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ("true", "1", "t")

init_db()

app = FastAPI(title="English Bot Server", debug=DEBUG_MODE)


MENU_PRINCIPAL = (
    "Olá! Bem-vindo ao English Bot! Escolha uma opção:\n\n"
    "1. Meu Nível de Inglês e Plano de Estudos\n" 
    "2. Iniciar Lição de Vocabulário (Quiz)\n"
    "3. Prática de Conversação com IA (PLN)\n"
    "4. Status da Conexão\n"
    "5. Sair / Desligar (digite 'parar')"
)
ESTADO_MENU = "menu_principal"
ESTADO_ESTUDANDO_LICAO = "estudando_licao"
ESTADO_ESCOLHA_NIVEL = "escolha_nivel"
ESTADO_AVALIACAO_INICIAL = "avaliacao_inicial"
ESTADO_AGUARDANDO_NIVEL_DIGITADO = "aguardando_nivel_digitado" 

def enviar_licao(db: Session, remetente_jid: str, licao: Licao, texto_inicial: str):
    
    opcoes = [
        f"A: {licao.opcao_a.split('. ', 1)[-1]}|A",
        f"B: {licao.opcao_b.split('. ', 1)[-1]}|B",
        f"C: {licao.opcao_c.split('. ', 1)[-1]}|C",
        f"D: {licao.opcao_d.split('. ', 1)[-1]}|D",
    ]
    
    mensagem_texto = (
        f"{texto_inicial}\n\n"
        f"*{licao.topico}*\n"
        f"Responda: {licao.texto_pergunta}"
    )
    
    send_button_menu(remetente_jid, mensagem_texto, opcoes)

@app.get("/")
def read_root():
    return {"message": "English Bot Server está ativo!"}


@app.post('/webhook')
async def handle_webhook(request: Request, db: Annotated[Session, Depends(get_db)]):
    try:
        data = await request.json()
        evento_dados = data[0] if isinstance(data, list) and len(data) > 0 else data

        evento_tipo = evento_dados.get('EventType')
        mensagem = evento_dados.get('message', {})
        
        if evento_tipo == 'messages' and mensagem.get('fromMe') == False:
            
            remetente_jid = mensagem.get('sender') 
            texto_recebido_payload = mensagem.get('text', '') or mensagem.get('content', '') or ''
            
            if isinstance(texto_recebido_payload, dict):
                texto_recebido = texto_recebido_payload.get('selectedID', '')
            else:
                texto_recebido = str(texto_recebido_payload).lower().strip()

            resposta_usuario = texto_recebido.upper() 
            
            usuario = db.query(Usuario).filter(Usuario.wa_jid == remetente_jid).first()
            if not usuario:
                usuario = Usuario(wa_jid=remetente_jid, nome=mensagem.get('senderName', 'Usuário Novo'), estado=ESTADO_MENU)
                db.add(usuario)
            
            usuario.ultima_interacao = datetime.now()
            
            print(f"\n[USER: {usuario.wa_jid}] Estado: {usuario.estado}, Lição: {usuario.pergunta_atual_id}, Recebeu: '{texto_recebido}'")

            resposta = ""

            if texto_recebido in ["oi", "olá", "ola", "menu"]:
                usuario.estado = ESTADO_MENU
                resposta = MENU_PRINCIPAL
            
            elif usuario.estado == ESTADO_ESTUDANDO_LICAO:
                
                licao = db.query(Licao).filter(Licao.id == usuario.pergunta_atual_id).first()
                
                if licao and resposta_usuario in ["A", "B", "C", "D"]:
                    letra_correta = licao.resposta_correta.upper()
                    
                    if resposta_usuario == letra_correta:
                        usuario.pontuacao += 1
                        proxima_licao = db.query(Licao).filter(Licao.id == usuario.pergunta_atual_id + 1).first()
                        
                        if proxima_licao:
                            usuario.pergunta_atual_id += 1
                            enviar_licao(db, remetente_jid, proxima_licao, "✅ **Correto!** Excelente. Próxima Lição:")
                        else:
                            usuario.estado = ESTADO_MENU
                            usuario.pergunta_atual_id = 0
                            resposta = (
                                "🎉 **Parabéns! Você completou a lição introdutória!**\n"
                                f"Total de acertos: {usuario.pontuacao}.\n\n"
                                f"Voltando ao menu principal.\n\n{MENU_PRINCIPAL}"
                            )
                        
                    else:
                        usuario.estado = ESTADO_MENU
                        usuario.pergunta_atual_id = 0
                        usuario.pontuacao = 0
                        
                        resposta = (
                            f"❌ **Incorreto.** A resposta correta para '{licao.texto_pergunta}' era {letra_correta}.\n"
                            "Estude mais e tente novamente!\n\n"
                            f"Voltando ao menu principal.\n\n{MENU_PRINCIPAL}"
                        )
                else:
                    resposta = "Comando inválido. Por favor, clique em um dos botões (A, B, C ou D)."

            elif usuario.estado == ESTADO_ESCOLHA_NIVEL:
                print(f"escolhido {texto_recebido}")
                if texto_recebido == "a":
                    
                    usuario.estado = ESTADO_AGUARDANDO_NIVEL_DIGITADO 
                    resposta = (
                        "Certo. Por favor, digite *apenas* o seu nível de inglês atual (ex: Iniciante, Intermediário Alto, Avançado)."
                    )
                    
                elif texto_recebido == "b":
                    usuario.estado = ESTADO_AVALIACAO_INICIAL 
                    resposta = "A avaliação de nível por IA (Opção B) está em desenvolvimento. Por favor, tente a Opção A ou volte ao menu."
                    usuario.estado = ESTADO_MENU

                else:
                    resposta = "Opção inválida. Por favor, escolha A ou B para continuar."
            
            elif usuario.estado == ESTADO_AGUARDANDO_NIVEL_DIGITADO:
    
                nivel_digitado = texto_recebido.upper()
                usuario.nivel_ingles = nivel_digitado
                usuario.estado = ESTADO_MENU

                prompt_plano = (
                    f"Crie um plano de estudo de inglês de 3 passos focado em um aluno de nível {nivel_digitado}. "
                    "O plano deve ser conciso e motivador, focado em vocabulário e gramática. Use emojis."
                )

                plano_estudo = get_ai_response(prompt_plano)

                resposta = (
                    f"✨ Nível salvo como: *{nivel_digitado}*.\n\n"
                    "🧠 **Seu Plano de Estudos Personalizado:**\n"
                    f"{plano_estudo}\n\n"
                    f"Voltando ao menu principal.\n\n{MENU_PRINCIPAL}"
                )

            elif usuario.estado == ESTADO_AVALIACAO_INICIAL:
                
                resposta = "A avaliação de nível por IA (Opção B) está em desenvolvimento. Por favor, tente a Opção A ou volte ao menu."
                usuario.estado = ESTADO_MENU

            elif usuario.estado in ["inicio", ESTADO_MENU, "finalizado", "conversando_ia"]:
                
                if texto_recebido == "1" or texto_recebido.lower() == "meu nível de inglês e plano de estudos":
                    usuario.estado = ESTADO_ESCOLHA_NIVEL
                    resposta = (
                        "Ótima escolha! Para criar seu plano, como você quer definir seu nível?\n\n"
                        "A. Digitar meu nível (Ex: Iniciante, Intermediário Alto)\n"
                        "B. Fazer um pequeno Teste de Nível com a IA (Em Breve)"
                    )
                
                elif texto_recebido == "2" or texto_recebido.lower() == "iniciar lição de vocabulário":
                    licao_inicial = db.query(Licao).filter(Licao.id == 1).first()
                    
                    if licao_inicial:
                        usuario.estado = ESTADO_ESTUDANDO_LICAO
                        usuario.pergunta_atual_id = 1
                        usuario.pontuacao = 0
                        
                        enviar_licao(db, remetente_jid, licao_inicial, "***-- INICIANDO LIÇÕES --***")
                    else:
                        resposta = "🚨 Erro: Nenhuma lição de inglês encontrada no banco de dados. Execute 'python adicionar_licoes.py'."

                elif texto_recebido in ["4", "status"]:
                    usuario.estado = ESTADO_MENU
                    status = get_instance_status()
                    resposta = f"📢 STATUS DA INSTÂNCIA:\n\nSua instância está atualmente: *{status}*.\n\nSe o status for 'DISCONNECTED', seu token pode ter expirado."
                
                elif texto_recebido in ["5", "sair", "parar"]:
                    usuario.estado = "finalizado"
                    resposta = "Certo. Saindo do sistema. Para reiniciar, envie 'oi' ou 'menu'."
                
                else:
                    if texto_recebido == "3" or usuario.estado == "conversando_ia":
                        
                        if texto_recebido not in ["3", "prática de conversação com ia"]:
                             pergunta_para_ia = texto_recebido
                        else:
                             pergunta_para_ia = "Me diga sobre o que podemos conversar em inglês. Ex: 'Qual a diferença entre look, see e watch?'"
                        
                        usuario.estado = "conversando_ia"
                        print(f"🤖 ENVIANDO PERGUNTA PARA IA: '{pergunta_para_ia}'")
                        resposta = get_ai_response(pergunta_para_ia)
                    
                    else:
                        resposta = f"Não entendi '{texto_recebido}'. Por favor, digite 'oi' ou uma opção numérica do menu."
                        usuario.estado = ESTADO_MENU

            db.commit()

            if resposta and usuario.estado != ESTADO_ESTUDANDO_LICAO: 
                 send_whatsapp_message(remetente_jid, resposta)

        return {"status": "ok"}
    
    except Exception as e:
        logging.error(f"🚨 Erro no processamento do webhook: {e}")
        return {"status": "error", "message": "Erro interno do bot"}

if __name__ == '__main__':
    import uvicorn
    log_level = "info" if DEBUG_MODE else "warning"
    
    print("🚀 Servidor Webhook do Bot (FastAPI) iniciado.")
    print("Aguardando eventos POST em: http://127.0.0.1:8000/webhook")
    
    uvicorn.run("bot_server:app", host='0.0.0.0', port=8000, log_level=log_level, reload=DEBUG_MODE)