import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_REMETENTE     = os.getenv("EMAIL_REMETENTE")
EMAIL_SENHA         = os.getenv("EMAIL_SENHA")
EMAIL_DESTINATARIOS = os.getenv("EMAIL_DESTINATARIOS", "").split(",")
EMAIL_ASSUNTO       = os.getenv("EMAIL_ASSUNTO", "Relatório Diário de Editais")
EMAIL_CORPO         = os.getenv("EMAIL_CORPO", "Segue o relatório em anexo.")

PASTA_EDITAIS = os.getenv("PASTA_EDITAIS", "Editais")

ORGAOS = {
    "BNDES":      "https://www.bndes.gov.br/wps/vanityurl/chamadadeinovacao",
    "CAPES":      "https://www.gov.br/capes/pt-br/assuntos/editais-e-resultados-capes",
    "CNPQ":       "http://memoria2.cnpq.br/web/guest/chamadas-publicas",
    "FAPEG":      "https://goias.gov.br/fapeg/categoria/editais/",
    "FINEP":      "http://www.finep.gov.br/chamadas-publicas?situacao=aberta",
    "SESI_SENAI": "https://www.portaldaindustria.com.br/canais/plataforma-inovacao-para-industria/",
}