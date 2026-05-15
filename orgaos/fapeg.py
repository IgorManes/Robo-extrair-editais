import os
import re
from datetime import date, timedelta
from playwright.sync_api import Page
from orgaos.base_orgao import BaseOrgao


class FAPEG(BaseOrgao):
    nome = "FAPEG"
    url  = "https://goias.gov.br/fapeg/categoria/editais/"

    MESES = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
        "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
        "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12
    }

    def coletar(self, page: Page) -> list[str]:
        arquivos_salvos = []
        limite = date.today() - timedelta(days=30)

        # ── 1. Percorrer todas as páginas ─────────────────
        links_validos = []
        pagina_atual  = 1
        continuar     = True

        while continuar:
            self.logger.info(f"Verificando página {pagina_atual}...")
            page.goto(self.url if pagina_atual == 1
                      else f"{self.url}page/{pagina_atual}/")
            page.wait_for_load_state("networkidle")

            artigos = page.locator("article").all()
            if not artigos:
                break

            parou_nesta_pagina = False
            for artigo in artigos:
                try:
                    texto = artigo.inner_text()

                    data_publicacao  = self._extrair_data_rotulo(texto, "publicado em")
                    data_atualizacao = self._extrair_data_rotulo(texto, "última atualização")

                    datas = [d for d in [data_publicacao, data_atualizacao] if d]
                    if not datas:
                        self.logger.warning("Nenhuma data encontrada — ignorando.")
                        continue

                    data_referencia = max(datas)

                    if data_referencia < limite:
                        self.logger.info(
                            f"Edital de {data_referencia} fora do limite — "
                            f"parando paginação."
                        )
                        if data_publicacao and data_publicacao < limite:
                            parou_nesta_pagina = True
                        continue

                    link   = artigo.locator("a").first
                    href   = link.get_attribute("href") or ""
                    titulo = link.inner_text().strip()

                    if href and (titulo, href) not in links_validos:
                        links_validos.append((titulo, href))
                        self.logger.info(
                            f"Edital válido: {titulo} (ref: {data_referencia})"
                        )

                except Exception as e:
                    self.logger.error(f"Erro ao processar artigo: {e}")
                    continue

            proximo = page.locator("a:has-text('Próximo'), a.next")
            if parou_nesta_pagina or not proximo.count():
                continuar = False
            else:
                pagina_atual += 1

        self.logger.info(f"{len(links_validos)} edital(is) válido(s) encontrado(s).")

        # ── 2. Acessar cada edital e baixar o PDF ─────────
        for titulo, href in links_validos:
            try:
                self.logger.info(f"Acessando: {titulo}")
                page.goto(href)
                page.wait_for_load_state("networkidle")

                # Coleta todos os links PDF em ordem — mais recente primeiro
                todos_links = page.locator("a[href]").all()
                links_pdf   = []

                for link in todos_links:
                    try:
                        texto_link = link.inner_text().strip()
                        href_link  = link.get_attribute("href") or ""
                        if ".pdf" in href_link.lower() and texto_link:
                            links_pdf.append((texto_link, link))
                    except Exception:
                        continue

                if not links_pdf:
                    self.logger.warning(f"Nenhum link PDF encontrado em: {href}")
                    continue

                # Verifica se o arquivo mais recente é um resultado
                texto_mais_recente  = links_pdf[0][0].lower()
                gatilho_e_resultado = bool(re.search(
                    r"resultado|homologa|classifica|selecion|deferido|indeferido",
                    texto_mais_recente
                ))

                if gatilho_e_resultado:
                    self.logger.info(
                        f"Arquivo mais recente é resultado "
                        f"('{links_pdf[0][0]}') — só aceita edital/retificação com data."
                    )

                # Procura o edital/retificação mais recente válido
                link_selecionado = None
                nome_selecionado = ""

                for texto_link, link in links_pdf:
                    texto_lower    = texto_link.lower()
                    is_edital      = bool(re.match(r"^edital", texto_lower))
                    is_retificacao = bool(re.match(
                        r"^\d+[ªa°º]?\s*retifica|^retifica", texto_lower
                    ))

                    if not is_edital and not is_retificacao:
                        continue

                    data_link = self._extrair_data(texto_link)

                    if data_link:
                        if data_link >= limite:
                            link_selecionado = link
                            nome_selecionado = texto_link
                            break
                        else:
                            self.logger.info(
                                f"Edital/retificação com data {data_link} "
                                f"fora do limite — ignorando."
                            )
                            break
                    else:
                        if gatilho_e_resultado:
                            self.logger.info(
                                f"'{texto_link}' sem data e gatilho é resultado "
                                f"— ignorando."
                            )
                            continue
                        else:
                            link_selecionado = link
                            nome_selecionado = texto_link
                            break

                if not link_selecionado:
                    self.logger.info(
                        "Nenhum edital/retificação válido nos últimos 30 dias "
                        "— ignorando."
                    )
                    continue

                self.logger.info(f"Link selecionado: '{nome_selecionado}'")

                href_pdf = link_selecionado.get_attribute("href") or ""
                if not href_pdf:
                    self.logger.warning("href do PDF não encontrado.")
                    continue

                nome_arquivo = f"{self._sanitizar_nome(titulo)}.pdf"

                with page.expect_download() as dl_info:
                    try:
                        page.goto(href_pdf, wait_until="commit")
                    except Exception:
                        pass
                download = dl_info.value
                download.save_as(os.path.join(self.pasta_orgao, nome_arquivo))
                arquivos_salvos.append(nome_arquivo)
                self.logger.info(f"Download concluído: {nome_arquivo}")

            except Exception as e:
                self.logger.error(f"Erro ao processar '{titulo}': {e}")
                continue

        return arquivos_salvos

    def _extrair_data_rotulo(self, texto: str, rotulo: str):
        """Extrai a data que vem logo após um rótulo específico no texto."""
        texto_lower = texto.lower()
        pos = texto_lower.find(rotulo)
        if pos == -1:
            return None
        trecho = texto_lower[pos:pos + 60]
        return self._extrair_data(trecho)

    def _extrair_data(self, texto: str):
        """Extrai data no formato 'dd de mês de yyyy' ou 'dd/mm/yyyy'."""
        m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto.lower())
        if m and m.group(2) in self.MESES:
            return date(int(m.group(3)), self.MESES[m.group(2)], int(m.group(1)))
        m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
        if m:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        return None

    @staticmethod
    def _sanitizar_nome(nome: str) -> str:
        for c in r'\/:*?"<>|':
            nome = nome.replace(c, "_")
        return nome.strip()[:100]