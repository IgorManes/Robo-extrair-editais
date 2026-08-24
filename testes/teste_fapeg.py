from utils.file_manager import criar_estrutura_dia, criar_pasta_orgao
from orgaos.fapeg import FAPEG

pasta_data, _ = criar_estrutura_dia()
pasta_orgao   = criar_pasta_orgao(pasta_data, "FAPEG")

fapeg     = FAPEG(pasta_orgao)
registros = fapeg.executar()

print("\n=== RESULTADO ===")
for reg in registros:
    for chave, valor in reg.items():
        print(f"{chave}: {valor}")
    print("---")
