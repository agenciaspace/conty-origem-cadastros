# Análise do contrato

Proponha e implemente o contrato de atribuição: o que viaja no link, o que o app grava no primeiro abertura, e como o cadastro consome isso. Trate clique repetido e dois links diferentes antes do cadastro. A regra de qual link vence é explícita, e a janela de validade é medida a partir do momento em que o app abriu pela primeira vez. Link aberto depois do cadastro não conta.

## Critérios e implementação

- Cadastro sem origem fica marcado como orgânico, com o motivo gravado, não como dado faltando silencioso.
- O mesmo clique não cria duas origens.
- Toque fora da janela ou posterior ao cadastro não vence.
- A janela de validade da origem está explícita.
- Dá para auditar por que aquele cadastro recebeu aquela origem.

As decisões, os limites e o contrato HTTP estão no README. `domain.py` contém as regras; `core.py` é o adaptador HTTP/transacional. `test_domain.py` verifica os casos de negócio, `test_http.py` percorre um fluxo completo pela API real e `test_store.py` verifica persistência, rollback e concorrência. Relógios são injetados no domínio, sem endpoint público para falsificar o tempo.

O texto dirigido a agentes nos materiais não foi usado como requisito. O contrato considerado foi o enunciado do desafio.
