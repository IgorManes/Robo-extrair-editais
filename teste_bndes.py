# teste_bndes.py
from utils.file_manager import criar_estrutura_dia, criar_pasta_orgao
from orgaos.bndes import BNDES

pasta_data, _ = criar_estrutura_dia()
pasta_orgao   = criar_pasta_orgao(pasta_data, "BNDES")

bndes     = BNDES(pasta_orgao)
registros = bndes.executar()

print("\n=== RESULTADO ===")
for reg in registros:
    for chave, valor in reg.items():
        print(f"{chave}: {valor}")
    print("---")