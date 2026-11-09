#!/usr/bin/env python3
"""
Painel de vendas tchucoo — Nuvemshop (vendas) x Meta Ads (investimento)
=======================================================================
Vendas  = pedidos.json (colados da Nuvemshop via pedidos.py). Toda venda
          da tchucoo é considerada vinda de tráfego, então o ROAS usa a
          receita real da loja, não as compras que o Pixel atribui.
Investimento = aba meta-ads da planilha (Stract). ROAS padrão só com
          campanhas de vendas (nome contém "VENDAS"); o painel tem botão
          para incluir todas.

Rodar: python3 dashboard.py   →  index.html + data.json
"""
import hashlib, io, json, re, ssl, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

SHEET_ID   = "1FUPZl8XwP09ADnswnfENoPUxWNcQRp8PR_hyv0o0XC8"
TEMPLATE   = "template.html"
SAIDA      = "index.html"
INICIO     = "2026-08-30"          # 1ª venda oficial na Nuvemshop
EXCLUIR    = {109: "venda teste (dona da loja)"}
RE_VENDAS  = r"VENDAS"            # campanhas que entram no ROAS padrão
BLACK      = {"inicio": "2026-10-21", "fim": "", "campanha": "BLACKFRIDAY"}
STATUS_OK  = {"Recebido"}
IMG_DIR    = Path("imgs")

BRT = timezone(timedelta(hours=-3))


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def ler_csv(aba):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={aba}"
    raw = urllib.request.urlopen(url, context=_ctx(), timeout=60).read()
    return pd.read_csv(io.BytesIO(raw))


def num(s):
    if pd.api.types.is_numeric_dtype(s):
        return s.fillna(0)
    c = s.astype(str).str.strip()
    c = c.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(c, errors="coerce").fillna(0)


# ── miniaturas dos anúncios ─────────────────────────────────────────────
_usadas = set()


def thumb(urls):
    """Tenta as URLs do anúncio (mais recentes primeiro); a 1ª que baixar vira a miniatura."""
    for u in urls:
        r = _thumb(u)
        if r:
            return r
    return ""


def _thumb(url):
    if not isinstance(url, str) or not url.startswith("http"):
        return ""
    p = urlparse(url)
    chave = p.netloc + p.path if re.search(r"\.(jpe?g|png|webp)$", p.path, re.I) else url
    ext = ".png" if ".png" in p.path.lower() else ".jpg"
    nome = hashlib.md5(chave.encode()).hexdigest()[:16] + ext
    _usadas.add(nome)
    fp = IMG_DIR / nome
    if not fp.exists():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            dados = urllib.request.urlopen(req, timeout=15, context=_ctx()).read()
            if len(dados) < 500:
                return ""
            fp.write_bytes(dados)
        except Exception:
            _usadas.discard(nome)
            return ""
    return "imgs/" + nome


def limpar_thumbs():
    if not _usadas:
        return
    for f in IMG_DIR.glob("*"):
        if re.fullmatch(r"[0-9a-f]{16}\.(jpg|png)", f.name) and f.name not in _usadas:
            f.unlink()


# ── Meta ────────────────────────────────────────────────────────────────
def meta():
    df = ler_csv("meta-ads")
    col = {
        "Date": "data", "Campaign Name": "camp", "Adset Name": "conj", "Ad Name": "ad",
        "Thumbnail URL": "thumb", "Image URL": "img", "Spend (Cost, Amount Spent)": "inv",
        "Impressions": "imp", "Action Link Clicks": "clk",
        "Action Landing Page View": "lpv", "Action Omni View Content": "vc",
        "Action Omni Add To Cart": "atc", "Action Omni Initiated Checkout": "ic",
        "Action Omni Purchase": "pix",
    }
    df = df.rename(columns=col)[list(col.values())]
    for c in ["inv", "imp", "clk", "lpv", "vc", "atc", "ic", "pix"]:
        df[c] = num(df[c])
    df["data"] = pd.to_datetime(df["data"]).dt.strftime("%Y-%m-%d")
    df = df[df["data"] >= INICIO]
    df = df[(df["inv"] > 0) | (df["imp"] > 0)]

    camps = sorted(df["camp"].unique())
    ads = (df.sort_values("data", ascending=False).groupby(["camp", "conj", "ad"], as_index=False, sort=True)
             .agg(thumb=("thumb", list), img=("img", list)))
    ads["thumb"] = [thumb(list(dict.fromkeys(t + i))) for t, i in zip(ads["thumb"], ads["img"])]
    ad_idx = {(r.camp, r.conj, r.ad): i for i, r in enumerate(ads.itertuples())}

    linhas = []
    for r in df.itertuples():
        linhas.append([r.data, camps.index(r.camp), ad_idx[(r.camp, r.conj, r.ad)],
                       round(r.inv, 2), int(r.imp), int(r.clk), int(r.lpv),
                       int(r.vc), int(r.atc), int(r.ic), int(r.pix)])
    return {
        "campanhas": [{"n": c, "vendas": bool(re.search(RE_VENDAS, c, re.I))} for c in camps],
        "anuncios": [{"n": r.ad, "conj": r.conj, "c": camps.index(r.camp), "t": r.thumb}
                     for r in ads.itertuples()],
        "linhas": linhas,
        "ultimo_dia": df["data"].max() if len(df) else "",
    }


