# Origem do cadastro no app

Contrato sem dependência de referrer: links contêm `touch_id`, identificador
opaco de origem registrada no servidor (`campaign`, `referral` ou `community`).
O app persiste um `installation_id` aleatório na primeira abertura e envia
`POST /opens`, mesmo sem link. A primeira abertura é gravada pelo servidor e
não muda com retries. O deep link encaminha `touch_id`; na conclusão do cadastro,
o app envia `installation_id` em `POST /registrations`.

A janela é **7 dias corridos a partir da primeira abertura da instalação**,
limite final inclusivo. Ela não é renovada por clique/reabertura. Dentro dela,
o último toque anterior ou simultâneo ao cadastro vence; empate de horário usa
menor ID de toque em ordem lexicográfica. Mesmo link na mesma instalação mantém
o primeiro instante; instalações diferentes não se confundem.

Sem toque elegível, grava `organic` e o motivo. A atribuição do cadastro é
imutável. A consulta mostra tanto a decisão congelada quanto uma auditoria
atual com todos os toques, inclusive os posteriores, explicitamente excluídos.
O relógio é do servidor; o cliente não informa timestamps arbitrários.

## Exemplo

Links ilustrativos (o domínio `.example` não é um serviço publicado):
`https://app.example/open?touch_id=camp-outubro` e
`https://app.example/open?touch_id=ref-alice`.

```bash
curl -s "$BASE/links" -H 'Content-Type: application/json' -d '{"id":"camp-outubro","source":"campaign","reference":"outubro"}'
curl -s "$BASE/links" -H 'Content-Type: application/json' -d '{"id":"ref-alice","source":"referral","reference":"alice"}'
curl -s "$BASE/opens" -H 'Content-Type: application/json' -d '{"installation_id":"i1","touch_id":"camp-outubro"}'
curl -s "$BASE/opens" -H 'Content-Type: application/json' -d '{"installation_id":"i1","touch_id":"ref-alice"}'
curl -s "$BASE/registrations" -H 'Content-Type: application/json' -d '{"id":"u1","installation_id":"i1"}'
curl -s "$BASE/registrations/u1"
```

O cadastro atribui `source: "referral"`, `reference: "alice"`; a auditoria marca
a campanha `superseded_by_later_touch` e a indicação `winner`. Se horários forem
exatamente iguais, vale o desempate documentado. Cada toque contém seu
`opened_at`, origem, referência e motivo. Clique pós-cadastro recebe
`after_registration`; janela vencida recebe `outside_first_open_window`.

Com mais tempo: Universal/App Links reais, deferred deep linking após instalação,
assinatura/expiração dos links, consentimento, expurgo e conciliação entre
aparelhos. O armazenamento local do app e a configuração iOS/Android são contrato
documentado; esta entrega implementa a API, não um aplicativo móvel.

## Rodar e verificar

Python 3.12 com base de fusos IANA (incluída no Ubuntu); sem `pip install`.

```bash
python3 -m unittest -v
python3 app.py
```

API na porta 8080. `PORT`, `HOST` (padrão 127.0.0.1), `DATABASE_PATH` (padrão
`data.sqlite3`) e `API_TOKEN` configuram o processo. Com `API_TOKEN`, envie
`Authorization: Bearer ...`; `/health` fica público. Os exemplos abaixo usam
`BASE` como a URL do processo ou de um proxy HTTPS. `test_http.py` executa o
fluxo pela rede HTTP real, além dos testes de domínio com relógio controlado.

Respostas são JSON; sucesso 200, entrada inválida 422, conflito 409, ausente
404. JSON malformado retorna 400. SQLite persiste estado em transações
`BEGIN IMMEDIATE`; uma operação inválida faz rollback, inclusive de alterações
parciais. Reiniciar preserva dados. Cada execução de testes usa banco isolado.

## Limites desta entrega

O adaptador HTTP é uma demonstração síncrona, não um servidor de produção.
SQLite guarda um documento de estado por aplicação: simples para verificar as
invariantes e a persistência, mas inadequado para grande volume. Com mais tempo,
normalizaria tabelas e índices, adicionaria autenticação por usuário/tenant,
limites operacionais, observabilidade e migrações. O token compartilhado não
substitui autorização por recurso. Não exponha dados reais neste demo.

## Uso de IA

Codex implementou, testou e fez revisão automatizada das regras, exemplos e
resultados a pedido de Leon Hatori. Não declaramos revisão humana que ainda
não ocorreu. Detalhes em [AI_USAGE.md](AI_USAGE.md).
