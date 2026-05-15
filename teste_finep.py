from utils.file_manager import criar_estrutura_dia, criar_pasta_orgao
from orgaos.finep import FINEP

pasta_data, _ = criar_estrutura_dia()
pasta_orgao   = criar_pasta_orgao(pasta_data, "FINEP")

finep     = FINEP(pasta_orgao)
registros = finep.executar()

print("\n=== RESULTADO ===")
for reg in registros:
    for chave, valor in reg.items():
        print(f"{chave}: {valor}")
    print("---")