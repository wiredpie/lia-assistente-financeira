# Base de Conhecimento

## Dados Utilizados

Utilizei os dados fornecidos pelo curso porém editados pelo Gemini, tornando-os mais robustos e com um histórico de transações maior, assim, possibilitando que o agente cumpra as funções propostas de forma mais eficiente.

---

## Estratégia de Integração

Cliente
   ↓
Lia interpreta a pergunta
   ↓
Lia extrai intenção + parâmetros
   ↓
script.py
   ↓
gastos.py / investimentos.py
   ↓
dados processados + cálculos
   ↓
script.py filtra o que é relevante
   ↓
Lia formula a resposta
   ↓
Cliente

### Como os dados são carregados?
Todo acesso e informações necessárias para a agente é feito através do script principal em python.
Para a limpeza e normalizaçao de dados, foi feito o programa utils.py: assim, apenas os dados relevantes para o escopo de atendimento da Lia sao tratados e encaminhados para as outras automaçoes, e, posteriormente, a propria agente. 

### Como os dados são usados no prompt?
Lia apenas tem contato com alguns dos dados tratados e outros que ela precisa para fornecer os parametros as chamadas de funçao. De resto, apenas o python lida com eles. 

---

## Exemplo de Contexto Montado

- Informações básicas sobre o cliente 
    Nome, renda mensal, status da conta
- Perfil investidor
    Moderado, não aceita risco variado
- Histórico de atendimento 
    Informações sobre histórico de atendimento
- Produtos financeiros adquiridos 
    Produtos onde seu dinheiro está investido
