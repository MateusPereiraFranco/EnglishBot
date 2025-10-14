from fastapi import FastAPI, Request, HTTPException
import logging
import os
from dotenv import load_dotenv
from send_message import send_whatsapp_message, send_button_menu
from utils import get_instance_status
from datetime import datetime
import json
from ai_service import get_ai_response, get_dynamic_exercise 

from database import init_db, get_db, Usuario, Licao
from sqlalchemy.orm import Session
from typing import Annotated
from fastapi import Depends

load_dotenv()

logging.getLogger('werkzeug').setLevel(logging.ERROR)
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ("true", "1", "t")

init_db()

app = FastAPI(title="English Bot Server", debug=DEBUG_MODE)

# ===============================================
# CONSTANTES DE FLUXO E MENUS
# ===============================================

ESTADO_MENU = "menu_principal"
ESTADO_ESTUDANDO_LICAO = "estudando_licao"
ESTADO_ESCOLHA_NIVEL = "escolha_nivel"
ESTADO_AVALIACAO_INICIAL = "avaliacao_inicial"
ESTADO_AGUARDANDO_NIVEL_DIGITADO = "aguardando_nivel_digitado"
ESTADO_AGUARDANDO_RESPOSTA_DINAMICA = "aguardando_resposta_dinamica"


# CONSTANTES GLOBAIS DE MENU
OPCOES_MENU_PRINCIPAL = {
    "1. Meu Nível e Plano de Estudos": "1",
    "2. Iniciar Lição (Dinâmica)": "2",
    "3. Prática de Conversação com IA (PLN)": "3",
    "4. Status da Conexão": "4",
    "5. Sair / Desligar": "5",
}
TEXTO_MENU_PRINCIPAL = "Olá! Bem-vindo ao English Bot! Escolha uma opção:"

OPCOES_ESCOLHA_NIVEL = {
    "A. Digitar meu nível": "A",
    "B. Fazer um pequeno Teste de Nível (Em Breve)": "B",
}
TEXTO_ESCOLHA_NIVEL = "Ótima escolha! Para criar seu plano, como você quer definir seu nível?"

OPCOES_NIVEL_DIGITADO = {
    "INICIANTE (POUCO CONHECIMENTO)": "INICIANTE",
    "INTERMEDIARIO (MÉDIO CONHECIMENTO)": "INTERMEDIARIO",
    "ALTO (ALTO TEMPO)" : "ALTO",
    "AVANÇADO (TEM UM CONHECIMENTO EXEPCIONAL)" : "AVANÇADO",
}
TEXTO_NIVEL_DIGITADO = "Certo. Por favor, escolha seu nível atual para gerar seu plano."


# ===============================================
# FUNÇÕES AUXILIARES
# ===============================================

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

def enviar_menu_botoes(remetente_jid: str, texto_principal: str, opcoes_dict: dict):
    
    opcoes_list = [f"{texto_visivel}|{id_controle}" for texto_visivel, id_controle in opcoes_dict.items()]
    send_button_menu(remetente_jid, texto_principal, opcoes_list)

def enviar_resposta_de_texto(remetente_jid: str, text: str):
    send_whatsapp_message(remetente_jid, text)

def get_opcao_texto(letra: str, exercicio_data: dict) -> str:
    """Extrai o texto completo da opção A, B, C ou D do JSON de exercício."""
    letra_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
    opcoes = exercicio_data.get('opcoes', [])
    index = letra_map.get(letra.upper())
    
    if index is not None and len(opcoes) > index:
        return opcoes[index]
    return "Texto da Opção não encontrado"

