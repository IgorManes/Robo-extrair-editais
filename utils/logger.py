import logging
import os
from datetime import date

def get_logger(nome: str) -> logging.Logger:
    logger = logging.getLogger(nome)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s — %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Saída no terminal
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Saída em arquivo de log do dia
    os.makedirs("logs", exist_ok=True)
    fh = logging.FileHandler(f"logs/{date.today()}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger