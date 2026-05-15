import os
from datetime import date
from config import PASTA_EDITAIS

def criar_estrutura_dia() -> tuple[str, str]:
    """
    Cria a pasta Editais/<data_de_hoje>/ e retorna
    (caminho_da_pasta, data_em_string).
    """
    data_str   = date.today().strftime("%Y-%m-%d")
    pasta_data = os.path.join(PASTA_EDITAIS, data_str)
    os.makedirs(pasta_data, exist_ok=True)
    return pasta_data, data_str

def criar_pasta_orgao(pasta_data: str, nome_orgao: str) -> str:
    """
    Cria a pasta Editais/<data>/<orgao>/ e retorna o caminho.
    """
    pasta = os.path.join(pasta_data, nome_orgao)
    os.makedirs(pasta, exist_ok=True)
    return pasta