def enviar_reforco_ia(remetente_jid: str, user_level: str, pergunta: str, resposta_errada_texto: str, resposta_certa_texto: str):
    
    prompt_reforco = (
        f"O aluno de nível {user_level} errou a pergunta: '{pergunta}'. "
        f"A resposta que ele deu foi: '{resposta_errada_texto}'. A resposta correta era: '{resposta_certa_texto}'. "
        "Crie uma explicação concisa e didática sobre o erro cometido e dê uma dica de estudo."
    )
    
    explicacao_ia = get_ai_response(prompt_reforco)
    
    enviar_resposta_de_texto(remetente_jid,
        f"❌ **Incorreto!** A resposta correta era *{resposta_certa_texto}*.\n\n"
        f"📢 **Reforço:** {explicacao_ia}\n"
        "Voltando ao menu principal."
    )
    enviar_menu_botoes(remetente_jid, TEXTO_MENU_PRINCIPAL, OPCOES_MENU_PRINCIPAL)


# ===============================================
# ROTAS DO FASTAPI
# ===============================================

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
            
            # EXTRAÇÃO DE CLIQUE LIMPA (selectedID)
            if isinstance(texto_recebido_payload, dict):
                texto_recebido = texto_recebido_payload.get('selectedID', '')
                
                # REMOÇÃO DA LÓGICA INCORRETA: o botão interativo retorna o ID de controle limpo.
                # A lógica de limpeza de prefixo aqui era o erro.
                # if ':' in texto_recebido:
                #    texto_recebido = texto_recebido.split(':', 1)[1].strip()

            else:
                texto_recebido = str(texto_recebido_payload).lower().strip()

            # O valor clicado (se for de botão) está agora em texto_recebido.
            # Se for clique de opção, o valor é o texto da opção em maiúsculas (ex: "AM")
            resposta_usuario = texto_recebido.upper() 
            
            # --- Gerenciamento de Usuário e Estado ---
            usuario = db.query(Usuario).filter(Usuario.wa_jid == remetente_jid).first()
            is_novo_usuario = False
            if not usuario:
                usuario = Usuario(wa_jid=remetente_jid, nome=mensagem.get('senderName', 'Usuário Novo'), nivel_ingles='Não definido', estado=ESTADO_ESCOLHA_NIVEL)
                db.add(usuario)
                is_novo_usuario = True
            
            elif usuario.nivel_ingles is None or usuario.nivel_ingles == 'Não definido':
                 if usuario.estado == ESTADO_MENU:
                     usuario.estado = ESTADO_ESCOLHA_NIVEL

            usuario.ultima_interacao = datetime.now()
            
            print(f"\n[USER: {usuario.wa_jid}] Estado: {usuario.estado}, Lição: {usuario.pergunta_atual_id}, Recebeu: '{texto_recebido}'")

            # ==========================================================
            # LÓGICA DO FLUXO (State Machine)
            # ==========================================================

            # A) AÇÃO DE RESET (oi, olá, menu)
            if texto_recebido in ["oi", "olá", "ola", "menu"]:
                if usuario.nivel_ingles is None or usuario.nivel_ingles == 'Não definido':
                    usuario.estado = ESTADO_ESCOLHA_NIVEL
                    enviar_menu_botoes(remetente_jid, TEXTO_ESCOLHA_NIVEL, OPCOES_ESCOLHA_NIVEL)
                else:
                    usuario.estado = ESTADO_MENU
                    enviar_menu_botoes(remetente_jid, TEXTO_MENU_PRINCIPAL, OPCOES_MENU_PRINCIPAL)
            
            
            # B) ESTADO: ESTUDANDO LIÇÃO (Lógica do Quiz de Inglês) - Usada para o quiz estático (Licao)
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
                            enviar_resposta_de_texto(remetente_jid,
                                "🎉 **Parabéns! Você completou a lição introdutória!**\n"
                                f"Total de acertos: {usuario.pontuacao}.\n\n"
                                f"Voltando ao menu principal."
                            )
                            enviar_menu_botoes(remetente_jid, TEXTO_MENU_PRINCIPAL, OPCOES_MENU_PRINCIPAL)
                        
                    else:
                        usuario.estado = ESTADO_MENU
                        usuario.pergunta_atual_id = 0
                        usuario.pontuacao = 0
                        
                        enviar_resposta_de_texto(remetente_jid,
                            f"❌ **Incorreto.** A resposta correta para '{licao.texto_pergunta}' era {letra_correta}.\n"
                            "Estude mais e tente novamente!\n\n"
                            f"Voltando ao menu principal."
                        )
                        enviar_menu_botoes(remetente_jid, TEXTO_MENU_PRINCIPAL, OPCOES_MENU_PRINCIPAL)
                        
                else:
                    enviar_resposta_de_texto(remetente_jid, "Comando inválido. Por favor, clique em um dos botões (A, B, C ou D).")


            # C) ESTADO: AGUARDANDO RESPOSTA DINÂMICA (NOVO LOOP DE CORREÇÃO)
            elif usuario.estado == ESTADO_AGUARDANDO_RESPOSTA_DINAMICA:
                
                # 1. Checagem: O usuário respondeu à questão de Múltipla Escolha?
                # resposta_usuario AGORA contém o TEXTO da opção clicada (ex: "IS", "AM")
                if usuario.exercicio_tipo == "choice" and resposta_usuario: 
                    
                    # 1. Obtemos o gabarito de TEXTO salvo
                    gabarito_texto = usuario.exercicio_correto_texto.upper() # Gabarito: "IS"
                    resposta_aluno_texto_limpa = resposta_usuario.upper() # Resposta do clique: "AM"
                    
                    # 2. **COMPARAÇÃO CORRIGIDA:** Compara o TEXTO do clique com o TEXTO CORRETO salvo.
                    if resposta_aluno_texto_limpa == gabarito_texto: 
                        # ACERTOU
                        usuario.total_acertos += 1
                        usuario.total_exercicios_feitos += 1
                        
                        enviar_resposta_de_texto(remetente_jid, "✅ **Correto!** Gerando próximo exercício dinâmico...")
                        
                        # Simula o clique na Opção 2 para gerar o novo exercício (continua no próximo bloco)
                        usuario.estado = ESTADO_MENU 
                        resposta_usuario = "2" 
                        
                    else:
                        # ERROU: Explica o erro e volta ao menu
                        usuario.total_exercicios_feitos += 1
                        
                        # NOVO FLUXO: Lógica de reforço da IA
                        dados_exercicio_original = json.loads(usuario.exercicio_dados_json)
                        pergunta_original = dados_exercicio_original.get("pergunta")
                        
                        enviar_reforco_ia(remetente_jid,
                            usuario.nivel_ingles,
                            pergunta_original,
                            resposta_aluno_texto_limpa,
                            gabarito_texto
                        )
                        usuario.estado = ESTADO_MENU


                # 2. Checagem: O usuário respondeu à questão ABERTA?
                elif usuario.exercicio_tipo == "open":
                    
                    # IMPLEMENTAÇÃO FUTURA: AQUI IRÁ A LÓGICA DE CORREÇÃO DA RESPOSTA ABERTA PELA IA
                    enviar_resposta_de_texto(remetente_jid, "Corrigindo sua resposta aberta com a IA... (Em breve)")
                    usuario.estado = ESTADO_MENU
                    enviar_menu_botoes(remetente_jid, TEXTO_MENU_PRINCIPAL, OPCOES_MENU_PRINCIPAL)
                    
                else:
                    enviar_resposta_de_texto(remetente_jid, "Comando inválido. Por favor, clique em um dos botões (A, B, C ou D).")

            
            # D) ESTADO: ESCOLHA DE NÍVEL (Trata A/B)
            elif usuario.estado == ESTADO_ESCOLHA_NIVEL:
                
                if resposta_usuario == "A":
                    usuario.estado = ESTADO_AGUARDANDO_NIVEL_DIGITADO 
                    enviar_menu_botoes(remetente_jid, TEXTO_NIVEL_DIGITADO, OPCOES_NIVEL_DIGITADO)

                elif resposta_usuario == "B":
                    usuario.estado = ESTADO_AVALIACAO_INICIAL 
                    enviar_resposta_de_texto(remetente_jid, "A avaliação de nível por IA (Opção B) está em desenvolvimento. Por favor, tente a Opção A ou volte ao menu.")
                    usuario.estado = ESTADO_MENU
                    enviar_menu_botoes(remetente_jid, TEXTO_MENU_PRINCIPAL, OPCOES_MENU_PRINCIPAL)
                
                elif is_novo_usuario or (usuario.nivel_ingles is None or usuario.nivel_ingles == 'Não definido'):
                    enviar_menu_botoes(remetente_jid, TEXTO_ESCOLHA_NIVEL, OPCOES_ESCOLHA_NIVEL)
                
                else:
                    enviar_menu_botoes(remetente_jid, "Opção inválida. Por favor, escolha A ou B para continuar.", OPCOES_ESCOLHA_NIVEL)


            # E) ESTADO: AGUARDANDO NÍVEL DIGITADO
            elif usuario.estado == ESTADO_AGUARDANDO_NIVEL_DIGITADO:
                
                nivel_selecionado = resposta_usuario 
                
                if nivel_selecionado in OPCOES_NIVEL_DIGITADO.values():
                    usuario.nivel_ingles = nivel_selecionado
                    usuario.estado = ESTADO_MENU
                    
                    prompt_plano = (
                        f"Crie um plano de estudo de inglês de 3 passos focado em um aluno de nível {nivel_selecionado}. "
                        "O plano deve ser conciso e motivador, focado em vocabulário e gramática. Use emojis."
                    )
                    
                    plano_estudo = get_ai_response(prompt_plano)
                    
                    enviar_resposta_de_texto(remetente_jid,
                        f"✨ Nível salvo como: *{nivel_selecionado}*.\n\n"
                        "🧠 **Seu Plano de Estudos Personalizado:**\n"
                        f"{plano_estudo}\n\n"
                        "Voltando ao menu principal."
                    )
                    enviar_menu_botoes(remetente_jid, TEXTO_MENU_PRINCIPAL, OPCOES_MENU_PRINCIPAL)

                else:
                    enviar_resposta_de_texto(remetente_jid, f"Nível inválido: {resposta_usuario}. Por favor, escolha uma opção dos botões.")
                    enviar_menu_botoes(remetente_jid, TEXTO_NIVEL_DIGITADO, OPCOES_NIVEL_DIGITADO) 
                

            # F) ESTADO: OPÇÕES DO MENU (Ações de 1 a 5, IA, etc.)
            elif usuario.estado in ["inicio", ESTADO_MENU, "finalizado", "conversando_ia", ESTADO_AVALIACAO_INICIAL]:
                
                if resposta_usuario in OPCOES_MENU_PRINCIPAL.values():
                    
                    if resposta_usuario == "1":
                        usuario.estado = ESTADO_ESCOLHA_NIVEL
                        enviar_menu_botoes(remetente_jid, TEXTO_ESCOLHA_NIVEL, OPCOES_ESCOLHA_NIVEL)

                    elif resposta_usuario == "2":
                        if usuario.nivel_ingles is None or usuario.nivel_ingles == 'Não definido':
                            enviar_resposta_de_texto(remetente_jid, "🚨 Por favor, defina seu nível na Opção 1 antes de iniciar as lições.")
                            enviar_menu_botoes(remetente_jid, TEXTO_ESCOLHA_NIVEL, OPCOES_ESCOLHA_NIVEL)
                            usuario.estado = ESTADO_ESCOLHA_NIVEL
                            return
                            
                        # --- GERAÇÃO DO EXERCÍCIO DINÂMICO (CORRIGIDO) ---
                        usuario.estado = ESTADO_AGUARDANDO_RESPOSTA_DINAMICA
                        user_level = usuario.nivel_ingles
                        
                        json_exercicio_str = get_dynamic_exercise(user_level)
                        
                        try:
                            exercicio = json.loads(json_exercicio_str)
                            
                            usuario.exercicio_tipo = exercicio.get("tipo")
                            
                            # O gabarito é o TEXTO CORRETO (ex: "IS") gerado pela IA.
                            usuario.exercicio_correto_texto = exercicio.get("correta").upper() 
                            usuario.exercicio_dados_json = json_exercicio_str
                            
                            if exercicio.get("tipo") == "choice":
                                
                                # CRÍTICO: O ID DE CONTROLE AGORA É O TEXTO DA OPÇÃO (em maiúsculas)
                                # Ex: O botão de "Am" retorna "AM", o de "Is" retorna "IS".
                                opcoes_choice = {
                                    f"A: {exercicio['opcoes'][0]}": exercicio['opcoes'][0].upper(),
                                    f"B: {exercicio['opcoes'][1]}": exercicio['opcoes'][1].upper(),
                                    f"C: {exercicio['opcoes'][2]}": exercicio['opcoes'][2].upper(),
                                    f"D: {exercicio['opcoes'][3]}": exercicio['opcoes'][3].upper(),
                                }
                                enviar_menu_botoes(remetente_jid, f"📝 **EXERCÍCIO DINÂMICO**\n\n{exercicio['pergunta']}", opcoes_choice)
                                
                            elif exercicio.get("tipo") == "open":
                                enviar_resposta_de_texto(remetente_jid, f"📝 **EXERCÍCIO ABERTO**\n\n{exercicio['pergunta']}\n\n*Por favor, digite sua resposta completa.*")
                                
                            else:
                                enviar_resposta_de_texto(remetente_jid, "⚠️ A IA gerou um exercício em um formato inválido. Tente novamente.")

                        except json.JSONDecodeError:
                            enviar_resposta_de_texto(remetente_jid, f"⚠️ Erro: A IA não retornou o exercício em um formato válido. Resposta da IA: {json_exercicio_str}")
                        
                    elif resposta_usuario == "3":
                        usuario.estado = "conversando_ia"
                        enviar_resposta_de_texto(remetente_jid, "🎉 **Conversação com IA ativada!**\n\nPergunte-me qualquer coisa sobre inglês.")

                    elif resposta_usuario == "4":
                        usuario.estado = ESTADO_MENU
                        status = get_instance_status()
                        enviar_resposta_de_texto(remetente_jid, f"📢 STATUS DA INSTÂNCIA:\n\nSua instância está atualmente: *{status}*.")
                        enviar_menu_botoes(remetente_jid, TEXTO_MENU_PRINCIPAL, OPCOES_MENU_PRINCIPAL)

                    elif resposta_usuario == "5":
                        usuario.estado = "finalizado"
                        enviar_resposta_de_texto(remetente_jid, "Certo. Saindo do sistema. Para reiniciar, envie 'oi' ou 'menu'.")
                        
                else:
                    if usuario.estado == "conversando_ia":
                        print(f"🤖 ENVIANDO PERGUNTA PARA IA: '{texto_recebido}'")
                        resposta = get_ai_response(texto_recebido)
                        enviar_resposta_de_texto(remetente_jid, resposta)
                    else:
                        enviar_menu_botoes(remetente_jid, f"Não entendi '{texto_recebido}'. Por favor, escolha uma opção:", OPCOES_MENU_PRINCIPAL)


            # --- FIM DA LÓGICA DE FLUXO ---

            db.commit()
            
            # Repetição para gerar novo exercício após o acerto
            if usuario.estado == ESTADO_MENU and resposta_usuario == "2":
                await handle_webhook(request, db) # Chama a função novamente para processar o clique simulado
                
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