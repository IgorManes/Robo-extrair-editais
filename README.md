# Robô de Extração de Editais

Automação em Python para coleta diária de editais em portais de órgãos de fomento.

Desenvolvido durante meu estágio no IEL Goiás e publicado com autorização da empresa, sem credenciais de acesso.

## O problema

A equipe de inovação gastava cerca de 2 horas todos os dias abrindo manualmente os portais dos órgãos de fomento para verificar quais editais estavam abertos, se havia publicações novas, retificações ou anexos atualizados.

## A solução

O robô roda automaticamente às 7h, antes do expediente. Quando a equipe chega, os editais abertos já estão baixados e organizados, e o relatório do dia já está na caixa de entrada das coordenadoras responsáveis.

O que ele faz em cada execução:

- Acessa os portais, cada um com seu próprio fluxo de navegação e regras de download
- Baixa os editais abertos e seus anexos, conforme a regra definida para cada órgão
- Organiza os arquivos em `Editais/<orgao>/<data-execucao>/`
- Registra log estruturado em planilha: URL, arquivos baixados, data, status e observações
- Sinaliza em vermelho as coletas que falharam, permitindo verificação manual pontual
- Envia e-mail automático às coordenadoras com o relatório em anexo

## Órgãos cobertos

BNDES · CAPES · CNPq · FAPEG · FINEP · SESI/SENAI

## Decisões técnicas

**Playwright em vez de Selenium.** Vários portais usam telas de carregamento e elementos que ficam sobrepostos durante a renderização, o que quebrava a execução com Selenium. O auto-wait nativo do Playwright resolveu isso sem espalhar `WebDriverWait` e `sleep` pelo código, deixando os fluxos mais curtos e legíveis.

**Classe base com implementação por órgão.** Cada portal tem estrutura, navegação e regra de download diferentes — alguns exigem baixar todos os arquivos, outros apenas a versão retificada. `base_orgao.py` define o fluxo comum da coleta e cada órgão herda dela com sua própria implementação. Isso permite ajustar ou adicionar um portal sem tocar nos demais, o que importa porque esses sites mudam de layout com frequência.

**Isolamento de falha por órgão.** A falha em um portal não interrompe a execução dos demais. O erro é registrado na planilha e o robô segue para o próximo órgão, garantindo que um site fora do ar não invalide a coleta do dia inteiro.

**Pasta por data de execução.** Cada execução gera sua própria pasta, preservando o histórico do que estava aberto em cada dia. Um edital aberto por vários dias é baixado novamente a cada execução — em um cenário de volume maior, o próximo passo seria controlar por hash do arquivo ou registro em banco, baixando apenas o que mudou.

**Agendamento por ferramenta externa.** A execução diária às 7h era feita pelo Agendador de Tarefas do Windows, chamando o `main.py` na máquina onde o robô rodava. Manter o agendamento fora do código deixou o projeto responsável apenas pela coleta, sem processo próprio rodando em segundo plano, e permitiu à equipe ajustar horário ou pausar a rotina sem depender de alteração no código.

## Testes por órgão

Os scripts em `testes/` validam o fluxo de navegação e download de cada portal isoladamente, sem executar a rotina completa. Foram usados durante o desenvolvimento e continuam úteis na manutenção: quando um portal muda de layout, dá para testar e corrigir apenas aquele fluxo.

## Stack

Python · Playwright · openpyxl · python-dotenv · smtplib

## Estrutura

```
├── main.py                  # Orquestra a execução dos órgãos
├── config.py                # Configurações e variáveis de ambiente
├── orgaos/
│   ├── base_orgao.py        # Classe base com o fluxo comum de coleta
│   ├── bndes.py             # Implementação específica de cada portal
│   ├── capes.py
│   ├── cnpq.py
│   ├── fapeg.py
│   ├── finep.py
│   └── sesi_senai.py
├── utils/
│   ├── email_sender.py      # Envio do relatório por e-mail
│   ├── file_manager.py      # Organização dos arquivos baixados
│   ├── logger.py            # Log de execução
│   └── report_generator.py  # Geração da planilha de relatório
├── testes/                  # Validação individual do fluxo de cada portal
└── requirements.txt
```

## Como rodar

```bash
git clone https://github.com/IgorManes/Robo-extrair-editais.git
cd Robo-extrair-editais

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
playwright install

cp .env.example .env          # preencha com suas credenciais
python main.py
```

### Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `EMAIL_REMETENTE` | Conta que envia o relatório |
| `EMAIL_SENHA` | Senha de aplicativo do remetente |
| `EMAIL_DESTINATARIOS` | Destinatários do relatório, separados por vírgula |
| `EMAIL_ASSUNTO` | Assunto do e-mail |
| `EMAIL_CORPO` | Texto do corpo do e-mail |
| `PASTA_EDITAIS` | Caminho onde os editais serão salvos |

## Observações

Os portais consultados são públicos. Credenciais de e-mail e caminhos de rede internos foram removidos — veja `.env.example` para as variáveis necessárias.
