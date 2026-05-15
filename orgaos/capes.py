import os
import re
from datetime import date
from playwright.sync_api import Page
from orgaos.base_orgao import BaseOrgao


class CAPES(BaseOrgao):
    nome = "CAPES"
    url  = "https://www.gov.br/capes/pt-br/assuntos/editais-e-resultados-capes"

    def coletar(self, page: Page) -> list[str]:
        arquivos_salvos = []

        # ── 1. Acessar página principal ───────────────────
        page.goto(self.url)
        page.wait_for_load_state("networkidle")
        self.logger.info("Página principal carregada.")

        # ── 2. Localizar links da seção "Editais Abertos" ─
        itens = page.evaluate("""
            () => {
                const heading = document.querySelector('h2.outstanding-title');
                if (!heading) return [];
                let container = heading.closest('div');
                while (container) {
                    const proximo = container.nextElementSibling;
                    if (proximo) {
                        const links = proximo.querySelectorAll('a[href]');
                        if (links.length > 0) {
                            return [...links].map(a => ({
                                texto: a.innerText.trim(),
                                href:  a.href
                            })).filter(item => item.texto && item.href);
                        }
                    }
                    const paiLinks = container.parentElement
                        ? container.parentElement.querySelectorAll('a[href]')
                        : [];
                    if (paiLinks.length > 0) {
                        return [...paiLinks].map(a => ({
                            texto: a.innerText.trim(),
                            href:  a.href
                        })).filter(item => item.texto && item.href);
                    }
                    container = container.parentElement;
                }
                return [];
            }
        """)

        itens = [i for i in itens if not i["texto"].lower().startswith("resultado")]

        if not itens:
            self.logger.warning("Nenhum edital aberto encontrado.")
            return arquivos_salvos

        self.logger.info(f"{len(itens)} edital(is) aberto(s) encontrado(s).")

        # ── 3. Acessar cada edital ────────────────────────
        for item in itens:
            titulo = item["texto"]
            href   = item["href"]
            try:
                self.logger.info(f"Acessando: {titulo}")
                page.goto(href)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(1000)

                melhor_link   = None
                melhor_data   = None
                melhor_nome   = ""
                pagina_busca  = href  # URL onde o edital foi encontrado

                # ── 4a. Tenta via tabela ──────────────────
                def _buscar_em_linhas(linhas):
                    nonlocal melhor_link, melhor_data, melhor_nome
                    data_anterior = None
                    for linha in linhas:
                        try:
                            texto_linha = linha.inner_text().strip()
                            data_so = self._extrair_data(texto_linha)
                            if data_so and len(texto_linha) < 30:
                                data_anterior = data_so
                                continue
                            if linha.locator("a").count() == 0:
                                continue
                            link_doc   = linha.locator("a").first
                            nome_doc   = link_doc.inner_text().strip()
                            nome_lower = nome_doc.lower()
                            if not re.search(r"edital\b.*n[ºo°]", nome_lower):
                                data_anterior = None
                                continue
                            if any(p in nome_lower for p in [
                                "resultado", "anexo", "relação", "lista",
                                "alteraç", "retificaç", "guia", "formulário", "termo"
                            ]):
                                data_anterior = None
                                continue
                            data_pub = self._extrair_data(texto_linha) or data_anterior
                            data_anterior = None
                            self.logger.info(f"Candidato: '{nome_doc}' | data: {data_pub}")
                            if melhor_data is None or (data_pub and data_pub > melhor_data):
                                melhor_data = data_pub
                                melhor_link = link_doc
                                melhor_nome = nome_doc
                        except Exception as ex:
                            self.logger.debug(f"Erro em linha: {ex}")
                            data_anterior = None
                            continue

                _buscar_em_linhas(page.locator("table tr, .listing tr, tbody tr").all())

                # ── 4b. Fallback: links diretos na página ─
                if not melhor_link:
                    for link in page.locator("a[href]").all():
                        try:
                            nome_doc   = link.inner_text().strip()
                            nome_lower = nome_doc.lower()
                            href_link  = link.get_attribute("href") or ""
                            if not re.search(r"edital\b.*n[ºo°]", nome_lower):
                                continue
                            if any(p in nome_lower for p in [
                                "resultado", "anexo", "relação", "lista",
                                "alteraç", "retificaç", "guia", "formulário", "termo"
                            ]):
                                continue
                            if ".pdf" not in href_link.lower():
                                continue
                            data_pub = self._extrair_data(nome_doc)
                            self.logger.info(f"Candidato (fallback): '{nome_doc}' | data: {data_pub}")
                            if melhor_link is None or (data_pub and (melhor_data is None or data_pub > melhor_data)):
                                melhor_data = data_pub
                                melhor_link = link
                                melhor_nome = nome_doc
                        except Exception:
                            continue

                # ── 4c. Fallback 2: subpáginas internas ──
                if not melhor_link:
                    try:
                        subpaginas = []
                        for link in page.locator("a[href]").all():
                            try:
                                texto_link = link.inner_text().strip().lower()
                                href_link  = link.get_attribute("href") or ""
                                if "gov.br/capes" not in href_link:
                                    continue
                                if ".pdf" in href_link.lower():
                                    continue
                                if href_link == href:
                                    continue
                                prioridade = 0
                                if "documentos-relacionados" in href_link.lower():
                                    prioridade = 3
                                elif "documento" in texto_link:
                                    prioridade = 2
                                elif "edital" in texto_link or "inscri" in texto_link:
                                    prioridade = 1
                                if prioridade > 0:
                                    subpaginas.append((prioridade, href_link))
                            except Exception:
                                continue

                        subpaginas.sort(key=lambda x: x[0], reverse=True)
                        for _, href_sub in subpaginas[:5]:
                            if melhor_link:
                                break
                            try:
                                self.logger.info(f"Tentando subpágina: {href_sub}")
                                page.goto(href_sub)
                                page.wait_for_load_state("networkidle")
                                page.wait_for_timeout(3000)
                                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                                page.wait_for_timeout(1000)
                                page.evaluate("window.scrollTo(0, 0)")
                                page.wait_for_timeout(500)
                                resultado_js = page.evaluate("""
                                    () => {
                                        const links = document.querySelectorAll('a[href*=".pdf"]');
                                        let melhor = null;
                                        let melhorAno = 0;
                                        let melhorNum = 0;
                                        for (const link of links) {
                                            const nome = link.innerText.trim();
                                            const nomeLower = nome.toLowerCase();
                                            if (!nomeLower.includes('edital')) continue;
                                            if (/resultado|anexo|rela[cç]|lista|altera[cç]|retifica[cç]|guia|formul|termo/.test(nomeLower)) continue;
                                            const m = nome.match(/n[ºo°]\\s*(\\d+)\\/(\\d{4})/i);
                                            if (m) {
                                                const num = parseInt(m[1]);
                                                const ano = parseInt(m[2]);
                                                if (ano > melhorAno || (ano === melhorAno && num > melhorNum)) {
                                                    melhorAno = ano;
                                                    melhorNum = num;
                                                    melhor = { href: link.href, nome: nome };
                                                }
                                            } else if (!melhor) {
                                                melhor = { href: link.href, nome: nome };
                                            }
                                        }
                                        return melhor;
                                    }
                                """)
                                if resultado_js and resultado_js.get("href"):
                                    self.logger.info(f"JS subpágina encontrou: '{resultado_js['nome']}'")
                                    melhor_nome  = resultado_js["nome"]
                                    melhor_link  = page.locator(f"a[href='{resultado_js['href']}']").first
                                    melhor_data  = self._extrair_data(resultado_js["nome"])
                                    pagina_busca = href_sub  # ← atualiza URL onde edital foi achado
                            except Exception:
                                continue
                    except Exception:
                        pass

                if not melhor_link:
                    self.logger.warning(f"Nenhum 'Edital nº' encontrado em: {href}")
                    continue

                self.logger.info(f"Selecionado: '{melhor_nome}' | data: {melhor_data}")

                # ── 5. Extrair número e ano do edital ─────
                m_edital   = re.search(r"n[ºo°]\s*(\d+)/(\d{4})", melhor_nome, re.IGNORECASE)
                num_edital = m_edital.group(1) if m_edital else None
                ano_edital = m_edital.group(2) if m_edital else None

                # ── 6. Criar subpasta para este edital ────
                nome_subpasta = self._sanitizar_nome(titulo)
                pasta_edital  = os.path.join(self.pasta_orgao, nome_subpasta)
                os.makedirs(pasta_edital, exist_ok=True)

                # ── 7. Download do edital principal ───────
                href_doc = melhor_link.get_attribute("href") or ""
                if not href_doc:
                    self.logger.warning("Link do documento não encontrado.")
                    continue

                nome_arquivo = f"{self._sanitizar_nome(titulo)}.pdf"
                caminho_edital = os.path.join(pasta_edital, nome_arquivo)
                self._baixar_pdf(page, href_doc, caminho_edital, nome_arquivo)
                arquivos_salvos.append({
                    "grupo":      titulo,
                    "caminho":    pasta_edital,
                    "nome_edital": nome_arquivo
                })

                # ── 8. Buscar alterações na pagina_busca ──
                if num_edital and ano_edital:
                    # Garante que está na página onde o edital foi encontrado
                    if page.url != pagina_busca:
                        page.goto(pagina_busca)
                        page.wait_for_load_state("networkidle")
                        page.wait_for_timeout(1000)

                    num_pad = num_edital.zfill(2)
                    alteracoes = page.evaluate(f"""
                        () => {{
                            const links = document.querySelectorAll('a[href*=".pdf"]');
                            const resultado = [];
                            for (const link of links) {{
                                const nome = link.innerText.trim();
                                const nomeLower = nome.toLowerCase();
                                if (!nomeLower.includes('altera')) continue;
                                if (!nomeLower.includes('edital')) continue;
                                if (nomeLower.includes('resultado')) continue;       
                                if (!nome.includes('{num_edital}/{ano_edital}') &&
                                    !nome.includes('{num_pad}/{ano_edital}')) continue;
                                resultado.push({{ href: link.href, nome: nome }});
                            }}
                            return resultado;
                        }}
                    """)

                    if alteracoes:
                        self.logger.info(
                            f"{len(alteracoes)} alteração(ões) encontrada(s) para "
                            f"edital nº {num_edital}/{ano_edital}."
                        )
                        for idx, alt in enumerate(alteracoes, start=1):
                            try:
                                nome_alt = (
                                    self._sanitizar_nome(alt["nome"])
                                    or f"alteracao_{idx:02d}"
                                )
                                nome_alt_arquivo = f"{nome_alt}.pdf"
                                caminho_alt = os.path.join(pasta_edital, nome_alt_arquivo)
                                self._baixar_pdf(page, alt["href"], caminho_alt, nome_alt_arquivo)
                                arquivos_salvos.append({
                                    "grupo":       titulo,
                                    "caminho":     pasta_edital,
                                    "nome_edital": nome_alt_arquivo
                                })
                            except Exception as e:
                                self.logger.error(f"Erro ao baixar alteração {idx}: {e}")
                                continue
                    else:
                        self.logger.info(
                            f"Nenhuma alteração para edital nº {num_edital}/{ano_edital}."
                        )

            except Exception as e:
                self.logger.error(f"Erro ao processar '{titulo}': {e}")
                continue

        return arquivos_salvos

    def _baixar_pdf(self, page: Page, href_doc: str, caminho: str, nome_log: str) -> None:
        """Baixa PDF usando expect_download, com fallback para salvar_pdf_da_pagina."""
        try:
            with page.expect_download() as dl_info:
                try:
                    page.goto(href_doc, wait_until="commit")
                except Exception:
                    pass
            dl_info.value.save_as(caminho)
            self.logger.info(f"Download concluído: {nome_log}")
        except Exception:
            # Fallback: PDF abriu no navegador
            try:
                page.goto(href_doc)
                page.wait_for_load_state("networkidle")
                page.pdf(path=caminho)
                self.logger.info(f"PDF da página salvo: {nome_log}")
            except Exception as e:
                self.logger.error(f"Falha ao baixar '{nome_log}': {e}")

    def _extrair_data(self, texto: str):
        """Extrai data no formato dd/mm/yyyy."""
        m = re.search(r"(\d{2})/(\d{2})/(\d{2,4})", texto)
        if m:
            ano = int(m.group(3))
            if ano < 100:
                ano += 2000
            return date(ano, int(m.group(2)), int(m.group(1)))
        return None

    @staticmethod
    def _sanitizar_nome(nome: str) -> str:
        for c in r'\/:*?"<>|':
            nome = nome.replace(c, "_")
        return nome.strip()[:100]