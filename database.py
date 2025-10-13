from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import logging
import os

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

DATABASE_URL = "sqlite:///./bot_data.db"
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Usuario(Base):
    __tablename__ = "usuarios"

    wa_jid = Column(String, primary_key=True, index=True) 
    nome = Column(String, default="Desconhecido")
    nivel_ingles = Column(String, default="Não definido")
    estado = Column(String, default="inicio") 
    pontuacao = Column(Integer, default=0)
    pergunta_atual_id = Column(Integer, default=0)
    ultima_interacao = Column(DateTime, default=datetime.now)

class Licao(Base):
    __tablename__ = "licoes"

    id = Column(Integer, primary_key=True, index=True)
    tema = Column(String, index=True, default="introducao")
    topico = Column(String)
    texto_pergunta = Column(String)
    opcao_a = Column(String)
    opcao_b = Column(String)
    opcao_c = Column(String)
    opcao_d = Column(String)
    resposta_correta = Column(String)
    

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        log.info("✅ Banco de dados e tabelas 'usuarios' e 'licoes' criadas.")
    except Exception as e:
        log.error(f"🚨 Erro ao inicializar o banco de dados: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()