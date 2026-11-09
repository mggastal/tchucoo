#!/usr/bin/env python3
"""
Pedidos da Nuvemshop (fonte de verdade das vendas da tchucoo)
=============================================================
Lê a lista de vendas copiada do painel da Nuvemshop (com ou sem o detalhe
dos produtos) e junta em pedidos.json, sem duplicar.

Uso:
    python3 pedidos.py colar.txt          # arquivo com o texto colado
    pbpaste | python3 pedidos.py          # direto da área de transferência

Regras:
- O número do pedido (#216) é a chave. Colar de novo o mesmo pedido só
  atualiza status/itens; nunca duplica.
- Se a colagem nova não traz os produtos, os produtos já salvos ficam.
- Ano: a Nuvemshop mostra só "8 nov". Usa o ano corrente; se a data cair
  no futuro, volta um ano.
"""
import json, re, sys
from datetime import date, datetime
from pathlib import Path

ARQ = Path(__file__).with_name("pedidos.json")

MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
         "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}

RE_NUM   = re.compile(r"^#(\d+)$")
RE_DATA  = re.compile(r"^(\d{1,2}) (\w{3})\.?$", re.I)
RE_HORA  = re.compile(r"^(\d{1,2}):(\d{2})$")
RE_VALOR = re.compile(r"^R\$\s*([\d.]+,\d{2})$")
RE_UNID  = re.compile(r"^(\d+) unid\.?(?:\s+(\S.*))?$")
RE_QTDX  = re.compile(r"^(\d+)x R\$\s*([\d.]+,\d{2})$")
RE_SKU   = re.compile(r"^SKU:\s*(\S*)")
RE_PROD  = re.compile(r"^(.+?) - (\d{6,})$")
CABEC    = {"Produto", "Unidades", "Preço unitário", "Total", "Venda", "Data",
            "Cliente", "Produtos", "Pagamento", "Envio"}


def brl(s):
    return round(float(s.replace(".", "").replace(",", ".")), 2)


def cliente_id(nome):
    """O repositório é público: o nome completo do cliente não é salvo.
    Fica um código (para contar recompra) e o nome abreviado ("Rayssa C.")."""
    import hashlib, unicodedata
    n = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    n = " ".join(n.split())
    return hashlib.sha1(n.encode()).hexdigest()[:10]


def abreviar(nome):
    partes = nome.split()
    if len(partes) <= 1:
        return nome
    return f"{partes[0].title()} {partes[-1][0].upper()}."


def inferir_data(dia, mes_txt, hoje=None):
    hoje = hoje or date.today()
    mes = MESES[mes_txt.lower()[:3]]
    d = date(hoje.year, mes, int(dia))
    if d > hoje:
        d = date(hoje.year - 1, mes, int(dia))
    return d


def parse(texto, hoje=None):
    linhas = [l.strip() for l in texto.replace("\r", "").split("\n")]
    linhas = [l for l in linhas if l]
    # início de cada pedido: "#123" seguido de uma data "8 nov"
    inicios = [i for i, l in enumerate(linhas)
               if RE_NUM.match(l) and i + 1 < len(linhas) and RE_DATA.match(linhas[i + 1])]
    pedidos = []
    for k, ini in enumerate(inicios):
        fim = inicios[k + 1] if k + 1 < len(inicios) else len(linhas)
        bloco = linhas[ini:fim]
        p = _pedido(bloco, hoje)
        if p:
            pedidos.append(p)
    return pedidos


def _pedido(b, hoje):
    num = int(RE_NUM.match(b[0]).group(1))
    m = RE_DATA.match(b[1])
    d = inferir_data(m.group(1), m.group(2), hoje)
    i = 2
    hora = None
    if i < len(b) and RE_HORA.match(b[i]):
        h, mi = RE_HORA.match(b[i]).groups()
        hora = f"{int(h):02d}:{mi}"
        i += 1
    cliente = b[i] if i < len(b) else ""
    i += 1
    total = None
    if i < len(b) and RE_VALOR.match(b[i]):
        total = brl(RE_VALOR.match(b[i]).group(1)); i += 1
    if total is None:
        return None
    unid, status = None, None
    if i < len(b) and RE_UNID.match(b[i]):
        mu = RE_UNID.match(b[i]); unid = int(mu.group(1)); status = mu.group(2); i += 1
    if not status and i < len(b):
        status = b[i]; i += 1
    pagamento = b[i] if i < len(b) else ""; i += 1
    envio_status = b[i] if i < len(b) else ""; i += 1
    envio = b[i] if i < len(b) and b[i] not in CABEC else ""; i += 1

    # itens: ancorados na linha "1x R$ 25,99"
    resto = b[i:]
    itens = []
    for j, l in enumerate(resto):
        mq = RE_QTDX.match(l)
        if not mq:
            continue
        qtd, preco = int(mq.group(1)), brl(mq.group(2))
        sku, nome, variante = "", "", ""
        # volta até o cabeçalho "NOME - 354290877"
        jj = j - 1
        if jj >= 0 and RE_SKU.match(resto[jj]):
            sku = RE_SKU.match(resto[jj]).group(1); jj -= 1
        meio = []
        while jj >= 0 and not RE_PROD.match(resto[jj]) and not RE_QTDX.match(resto[jj]) \
                and resto[jj] not in CABEC and not RE_VALOR.match(resto[jj]):
            meio.insert(0, resto[jj]); jj -= 1
        if jj >= 0 and RE_PROD.match(resto[jj]):
            nome = RE_PROD.match(resto[jj]).group(1).strip()
            meio = [x for x in meio if x.strip().upper() != nome.upper()]
        elif meio:
            nome = meio.pop(0)
        variante = " ".join(meio).strip()
        if variante.lower() == "tamanho único":
            variante = "Único"
        itens.append({"produto": nome, "variante": variante, "sku": sku,
                      "qtd": qtd, "preco": preco, "total": round(qtd * preco, 2)})

    return {"num": num, "data": d.isoformat(), "hora": hora,
            "cliente": abreviar(cliente), "cliente_id": cliente_id(cliente),
            "total": total, "unidades": unid, "status": status or "",
            "pagamento": pagamento, "envio_status": envio_status, "envio": envio,
            "itens": itens}


