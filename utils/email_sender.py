import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders
import os

from config import (
    EMAIL_REMETENTE, EMAIL_SENHA,
    EMAIL_DESTINATARIOS, EMAIL_ASSUNTO, EMAIL_CORPO
)
from utils.logger import get_logger

logger = get_logger("email_sender")


def enviar_relatorio(caminho_relatorio: str) -> None:
    """
    Envia o relatório Excel como anexo para os destinatários
    definidos no .env.
    """
    msg            = MIMEMultipart()
    msg["From"]    = EMAIL_REMETENTE
    msg["To"]      = ", ".join(EMAIL_DESTINATARIOS)
    msg["Subject"] = EMAIL_ASSUNTO
    msg.attach(MIMEText(EMAIL_CORPO, "plain", "utf-8"))

    # Anexar o arquivo Excel
    with open(caminho_relatorio, "rb") as f:
        parte = MIMEBase("application", "octet-stream")
        parte.set_payload(f.read())
    encoders.encode_base64(parte)
    nome_arquivo = os.path.basename(caminho_relatorio)
    parte.add_header("Content-Disposition", f'attachment; filename="{nome_arquivo}"')
    msg.attach(parte)

    # Envio via Gmail SSL
    try:
        with smtplib.SMTP("cloud29.mailgrid.net.br", 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(EMAIL_REMETENTE, EMAIL_SENHA)
            smtp.sendmail(EMAIL_REMETENTE, EMAIL_DESTINATARIOS, msg.as_string())
        logger.info("E-mail enviado com sucesso.")
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail: {e}")
        raise