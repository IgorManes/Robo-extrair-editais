from utils.file_manager import criar_estrutura_dia, criar_pasta_orgao
from utils.report_generator import gerar_relatorio
from collections import OrderedDict

from orgaos.bndes import BNDES
from orgaos.capes import CAPES
from orgaos.cnpq import CNPQ
from orgaos.fapeg import FAPEG
from orgaos.finep import FINEP
from orgaos.sesi_senai import SESI_SENAI

from utils.logger import get_logger

logger = get_logger("MAIN")


def consolidar_registros(registros: list[dict]) -> list[dict]:
    """Agrupa registros do mesmo edital em uma linha, juntando NOME_EDITAL com ###."""
    grupos = OrderedDict()
    for reg in registros:
        chave = (reg["ORGAO"], reg.get("GRUPO", reg["NOME_EDITAL"]))
        if chave not in grupos:
            grupos[chave] = reg.copy()
            grupos[chave]["_nomes"] = [reg["NOME_EDITAL"]]
        else:
            grupos[chave]["_nomes"].append(reg["NOME_EDITAL"])

    resultado = []
    for reg in grupos.values():
        reg["NOME_EDITAL"] = " ### ".join(reg.pop("_nomes"))
        reg.pop("GRUPO", None)
        resultado.append(reg)
    return resultado


def main():
    logger.info("Iniciando coleta de editais.")

    pasta_data, data_str = criar_estrutura_dia()
    logger.info(f"Pasta de execução: {pasta_data}")

    orgaos = [
        BNDES(criar_pasta_orgao(pasta_data, "BNDES")),
        CAPES(criar_pasta_orgao(pasta_data, "CAPES")),
        CNPQ(criar_pasta_orgao(pasta_data, "CNPQ")),
        FAPEG(criar_pasta_orgao(pasta_data, "FAPEG")),
        FINEP(criar_pasta_orgao(pasta_data, "FINEP")),
        SESI_SENAI(criar_pasta_orgao(pasta_data, "SESI_SENAI")),
    ]

    todos_registros = []

    for orgao in orgaos:
        logger.info(f"Executando: {orgao.nome}")
        try:
            registros = orgao.executar()
            todos_registros.extend(registros)
            logger.info(f"{orgao.nome} concluído: {len(registros)} registro(s).")
        except Exception as e:
            logger.error(f"Erro inesperado em {orgao.nome}: {e}")
            todos_registros.append({
                "ORGAO":           orgao.nome,
                "LINK":            orgao.url,
                "CAMINHO":         "",
                "NOME_EDITAL":     "-",
                "DATA_EXECUCAO":   data_str,
                "STATUS_EXECUCAO": "Falha",
                "OBSERVACOES":     str(e),
            })

    # Consolida múltiplos arquivos do mesmo edital em uma linha
    todos_registros = consolidar_registros(todos_registros)

    caminho_relatorio = gerar_relatorio(todos_registros, pasta_data)
    logger.info(f"Relatório gerado: {caminho_relatorio}")
    logger.info(f"Total de registros: {len(todos_registros)}")

    try:
        from utils.email_sender import enviar_relatorio
        enviar_relatorio(caminho_relatorio)
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail: {e}")

    logger.info("Coleta finalizada.")


if __name__ == "__main__":
    main()