from database import SessionLocal, Licao, init_db
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

licoes_iniciais = [
    Licao(
        id=1,
        tema="vocabulario_saudacoes",
        topico="Lição 1: Saudações",
        texto_pergunta="Qual é a tradução correta para a frase: 'How are you?'",
        opcao_a="A. Quem é você?",
        opcao_b="B. Onde você está?",
        opcao_c="C. Como você está?",
        opcao_d="D. Qual é o seu nome?",
        resposta_correta="c"
    ),
    Licao(
        id=2,
        tema="gramatica_ser_estar",
        topico="Lição 2: Verb To Be (Básico)",
        texto_pergunta="Complete a frase: 'She ____ a student.'",
        opcao_a="A. are",
        opcao_b="B. is",
        opcao_c="C. am",
        opcao_d="D. be",
        resposta_correta="b"
    ),
    Licao(
        id=3,
        tema="vocabulario_comum",
        topico="Lição 3: Cores",
        texto_pergunta="Qual palavra significa 'vermelho' em inglês?",
        opcao_a="A. Yellow",
        opcao_b="B. Blue",
        opcao_c="C. Green",
        opcao_d="D. Red",
        resposta_correta="d"
    ),
]

def adicionar_licoes():
    db = SessionLocal()
    try:
        if db.query(Licao).filter(Licao.id == 1).first():
            log.info("📝 Lições iniciais já existem. Nenhuma alteração feita.")
            return

        for licao in licoes_iniciais:
            db.add(licao)
        
        db.commit()
        log.info("✅ 3 Lições de Inglês adicionadas com sucesso.")

    except Exception as e:
        db.rollback()
        log.error(f"🚨 Erro ao adicionar lições: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    adicionar_licoes()