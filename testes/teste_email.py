from utils.email_sender import enviar_relatorio
import glob

# Pega o relatório mais recente
arquivos = glob.glob("Editais/**/*.xlsx", recursive=True)
if arquivos:
    relatorio = max(arquivos)
    print(f"Enviando: {relatorio}")
    enviar_relatorio(relatorio)
else:
    print("Nenhum relatório encontrado.")
