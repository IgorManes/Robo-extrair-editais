import os
from abc import ABC, abstractmethod
from datetime import date
from playwright.sync_api import sync_playwright, Page

from utils.logger import get_logger


class BaseOrgao(ABC):
    nome: str = ""
    url:  str = ""

    def __init__(self, pasta_orgao: str):
        self.pasta_orgao = pasta_orgao
        self.logger      = get_logger(self.nome)

    @abstractmethod
    def coletar(self, page: Page) -> list:
        pass

    def executar(self) -> list[dict]:
        base = {
            "ORGAO":         self.nome,
            "LINK":          self.url,
            "DATA_EXECUCAO": date.today().strftime("%Y-%m-%d"),
        }

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
                )
                context = browser.new_context(
                    ignore_https_errors=True,
                    accept_downloads=True,
                )
                page = context.new_page()
                page.set_default_timeout(30_000)

                arquivos = self.coletar(page)
                browser.close()

            if not arquivos:
                self.logger.info("Nenhum edital encontrado.")
                return [{
                    **base,
                    "CAMINHO":         os.path.abspath(self.pasta_orgao),
                    "NOME_EDITAL":     "Nenhum edital encontrado",
                    "STATUS_EXECUCAO": "Sucesso",
                    "OBSERVACOES":     "-",
                }]

            registros = []
            for arq in arquivos:
                if isinstance(arq, dict):
                    if arq.get("status") == "Falha":
                        registros.append({
                            **base,
                            "CAMINHO":         os.path.abspath(arq.get("caminho", self.pasta_orgao)),
                            "GRUPO":           arq.get("grupo", arq.get("titulo", "-")),
                            "NOME_EDITAL":     arq.get("titulo", arq.get("nome_edital", "-")),
                            "STATUS_EXECUCAO": "Falha",
                            "OBSERVACOES":     arq.get("observacao", "-"),
                        })
                    else:
                        registros.append({
                            **base,
                            "CAMINHO":         os.path.abspath(arq.get("caminho", self.pasta_orgao)),
                            "GRUPO":           arq.get("grupo", arq.get("nome_edital", "-")),
                            "NOME_EDITAL":     arq.get("nome_edital", "-"),
                            "STATUS_EXECUCAO": "Sucesso",
                            "OBSERVACOES":     "-",
                        })
                else:
                    registros.append({
                        **base,
                        "CAMINHO":         os.path.abspath(self.pasta_orgao),
                        "GRUPO":           arq,
                        "NOME_EDITAL":     arq,
                        "STATUS_EXECUCAO": "Sucesso",
                        "OBSERVACOES":     "-",
                    })

            self.logger.info(f"Coleta concluída: {len(registros)} registro(s).")
            return registros

        except Exception as e:
            self.logger.error(f"Erro na coleta: {e}")
            return [{
                **base,
                "CAMINHO":         os.path.abspath(self.pasta_orgao),
                "NOME_EDITAL":     "-",
                "STATUS_EXECUCAO": "Falha",
                "OBSERVACOES":     str(e),
            }]

    def salvar_download(self, page: Page, acao: callable, nome_arquivo: str) -> str:
        caminho = os.path.join(self.pasta_orgao, nome_arquivo)
        with page.expect_download() as dl_info:
            acao()
        dl_info.value.save_as(caminho)
        self.logger.info(f"Arquivo salvo: {caminho}")
        return nome_arquivo

    def salvar_pdf_da_pagina(self, page: Page, nome_arquivo: str) -> str:
        caminho = os.path.join(self.pasta_orgao, nome_arquivo)
        page.pdf(path=caminho, format="A4")
        self.logger.info(f"PDF da página salvo: {caminho}")
        return nome_arquivo