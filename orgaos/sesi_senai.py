import os
import re
from playwright.sync_api import Page
from orgaos.base_orgao import BaseOrgao


class SESI_SENAI(BaseOrgao):
    nome = "SESI/SENAI"
    url  = "https://www.portaldaindustria.com.br/canais/plataforma-inovacao-para-industria/"

    def coletar(self, page: Page) -> list:
        arquivos_salvos = []

        # Site lento — aumenta timeout
        page.set_default_timeout(60_000)

        # ── 1. Acessar página principal ───────────────────
        page.goto(self.url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        self.logger.info("Página principal carregada.")

        # ── 2. Clicar na aba "Últimas chamadas" ───────────
        try:
            page.locator("text=Últimas chamadas").first.click()
            page.wait_for_timeout(2000)
            self.logger.info("Aba 'Últimas chamadas' selecionada.")
        except Exception as e:
            self.logger.error(f"Erro ao clicar na aba: {e}")
            return arquivos_salvos

        # ── 3. Coletar apenas links do slide "Últimas chamadas" ──
        links_chamadas = page.evaluate("""
            () => {
                const slides = document.querySelectorAll('div.swiper-wrapper .swiper-slide');
                for (const slide of slides) {
                    const label = slide.querySelector('p.acessibilidade');
                    if (!label || !label.innerText.includes('Últimas chamadas')) continue;

                    const links = [];
                    slide.querySelectorAll('a[href]').forEach(a => {
                        const texto = (a.innerText || '').trim().split('\\n')[0].trim();
                        const href  = a.href;
                        if (texto && href) links.push({ texto, href });
                    });
                    return links;
                }
                return [];
            }
        """)

        # Remove duplicatas
        hrefs_vistos = set()
        links_unicos = []
        for l in links_chamadas:
            if l["href"] not in hrefs_vistos:
                hrefs_vistos.add(l["href"])
                links_unicos.append(l)

        self.logger.info(f"{len(links_unicos)} link(s) encontrado(s) em 'Últimas chamadas'.")

        # ── 4. Acessar cada chamada ───────────────────────
        for item in links_unicos:
            titulo_chamada = item["texto"]
            href_chamada   = item["href"]
            try:
                self.logger.info(f"Acessando: {titulo_chamada}")
                page.goto(href_chamada, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                # ── 5. Clicar na aba CHAMADAS ABERTAS ────
                try:
                    btn = page.locator(
                        "button:has-text('CHAMADAS ABERTAS'), "
                        "a:has-text('CHAMADAS ABERTAS'), "
                        "text=CHAMADAS ABERTAS"
                    ).first
                    if btn.count() > 0:
                        btn.click()
                        page.wait_for_timeout(1500)
                        self.logger.info("Aba 'CHAMADAS ABERTAS' selecionada.")
                except Exception:
                    pass

                # ── 6. Coletar chamadas abertas ───────────
                chamadas = page.evaluate("""
                    () => {
                        const resultado = [];
                        const processados = new Set();

                        // Busca apenas dentro do container ativo de CHAMADAS ABERTAS
                        let scope = document.querySelector(
                            '.tab-pane.active, [data-tab="abertas"], .chamadas-abertas'
                        );
                        // Fallback: filtra apenas elementos visíveis da página
                        if (!scope) scope = document.body;

                        scope.querySelectorAll('a, button').forEach(btn => {
                            // Ignora elementos não visíveis
                            const rect = btn.getBoundingClientRect();
                            if (rect.width === 0 && rect.height === 0) return;

                            const texto = (btn.innerText || '').trim().toLowerCase();
                            if (!texto.includes('download do regulamento') &&
                                !texto.includes('acesse aqui')) return;

                            const href = btn.href || btn.getAttribute('href') || '';

                            // Sobe para encontrar título da chamada
                            let container = btn.parentElement;
                            let tituloEl  = null;
                            for (let i = 0; i < 8; i++) {
                                if (!container) break;
                                tituloEl = container.querySelector(
                                    'h2, h3, h4, strong, .title, .chamada-titulo'
                                );
                                if (tituloEl && (tituloEl.innerText || '').trim().length > 5) break;
                                container = container.parentElement;
                            }

                            const titulo = tituloEl
                                ? (tituloEl.innerText || '').trim()
                                : 'Chamada sem título';

                            const chave = titulo + href;
                            if (processados.has(chave)) return;
                            processados.add(chave);

                            resultado.push({
                                titulo: titulo,
                                href:   href,
                                tipo:   texto.includes('download') ? 'download' : 'externo'
                            });
                        });
                        return resultado;
                    }
                """)

                if not chamadas:
                    self.logger.warning(f"Nenhuma chamada aberta em: {href_chamada}")
                    continue

                self.logger.info(f"{len(chamadas)} chamada(s) aberta(s) encontrada(s).")

                # ── 7. Processar cada chamada ─────────────
                for chamada in chamadas:
                    titulo_edital = chamada["titulo"]
                    href_pdf      = chamada["href"]
                    tipo          = chamada["tipo"]

                    if tipo == "externo":
                        self.logger.warning(
                            f"'{titulo_edital}' redireciona para ambiente externo."
                        )
                        arquivos_salvos.append({
                            "grupo":      titulo_edital,
                            "caminho":    self.pasta_orgao,
                            "titulo":     titulo_edital,
                            "status":     "Falha",
                            "observacao": "Redireciona para ambiente externo"
                        })
                        continue

                    # Download do regulamento
                    try:
                        nome_arquivo = f"{self._sanitizar_nome(titulo_edital)}.pdf"
                        caminho      = os.path.join(self.pasta_orgao, nome_arquivo)

                        self.logger.info(f"Abrindo regulamento: {nome_arquivo}")

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
                            # Fallback: PDF abre no navegador
                            try:
                                nova_aba.goto(href_pdf, wait_until="domcontentloaded")
                                nova_aba.wait_for_timeout(2000)
                                self.salvar_pdf_da_pagina(nova_aba, nome_arquivo)
                                sucesso = True
                            except Exception as e2:
                                self.logger.error(f"Fallback falhou: {e2}")
                        finally:
                            nova_aba.close()

                        if sucesso:
                            arquivos_salvos.append({
                                "grupo":       titulo_edital,
                                "caminho":     self.pasta_orgao,
                                "nome_edital": nome_arquivo
                            })
                            self.logger.info(f"Download concluído: {nome_arquivo}")
                        else:
                            self.logger.error(f"Falha ao salvar: {nome_arquivo}")

                    except Exception as e:
                        self.logger.error(f"Erro ao baixar '{titulo_edital}': {e}")
                        continue

            except Exception as e:
                self.logger.error(f"Erro ao processar '{titulo_chamada}': {e}")
                continue

        return arquivos_salvos

    @staticmethod
    def _sanitizar_nome(nome: str) -> str:
        for c in r'\/:*?"<>|':
            nome = nome.replace(c, "_")
        nome = re.sub(r"\s+", " ", nome)
        return nome.strip()[:100]