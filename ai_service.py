import os
from dotenv import load_dotenv
import logging
from google import genai
from google.genai.errors import APIError
# ... (imports de send_message e utils, se necessário)

load_dotenv()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
logging.getLogger('google.genai').setLevel(logging.WARNING)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY) 
    else:
        log.warning("Chave GEMINI_API_KEY não encontrada. Serviço de IA inativo.")
        client = None
except Exception as e:
    log.error(f"Erro ao iniciar o cliente Gemini: {e}")
    client = None


def get_ai_response(prompt: str) -> str:
# ... (função sem alterações) ...
    if not client:
        return "🤖 Serviço de IA indisponível. Verifique a GEMINI_API_KEY no .env."

    system_instruction = (
        "Você é um assistente de conversação amigável chamado 'English Bot'. "
        "Seu objetivo é responder perguntas sobre a língua inglesa e auxiliar o usuário no aprendizado. "
        "Responda de forma sucinta e didática. Não use asteriscos duplos (**) para negrito; use *asterisco único* para negrito e itálico, e aplique a formatação de forma MUITO moderada para manter o texto limpo."
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={'system_instruction': system_instruction}
        )

        return response.text.strip()

    except APIError as e:
        log.error(f"❌ Erro da API Gemini: {e}")
        return "🤖 Houve um erro na comunicação com a IA. Tente novamente mais tarde."
    except Exception as e:
        log.error(f"🚨 Erro inesperado ao obter resposta da IA: {e}")
        return "🤖 Não foi possível processar sua solicitação."
    
def get_dynamic_exercise(user_level: str) -> str:
    
    if not client:
        return '{"error": "Serviço de IA indisponível."}'
    
    prompt_instruction = (
        f"Crie um exercício de inglês adequado para um aluno de nível '{user_level}'. "
        "O exercício deve ser sobre gramática ou vocabulário. "
        "O tipo de pergunta deve ser de múltipla escolha (choice) ou resposta aberta (open). "
        "Retorne a pergunta e a resposta CORRETA no formato JSON estrito."
    )
    
    user_prompt = (
        "Gere APENAS o JSON. O ID deve ser o ID do exercício (EX1, EX2, etc.). "
        "Para 'choice', o valor de 'correta' DEVE ser a PALAVRA OU FASE EXATA da opção correta (ex: 'is' ou 'blue' ou 'I am'). "
        "Para 'choice', inclua 4 'opcoes' como strings dentro da lista 'opcoes'."
    )
    
    response_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "tipo": {"type": "string", "enum": ["choice", "open"]},
            "pergunta": {"type": "string"},
            "opcoes": {"type": "array", "items": {"type": "string"}},
            "correta": {"type": "string"},
            "explicacao": {"type": "string"}
        },
        "required": ["id", "tipo", "pergunta", "correta"]
    }
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt_instruction, user_prompt],
            config={
                'response_mime_type': 'application/json',
                'response_schema': response_schema
            }
        )
        
        return response.text.strip()
    
    except APIError as e:
        log.error(f"❌ Erro da API Gemini ao gerar exercício: {e}")
        return '{"error": "Falha na geração do exercício."}'
    except Exception as e:
        log.error(f"🚨 Erro inesperado ao gerar exercício: {e}")
        return '{"error": "Erro de processamento interno."}'