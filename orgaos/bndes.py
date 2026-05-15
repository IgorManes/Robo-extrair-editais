from playwright.sync_api import Page, BrowserContext
from orgaos.base_orgao import BaseOrgao


class BNDES(BaseOrgao):
    nome = "BNDES"
    url  = "https://www.bndes.gov.br/wps/vanityurl/chamadadeinovacao"

    def _aceitar_cookies(self, page: Page) -> None:
        """Remove o banner de cookies sem tocar em outros elementos."""
        try:
            page.evaluate("""
                () => {
                    document.cookie = 'cookieConsent=true; path=/';
                    document.cookie = 'cookie_consent=accepted; path=/';
                    document.cookie = 'CookieConsent=true; path=/';
                    document.querySelectorAll('*').forEach(el => {
                        if (el.innerText && el.innerText.includes('ACCEPT ALL')) {
                            const banner = el.closest('[class*="cookie"], [class*="consent"], [class*="privacy"], [id*="cookie"]');
                            if (banner) banner.remove();
                        }
                    });
                }
            """)
            page.wait_for_timeout(300)
        except Exception:
            pass

    def _abrir_nova_aba(self, page: Page, context: BrowserContext,
                        locator_str: str) -> Page:
        """Clica em um link que abre nova aba e retorna a nova Page."""
        with context.expect_page() as nova_pagina_info:
            page.locator(locator_str).first.click()
        nova_pagina = nova_pagina_info.value
        nova_pagina.set_default_timeout(60_000)
        nova_pagina.set_viewport_size({"width": 1280, "height": 8000})
        nova_pagina.wait_for_load_state("domcontentloaded")
        nova_pagina.wait_for_timeout(6000)
        return nova_pagina

    def _carregar_todos_resultados(self, page: Page) -> None:
        """Aguarda o carregamento completo dos cards com viewport alto."""
        page.wait_for_timeout(3000)

    def coletar(self, page: Page) -> list[str]:
        arquivos_salvos = []

        page.set_default_timeout(60_000)
        
        context = page.context

        # ── 1. Acessar página principal ───────────────────
        page.goto(self.url)
        page.wait_for_load_state("networkidle")
        self._aceitar_cookies(page)

        # ── 2. Coletar hrefs das chamadas em andamento ────
        links_chamadas = page.locator("a", has_text="Acesse aqui o link").all()

        if not links_chamadas:
            self.logger.warning("Nenhuma chamada em andamento encontrada.")
            return arquivos_salvos

        hrefs = [link.get_attribute("href") for link in links_chamadas]
        self.logger.info(f"{len(hrefs)} chamada(s) em andamento encontrada(s).")

        # ── 3. Iterar sobre cada chamada ──────────────────
        for idx, href in enumerate(hrefs, start=1):
            pagina_chamada = None
            pagina_recursos = None
            try:
                self.logger.info(f"Processando chamada {idx}/{len(hrefs)}: {href}")

                pagina_chamada = context.new_page()
                pagina_chamada.set_default_timeout(60_000)
                pagina_chamada.goto(href, wait_until="domcontentloaded")
                pagina_chamada.wait_for_timeout(3000)
                self._aceitar_cookies(pagina_chamada)

                # ── 4. Expandir acordeão ──────────────────
                acordeao = pagina_chamada.locator(
                    "text=Edital e Anexos da Chamada Pública"
                ).first
                acordeao.click()
                pagina_chamada.wait_for_timeout(1000)

                # ── 5. Clicar no link — abre nova aba ─────
                pagina_recursos = self._abrir_nova_aba(
                    pagina_chamada,
                    context,
                    "a:has-text('Clique aqui para acessar o Edital e Anexos'), "
                    "a:has-text('aqui')"
                )
                self._aceitar_cookies(pagina_recursos)
                self.logger.info(f"Chamada {idx} — recursos: {pagina_recursos.url}")

                # ── 6. Preenche campo de busca ────────────
                pagina_recursos.wait_for_selector(
                    "input[placeholder='Procurar...']",
                    state="visible",
                    timeout=45000
                )
                self._aceitar_cookies(pagina_recursos)

                campo_busca = pagina_recursos.locator("input[placeholder='Procurar...']")
                campo_busca.click()
                pagina_recursos.wait_for_timeout(300)
                campo_busca.type("cpsi", delay=100)
                pagina_recursos.wait_for_timeout(2000)

                self._carregar_todos_resultados(pagina_recursos)

                # ── 7. Localizar edital correto ───────────
                item_edital = None
                for item in pagina_recursos.locator("h3").all():
                    try:
                        texto = (item.inner_text() or "").strip()
                        texto_lower = texto.lower()
                        if ("edital" in texto_lower
                                and "anexo" not in texto_lower
                                and "zip" not in texto_lower
                                and "arquivos" not in texto_lower):
                            item_edital = item
                            self.logger.info(f"Edital encontrado: {texto}")
                            break
                    except Exception:
                        continue

                if not item_edital:
                    self.logger.warning(f"Nenhum edital encontrado na chamada {idx}.")
                    continue

                nome_edital = item_edital.inner_text().strip()
                item_edital.click()
                pagina_recursos.wait_for_load_state("networkidle")

                # ── 8. Download ───────────────────────────
                nome_arquivo = f"{self._sanitizar_nome(nome_edital)}.pdf"
                arquivo = self.salvar_download(
                    pagina_recursos,
                    lambda: pagina_recursos.locator(
                        "a:has-text('Download'), button:has-text('Download')"
                    ).first.click(),
                    nome_arquivo
                )
                arquivos_salvos.append(arquivo)
                self.logger.info(f"Download concluído: {arquivo}")

            except Exception as e:
                self.logger.error(f"Erro ao processar chamada {idx}: {e}")

            finally:
                for p in [pagina_recursos, pagina_chamada]:
                    if p:
                        try:
                            p.close()
                        except Exception:
                            pass

        return arquivos_salvos

    @staticmethod
    def _sanitizar_nome(nome: str) -> str:
        for c in r'\/:*?"<>|':
            nome = nome.replace(c, "_")
        return nome.strip()[:100]