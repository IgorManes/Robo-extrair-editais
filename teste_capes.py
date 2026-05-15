from utils.file_manager import criar_estrutura_dia, criar_pasta_orgao
from orgaos.capes import CAPES

pasta_data, _ = criar_estrutura_dia()
pasta_orgao   = criar_pasta_orgao(pasta_data, "CAPES")

capes     = CAPES(pasta_orgao)
registros = capes.executar()

print("\n=== RESULTADO ===")
for reg in registros:
    for chave, valor in reg.items():
        print(f"{chave}: {valor}")
    print("---")