# tchucoo · Painel de Vendas

https://mggastal.github.io/tchucoo/

- **Vendas** = pedidos pagos da Nuvemshop, guardados em `pedidos.json`. Toda venda conta como tráfego, então o ROAS usa a receita real da loja (não as compras do Pixel).
- **Investimento** = aba `meta-ads` da planilha Stract. ROAS padrão só com campanhas que têm `VENDAS` no nome; o painel tem botão para todas.

## Atualizar vendas
1. Copiar a lista de vendas do painel da Nuvemshop (de preferência com o detalhe dos produtos) e salvar em `colagens/AAAA-MM-DD.txt` (pasta fora do git).
2. `python3 pedidos.py colagens/AAAA-MM-DD.txt` (junta sem duplicar; recusados ficam fora das contas).
3. `python3 dashboard.py` e commit de `pedidos.json`, `index.html`, `data.json`.

A GitHub Action roda todo dia às 06:00 e atualiza o investimento do Meta.

Regras em `dashboard.py`: `INICIO` (1ª venda oficial 30/08/2026), `EXCLUIR` (#109 venda teste), `BLACK` (21/10 em diante).
O nome completo do cliente não é salvo (repositório público): fica nome abreviado + código para contar recompra.

`antigo/` guarda o gerador anterior (só Meta Ads); `relatorio_22set.html` e `pauta_reuniao_28ago.html` ficam como estavam.
