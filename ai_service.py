import os
from dotenv import load_dotenv
import logging
from google import genai
from google.genai.errors import APIError

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