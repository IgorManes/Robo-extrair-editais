import os
from playwright.sync_api import Page
from orgaos.base_orgao import BaseOrgao


class CNPQ(BaseOrgao):
    nome = "CNPQ"
    url  = "http://memoria2.cnpq.br/web/guest/chamadas-publicas"

    def coletar(self, page: Page) -> list[str]:
        arquivos_salvos = []

        # ── 1. Acessar página de chamadas públicas ────────
        page.goto(self.url)
        page.wait_for_load_state("networkidle")
        self.logger.info("Página de chamadas públicas carregada.")

        # ── 2. Coletar botões "Chamada" com class="btn" ───
        botoes = page.locator("a.btn:has-text('Chamada')").all()

        if not botoes:
            self.logger.warning("Nenhuma chamada pública encontrada.")
            return arquivos_salvos

        self.logger.info(f"{len(botoes)} chamada(s) encontrada(s).")

        # ── 3. Coletar hrefs e títulos antes de navegar ───
        hrefs   = []
        titulos = []
        for idx, botao in enumerate(botoes, start=1):
            href = botao.get_attribute("href") or ""
            hrefs.append(href)
            try:
                titulo = botao.locator(
                    "xpath=ancestor::div[position()<=5]//h1|"
                    "xpath=ancestor::div[position()<=5]//h2|"
                    "xpath=ancestor::div[position()<=5]//h3|"
                    "xpath=ancestor::div[position()<=5]//strong"
                ).first.inner_text().strip()
                if not titulo:
                    titulo = f"edital_cnpq_{idx}"
            except Exception:
                titulo = f"edital_cnpq_{idx}"
            titulos.append(titulo)

        # ── 4. Baixar cada edital pelo href ───────────────
        for idx, (href, titulo) in enumerate(zip(hrefs, titulos), start=1):
            try:
                self.logger.info(f"Baixando chamada {idx}: {titulo}")
                nome_arquivo = f"{self._sanitizar_nome(titulo)}.pdf"

                with page.expect_download() as dl_info:
                    try:
                        page.goto(href, wait_until="commit")
                    except Exception:
                        pass
                download = dl_info.value
                download.save_as(os.path.join(self.pasta_orgao, nome_arquivo))
                arquivos_salvos.append(nome_arquivo)
                self.logger.info(f"Download concluído: {nome_arquivo}")

            except Exception as e:
                self.logger.error(f"Erro ao processar chamada {idx}: {e}")
                continue

        return arquivos_salvos

    @staticmethod
    def _sanitizar_nome(nome: str) -> str:
        for c in r'\/:*?"<>|':
            nome = nome.replace(c, "_")
        return nome.strip()[:100]