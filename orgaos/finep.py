import os
import re
import requests
from urllib.parse import urlparse
from playwright.sync_api import Page
from orgaos.base_orgao import BaseOrgao

GRUPO_ID   = "222684"  # fixo no site da FINEP
API_URL    = "https://www.finep.gov.br/o/c/chamadapublicas"
PAGE_SIZE  = 250


class FINEP(BaseOrgao):
    nome = "FINEP"
    url  = "https://www.finep.gov.br/oportunidades"

    def coletar(self, page: Page) -> list:
        arquivos_salvos = []

        # ── 1. Busca todas as chamadas abertas via API ────
        abertas = []
        for pg in range(1, 10):
            resp = requests.get(
                f"{API_URL}?sort=dataDePublicacao:desc&search=&page={pg}&pageSize={PAGE_SIZE}",
                headers={"Accept": "application/json"},
                timeout=30
            )
            if resp.status_code != 200:
                break
            dados = resp.json()
            itens = dados.get("items", [])
            for item in itens:
                if item.get("situacao", {}).get("key") == "aberta":
                    abertas.append(item)
            if pg >= dados.get("lastPage", 1):
                break

        self.logger.info(f"{len(abertas)} chamada(s) aberta(s) encontrada(s).")

        if not abertas:
            return arquivos_salvos

        # ── 2. Acessar página de detalhe de cada chamada ─
        for item in abertas:
            titulo   = item.get("titulo", "sem_titulo")
            item_id  = item.get("id")
            try:
                url_detalhe = f"https://www.finep.gov.br/e/chamada-publica/{GRUPO_ID}/{item_id}"
                self.logger.info(f"Acessando: {titulo}")

                page.goto(url_detalhe, wait_until="networkidle")
                page.wait_for_timeout(2000)

                # ── 3. Pega links PDF da Lista de Documentos ─
                links_pdf = page.evaluate("""
                    () => {
                        const links = [];
                        document.querySelectorAll('a[href*="download=true"]').forEach(a => {
                            // Nome do documento — sobe para encontrar o texto da linha
                            let container = a.parentElement;
                            let nome = '';
                            for (let i = 0; i < 5; i++) {
                                if (!container) break;
                                const tds = container.querySelectorAll('td');
                                if (tds.length >= 2) {
                                    nome = tds[1].innerText.trim();
                                    break;
                                }
                                container = container.parentElement;
                            }
                            links.push({
                                href: a.href,
                                nome: nome || 'documento'
                            });
                        });
                        return links;
                    }
                """)

                if not links_pdf:
                    self.logger.warning(f"Nenhum documento encontrado em: {url_detalhe}")
                    continue

                self.logger.info(f"{len(links_pdf)} documento(s) encontrado(s).")

                # ── 4. Criar subpasta para cada chamada ───
                nome_pasta   = self._sanitizar_nome(titulo)
                pasta_edital = os.path.join(self.pasta_orgao, nome_pasta)
                os.makedirs(pasta_edital, exist_ok=True)

                # ── 5. Baixar cada documento ──────────────
                for idx, doc in enumerate(links_pdf, start=1):
                    try:
                        href_pdf  = doc["href"]
                        nome_doc  = self._sanitizar_nome(doc["nome"]) or f"documento_{idx:02d}"
                        extensao  = self._extrair_extensao(href_pdf)
                        nome_arq  = f"{idx:02d} - {nome_doc}{extensao}"
                        caminho   = os.path.join(pasta_edital, nome_arq)

                        self.logger.info(f"Baixando: {nome_arq}")

                        nova_aba = page.context.new_page()
                        sucesso  = False
                        try:
                            with nova_aba.expect_download() as dl_info:
                                try:
                                    nova_aba.goto(href_pdf, wait_until="commit")
                                except Exception:
                                    pass
                            dl_info.value.save_as(caminho)
                            sucesso = True
                        except Exception:
                            try:
                                nova_aba.goto(href_pdf, wait_until="domcontentloaded")
                                nova_aba.wait_for_timeout(2000)
                                self.salvar_pdf_da_pagina(nova_aba, nome_arq)
                                sucesso = True
                            except Exception as e2:
                                self.logger.error(f"Fallback falhou: {e2}")
                        finally:
                            nova_aba.close()

                        if sucesso:
                            arquivos_salvos.append({
                                "grupo":       titulo,
                                "caminho":     pasta_edital,
                                "nome_edital": nome_arq
                            })
                            self.logger.info(f"Download concluído: {nome_arq}")

                    except Exception as e:
                        self.logger.error(f"Erro ao baixar doc {idx}: {e}")
                        continue

            except Exception as e:
                self.logger.error(f"Erro ao processar '{titulo}': {e}")
                continue

        return arquivos_salvos

    @staticmethod
    def _extrair_extensao(url: str) -> str:
        caminho = urlparse(url).path
        _, ext  = os.path.splitext(caminho)
        return ext.lower() if ext else ".pdf"

    @staticmethod
    def _sanitizar_nome(nome: str) -> str:
        for c in r'\/:*?"<>|':
            nome = nome.replace(c, "_")
        nome = re.sub(r"\s+", " ", nome)
        return nome.strip()[:100]