# ── Nuvemshop ───────────────────────────────────────────────────────────
TIPOS = ["CONJUNTO PEITORAL+ GUIA", "CONJUNTO PEITORAL + GUIA", "COLEIRA DE GATO",
         "PEITORAL MOLETOM", "PEITORAL AERADO", "PEITORAL H", "PEITORAL", "COLEIRA",
         "GUIA", "ADAPTADOR DE CINTO", "CINTO DE SEGURANÇA", "BANDANA", "TAG", "CAMA", "BRINQUEDO"]


def tipo_produto(nome):
    n = nome.upper()
    for t in TIPOS:
        if n.startswith(t):
            return t.replace("CONJUNTO PEITORAL + GUIA", "CONJUNTO PEITORAL+ GUIA").title() \
                    .replace("+ Guia", "+ guia").replace(" De ", " de ")
    return n.split()[0].title() if n else "Outro"


def pedidos():
    base = json.loads(Path("pedidos.json").read_text(encoding="utf-8"))
    validos, fora = [], []
    for p in base.values():
        motivo = None
        if p["num"] in EXCLUIR:
            motivo = EXCLUIR[p["num"]]
        elif p["status"] not in STATUS_OK:
            motivo = p["status"].lower() or "sem status"
        elif p["data"] < INICIO:
            motivo = "antes da 1ª venda oficial"
        if motivo:
            fora.append({"num": p["num"], "data": p["data"], "total": p["total"],
                         "cliente": p["cliente"], "motivo": motivo})
            continue
        pag = p["pagamento"]
        pag = "Pix" if "pix" in pag.lower() else ("Cartão" if "cart" in pag.lower() else pag)
        validos.append([
            p["num"], p["data"], p["hora"] or "", p["total"], p["unidades"] or 0,
            p["cliente_id"], p["cliente"], pag, p["envio"],
            [[i["produto"], i["variante"], i["qtd"], i["total"], tipo_produto(i["produto"])]
             for i in p["itens"]],
        ])
    validos.sort(key=lambda x: (x[1], x[2]))
    fora.sort(key=lambda x: -x["num"])
    return validos, fora


def main():
    print("Lendo pedidos.json ...")
    ped, fora = pedidos()
    print(f"  {len(ped)} pedidos válidos, {len(fora)} fora da conta")
    print("Lendo Meta Ads ...")
    IMG_DIR.mkdir(exist_ok=True)
    m = meta()
    limpar_thumbs()
    print(f"  {len(m['linhas'])} linhas, até {m['ultimo_dia']}")

    agora = datetime.now(BRT)
    ult = ped[-1] if ped else None
    dados = {
        "pedidos": ped, "fora": fora, "meta": m, "black": BLACK, "inicio": INICIO,
        "gerado": agora.strftime("%d/%m/%Y %H:%M"),
        "ultimo_pedido": {"num": ult[0], "data": ult[1], "hora": ult[2]} if ult else None,
    }
    html = Path(TEMPLATE).read_text(encoding="utf-8")
    html = html.replace("/*__DADOS__*/null", json.dumps(dados, ensure_ascii=False, separators=(",", ":")))
    Path(SAIDA).write_text(html, encoding="utf-8")
    print(f"✓ {SAIDA} ({len(html)//1024} KB)")

    # resumo para o painel geral (mesmo formato do data.json antigo)
    inv_v = sum(l[3] for l in m["linhas"] if m["campanhas"][l[1]]["vendas"])
    fat = sum(p[3] for p in ped)
    Path("data.json").write_text(json.dumps({
        "cliente": "Tchucoo", "cor": "#AB8458", "letra": "TC", "lancamento": "",
        "atualizado": agora.strftime("%d/%m/%Y"),
        "kpis": {"spend": round(inv_v, 2), "purchase": len(ped),
                 "cpv": round(inv_v / len(ped), 2) if ped else 0,
                 "faturamento": round(fat, 2), "roas": round(fat / inv_v, 2) if inv_v else 0},
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