def carregar():
    if ARQ.exists():
        return {int(k): v for k, v in json.loads(ARQ.read_text(encoding="utf-8")).items()}
    return {}


def salvar(base):
    dados = {str(k): base[k] for k in sorted(base, reverse=True)}
    ARQ.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def juntar(base, novos):
    n_novos = n_atual = n_itens = 0
    for p in novos:
        ant = base.get(p["num"])
        if ant is None:
            base[p["num"]] = p; n_novos += 1
            continue
        if not p["itens"] and ant.get("itens"):
            p["itens"] = ant["itens"]
        elif p["itens"] and not ant.get("itens"):
            n_itens += 1
        if p != ant:
            n_atual += 1
        base[p["num"]] = p
    return n_novos, n_atual, n_itens


def parse_csv(caminho):
    """Export de vendas da Nuvemshop (CSV ; latin-1, uma linha por produto).
    Dados pessoais (CPF, e-mail, endereço) são ignorados."""
    import csv
    raw = Path(caminho).read_bytes()
    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError:
        txt = raw.decode("latin-1")
    pedidos = {}
    for r in csv.DictReader(txt.splitlines(), delimiter=";"):
        num = int(r["Número do Pedido"])
        if num not in pedidos:
            dt = datetime.strptime(r["Data"], "%d/%m/%Y %H:%M:%S")
            pag = (r.get("Status do Pagamento") or "").strip()
            meio = (r.get("Meio de pagamento") or "").strip()
            meio = {"pix": "Pix", "credit_card": "Cartão de crédito"}.get(meio.lower(), meio)
            pedidos[num] = {
                "num": num, "data": dt.date().isoformat(), "hora": dt.strftime("%H:%M"),
                "cliente": abreviar(r["Nome do comprador"]), "cliente_id": cliente_id(r["Nome do comprador"]),
                "total": round(float(r["Total"]), 2), "unidades": 0,
                "status": "Recebido" if pag == "Confirmado" else pag,
                "pagamento": f"{r.get('Forma de Pagamento','')} - {meio}".strip(" -"),
                "envio_status": r.get("Status do Envio", ""), "envio": r.get("Forma de Entrega", ""),
                "itens": []}
        nome = r["Nome do Produto"].strip()
        m = re.match(r"^(.*?)\s*\(([^()]*)\)$", nome)
        nome, var = (m.group(1), m.group(2)) if m else (nome, "Único")
        qtd = int(float(r["Quantidade Comprada"] or 1)); preco = round(float(r["Valor do Produto"]), 2)
        pedidos[num]["itens"].append({"produto": nome, "variante": var, "sku": r.get("SKU", ""),
                                      "qtd": qtd, "preco": preco, "total": round(qtd * preco, 2)})
        pedidos[num]["unidades"] += qtd
    return list(pedidos.values())


def main():
    arq = sys.argv[1] if len(sys.argv) > 1 else None
    if arq and arq.lower().endswith(".csv"):
        novos = parse_csv(arq)
    else:
        texto = Path(arq).read_text(encoding="utf-8") if arq else sys.stdin.read()
        novos = parse(texto)
    if not novos:
        sys.exit("Nenhum pedido encontrado no texto colado.")
    base = carregar()
    n, a, it = juntar(base, novos)
    salvar(base)
    sem_itens = [p["num"] for p in novos if not p["itens"]]
    print(f"Lidos {len(novos)} pedidos (#{min(p['num'] for p in novos)} a #{max(p['num'] for p in novos)}): "
          f"{n} novos, {a} atualizados, {it} ganharam produtos.")
    for p in novos:
        if p["itens"]:
            soma = round(sum(x["total"] for x in p["itens"]), 2)
            if soma > p["total"] + 0.01:
                print(f"  aviso #{p['num']}: itens somam R$ {soma} > total R$ {p['total']}")
    if sem_itens:
        print(f"  sem produtos na colagem: {len(sem_itens)} pedidos")
    print(f"Base: {len(base)} pedidos em {ARQ.name}")


if __name__ == "__main__":
    main()
