from utils.file_manager import criar_estrutura_dia, criar_pasta_orgao
from orgaos.sesi_senai import SESI_SENAI

pasta_data, _ = criar_estrutura_dia()
pasta_orgao   = criar_pasta_orgao(pasta_data, "SESI_SENAI")

sesi     = SESI_SENAI(pasta_orgao)
registros = sesi.executar()

print("\n=== RESULTADO ===")
for reg in registros: 
    for chave, valor in reg.items():
        print(f"{chave}: {valor}")
    print("---")
