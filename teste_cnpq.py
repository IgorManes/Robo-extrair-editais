from utils.file_manager import criar_estrutura_dia, criar_pasta_orgao
from orgaos.cnpq import CNPQ

pasta_data, _ = criar_estrutura_dia()
pasta_orgao   = criar_pasta_orgao(pasta_data, "CNPQ")

cnpq      = CNPQ(pasta_orgao)
registros = cnpq.executar()

print("\n=== RESULTADO ===")
for reg in registros:
    for chave, valor in reg.items():
        print(f"{chave}: {valor}")
    print("---")