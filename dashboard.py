#!/usr/bin/env python3
"""
Gerador Dashboard E-commerce — Meta Ads
========================================
Funil: Impressões → Link Clicks → Page View → View Content
        → Add to Cart → Init Checkout → Purchase

Conversão principal: Purchase (Action Omni Purchase)
"""

import pandas as pd, json, re, hashlib, requests
from datetime import date
from pathlib import Path

# ══════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════
SHEET_ID         = "1FUPZl8XwP09ADnswnfENoPUxWNcQRp8PR_hyv0o0XC8"
TEMPLATE_FILE    = "dashboard.html"
OUTPUT_FILE      = "index.html"

NOME_CLIENTE     = "Tchucoo"
LOGO_LETRA       = "TC"
COR_ACENTO       = "#AD96DC"

LANCAMENTO_COD   = ""        # filtra campanhas; "" = ver tudo

# Metas do funil e-commerce — define cores (verde/amarelo/vermelho)
CPV_BOM          = 50.0     # Custo por Venda ≤ 50 → verde
CPV_MEDIO        = 80.0     # Custo por Venda ≤ 80 → amarelo | acima → vermelho
CTR_BOM          = 1.5      # CTR Link ≥ 1.5% → verde
CTR_MEDIO        = 0.8      # CTR Link ≥ 0.8% → amarelo
CPM_BOM          = 5.0      # CPM ≤ 5 → verde
CPM_MEDIO        = 12.0     # CPM ≤ 12 → amarelo
# Taxas de conversão do funil (maiores = melhor)
CR_BOM           = 60.0     # Connect Rate (PV/LC) ≥ 60% → verde
CR_MEDIO         = 35.0
VC_BOM           = 40.0     # View Content Rate (VC/PV) ≥ 40% → verde
VC_MEDIO         = 20.0
ATC_BOM          = 10.0     # Add to Cart Rate (ATC/VC) ≥ 10% → verde
ATC_MEDIO        = 5.0
IC_BOM           = 60.0     # Init Checkout Rate (IC/ATC) ≥ 60% → verde
IC_MEDIO         = 35.0
PURCH_BOM        = 40.0     # Purchase Rate (P/IC) ≥ 40% → verde
PURCH_MEDIO      = 20.0

# ══════════════════════════════════════════════════════
def sheet_url(t): return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={t}"
URL_META = sheet_url("meta-ads")
URL_GA   = sheet_url("breakdown-gender-age")
URL_PT   = sheet_url("breakdown-platform")
URL_REG  = sheet_url("breakdown-regiao")

def to_num(s):
    if pd.api.types.is_numeric_dtype(s): return s.fillna(0)
    clean = s.astype(str).str.strip().str.replace("R$","",regex=False).str.strip()
    if clean.str.contains(r"\d,\d", regex=True).any():
        clean = clean.str.replace(".","",regex=False).str.replace(",",".",regex=False)
    return pd.to_numeric(clean, errors="coerce").fillna(0)

def safe(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return None
    return round(float(v),2) if float(v)!=0 else None

def download_thumb(url, d):
    if not url or str(url)=="nan": return ""
    try:
        ext=".png" if ".png" in url.lower() else ".jpg"
        fname=hashlib.md5(url.encode()).hexdigest()[:16]+ext
        fp=d/fname
        if not fp.exists():
            r=requests.get(url,timeout=10,headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code==200: fp.write_bytes(r.content)
            else: return ""
        return "imgs/"+fname
    except: return ""

# ══ META ADS ══════════════════════════════════════════
def load_meta():
    print("  Lendo meta-ads...")
    df=pd.read_csv(URL_META)
    df=df.rename(columns={
        "Date":"date",
        "Campaign Name":"campaign",
        "Adset Name":"adset",
        "Ad Name":"ad",
        "Thumbnail URL":"thumb",
        "Spend (Cost, Amount Spent)":"spend",
        "Impressions":"impressions",
        "Action Link Clicks":"link_clicks",
        "Action Landing Page View":"page_view",
        "Clicks":"clicks",
        "Action Omni View Content":"view_content",
        "Action Omni Add To Cart":"add_to_cart",
        "Action Omni Initiated Checkout":"init_checkout",
        "Action Omni Purchase":"purchase",
        "Action Post Engagement":"engagement",
    })
    df["date"]=pd.to_datetime(df["date"],errors="coerce")
    for c in ["spend","impressions","link_clicks","page_view","clicks",
              "view_content","add_to_cart","init_checkout","purchase","engagement"]:
        if c in df.columns: df[c]=to_num(df[c])
        else: df[c]=0
    if "clicks" not in df.columns: df["clicks"]=df["link_clicks"]
    df["is_lct"]=df["campaign"].str.contains(LANCAMENTO_COD,na=False,case=False) if LANCAMENTO_COD else True
    df=df.dropna(subset=["date"])
    print(f"     {len(df)} linhas | {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"     Compras: {df['purchase'].sum():.0f} | Invest.: R${df['spend'].sum():.2f}")
    return df

def calc_kpis(p):
    sp=float(p["spend"].sum()); imp=float(p["impressions"].sum())
    lc=float(p["link_clicks"].sum()); pv=float(p["page_view"].sum())
    vc=float(p["view_content"].sum()); atc=float(p["add_to_cart"].sum())
    ic=float(p["init_checkout"].sum()); pu=float(p["purchase"].sum())
    cl=float(p["clicks"].sum()) if "clicks" in p.columns else lc
    return {
        "spend":round(sp,2),
        "impressions":int(imp),
        "link_clicks":int(lc),
        "clicks":int(cl),
        "page_view":int(pv),
        "view_content":int(vc),
        "add_to_cart":int(atc),
        "init_checkout":int(ic),
        "purchase":int(pu),
        # Taxas do funil
        "ctr":          round(lc/imp*100,2) if imp>0 else None,
        "ctr_all":      round(cl/imp*100,2) if imp>0 else None,
        "connect_rate": round(pv/lc*100,2)  if lc>0  else None,
        "vc_rate":      round(vc/pv*100,2)  if pv>0  else None,
        "atc_rate":     round(atc/vc*100,2) if vc>0  else None,
        "ic_rate":      round(ic/atc*100,2) if atc>0 else None,
        "purch_rate":   round(pu/ic*100,2)  if ic>0  else None,
        # Custos
        "cpv":  round(sp/pu,2)  if pu>0  else None,   # Custo por Venda
        "cpa":  round(sp/atc,2) if atc>0 else None,   # Custo por Add to Cart
        "cpm":  round(sp/imp*1000,2) if imp>0 else None,
    }

def meta_kpis(df):
    return {"lct":calc_kpis(df[df["is_lct"]]),"all":calc_kpis(df)}

def build_daily(p):
    has_eng="engagement" in p.columns
    has_clicks="clicks" in p.columns
    agg_cols=dict(
        spend=("spend","sum"),impressions=("impressions","sum"),
        link_clicks=("link_clicks","sum"),page_view=("page_view","sum"),
        view_content=("view_content","sum"),add_to_cart=("add_to_cart","sum"),
        init_checkout=("init_checkout","sum"),purchase=("purchase","sum"),
    )
    if has_eng: agg_cols["engagement"]=("engagement","sum")
    if has_clicks: agg_cols["clicks"]=("clicks","sum")
    agg=p.groupby("date").agg(**agg_cols).reset_index().sort_values("date")
    out={k:[] for k in ["days","spend","impressions","link_clicks","clicks","page_view",
                         "view_content","add_to_cart","init_checkout","purchase",
                         "ctr","ctr_all","connect_rate","vc_rate","atc_rate","ic_rate",
                         "purch_rate","cpv","cpm","engagement"]}
    for _,r in agg.iterrows():
        sp=float(r["spend"]); imp=float(r["impressions"]); lc=float(r["link_clicks"])
        pv=float(r["page_view"]); vc=float(r["view_content"]); atc=float(r["add_to_cart"])
        ic=float(r["init_checkout"]); pu=float(r["purchase"])
        cl=float(r["clicks"]) if has_clicks else lc
        eng=float(r["engagement"]) if has_eng else 0
        out["days"].append(r["date"].strftime("%d/%m"))
        out["spend"].append(round(sp,2)); out["impressions"].append(int(imp))
        out["link_clicks"].append(int(lc)); out["clicks"].append(int(cl))
        out["page_view"].append(int(pv)); out["view_content"].append(int(vc))
        out["add_to_cart"].append(int(atc)); out["init_checkout"].append(int(ic))
        out["purchase"].append(int(pu)); out["engagement"].append(int(eng))
        out["ctr"].append(round(lc/imp*100,2) if imp>0 else None)
        out["ctr_all"].append(round(cl/imp*100,2) if imp>0 else None)
        out["connect_rate"].append(round(pv/lc*100,2) if lc>0 else None)
        out["vc_rate"].append(round(vc/pv*100,2) if pv>0 else None)
        out["atc_rate"].append(round(atc/vc*100,2) if vc>0 else None)
        out["ic_rate"].append(round(ic/atc*100,2) if atc>0 else None)
        out["purch_rate"].append(round(pu/ic*100,2) if ic>0 else None)
        out["cpv"].append(round(sp/pu,2) if pu>0 else None)
        out["cpm"].append(round(sp/imp*1000,2) if imp>0 else None)
    return out

def meta_daily(df):
    return {"lct":build_daily(df[df["is_lct"]]),"all":build_daily(df)}

def meta_daily_camps(df):
    result={"lct":{},"all":{}}
    for key,subset in [("lct",df[df["is_lct"]]),("all",df)]:
        for camp in subset["campaign"].unique():
            result[key][camp]=build_daily(subset[subset["campaign"]==camp])
    return result

def meta_raw(df):
    rows=[]
    agg=df.groupby(["date","campaign","adset","is_lct"]).agg(
        spend=("spend","sum"),purchase=("purchase","sum"),
        impressions=("impressions","sum"),link_clicks=("link_clicks","sum"),
        clicks=("clicks","sum"),page_view=("page_view","sum"),
        view_content=("view_content","sum"),add_to_cart=("add_to_cart","sum"),
        init_checkout=("init_checkout","sum"),
    ).reset_index()
    for _,r in agg.iterrows():
        rows.append({
            "d":r["date"].strftime("%d/%m"),"c":str(r["campaign"]),"a":str(r["adset"]),
            "lct":bool(r["is_lct"]),"sp":round(float(r["spend"]),2),
            "pu":int(r["purchase"]),"imp":int(r["impressions"]),
            "lc":int(r["link_clicks"]),"cl":int(r["clicks"]),"pv":int(r["page_view"]),
            "vc":int(r["view_content"]),"atc":int(r["add_to_cart"]),"ic":int(r["init_checkout"]),
        })
    return rows

def meta_tables_period(df, p, img_dir):
    def ag(sub,cols): return sub.groupby(cols).agg(
        spend=("spend","sum"),impressions=("impressions","sum"),
        link_clicks=("link_clicks","sum"),clicks=("clicks","sum"),
        page_view=("page_view","sum"),view_content=("view_content","sum"),
        add_to_cart=("add_to_cart","sum"),init_checkout=("init_checkout","sum"),
        purchase=("purchase","sum"),
    ).reset_index()

    def calc_row(r):
        sp=round(float(r["spend"]),2); imp=int(r["impressions"]); lc=int(r["link_clicks"])
        cl=int(r["clicks"]) if "clicks" in r.index else lc
        pv=int(r["page_view"]); vc=int(r["view_content"]); atc=int(r["add_to_cart"])
        ic=int(r["init_checkout"]); pu=int(r["purchase"])
        return {"spend":sp,"imp":imp,"lc":lc,"cl":cl,"pv":pv,"vc":vc,"atc":atc,"ic":ic,"pu":pu,
            "ctr":         round(lc/imp*100,2) if imp>0  else None,
            "ctr_all":     round(cl/imp*100,2) if imp>0  else None,
            "connect_rate":round(pv/lc*100,2)  if lc>0   else None,
            "vc_rate":     round(vc/pv*100,2)  if pv>0   else None,
            "atc_rate":    round(atc/vc*100,2) if vc>0   else None,
            "ic_rate":     round(ic/atc*100,2) if atc>0  else None,
            "purch_rate":  round(pu/ic*100,2)  if ic>0   else None,
            "cpv":         round(sp/pu,2)       if pu>0   else None,
            "cpm":         round(sp/imp*1000,2) if imp>0  else None,
        }

    camps_agg=ag(p,"campaign")
    camps=[{"n":str(r["campaign"]),**calc_row(r)} for _,r in camps_agg.sort_values("purchase",ascending=False).iterrows()]
    adsets_agg=ag(p,["campaign","adset"])
    adsets=[{"n":str(r["adset"]),"camp":str(r["campaign"]),**calc_row(r)} for _,r in adsets_agg.sort_values("purchase",ascending=False).iterrows()]

    df_full_thumb=df[df["thumb"].notna()&(df["thumb"].astype(str)!="nan")] if "thumb" in df.columns else pd.DataFrame()
    thumb_map={}
    for _,r in df_full_thumb.iterrows():
        k=(str(r["ad"]),str(r["adset"]),str(r["campaign"]))
        if k not in thumb_map: thumb_map[k]=download_thumb(str(r["thumb"]),img_dir)

    ads_agg=p.groupby(["ad","adset","campaign"]).agg(
        spend=("spend","sum"),impressions=("impressions","sum"),
        link_clicks=("link_clicks","sum"),clicks=("clicks","sum"),
        purchase=("purchase","sum"),add_to_cart=("add_to_cart","sum"),
    ).reset_index().sort_values("purchase",ascending=False)
    ads=[]
    for _,r in ads_agg.iterrows():
        sp=round(float(r["spend"]),2); imp=int(r["impressions"])
        lc=int(r["link_clicks"]); cl=int(r["clicks"]) if "clicks" in r.index else lc
        pu=int(r["purchase"]); atc=int(r["add_to_cart"])
        k=(str(r["ad"]),str(r["adset"]),str(r["campaign"]))
        ads.append({"n":str(r["ad"]),"adset":str(r["adset"]),"camp":str(r["campaign"]),
            "thumb":thumb_map.get(k,""),"spend":sp,"imp":imp,"lc":lc,"cl":cl,"pu":pu,"atc":atc,
            "ctr":round(lc/imp*100,2) if imp>0 else None,
            "ctr_all":round(cl/imp*100,2) if imp>0 else None,
            "cpv":round(sp/pu,2) if pu>0 else None,
        })
    return {"camps":camps,"adsets":adsets,"ads":ads}

def meta_tables(df, img_dir):
    hoje=pd.Timestamp(date.today()); ontem=hoje-pd.Timedelta(days=1)
    result={"lct":{},"all":{}}
    period_ranges={
        "1":  (ontem, ontem),
        "7":  (hoje-pd.Timedelta(days=6), hoje),
        "14": (hoje-pd.Timedelta(days=13), hoje),
        "30": (hoje-pd.Timedelta(days=29), hoje),
        "all": (None, None),
    }
    for key,subset in [("lct",df[df["is_lct"]]),("all",df)]:
        for pname,(start,end) in period_ranges.items():
            p=subset if start is None else subset[(subset["date"]>=start)&(subset["date"]<=end)]
            result[key][pname]=meta_tables_period(df,p,img_dir)
            print(f"     [{key}][{pname}]: {len(result[key][pname]['camps'])} camps | {len(result[key][pname]['ads'])} ads")
    return result

def meta_breakdowns(df):
    print("  Lendo breakdowns...")
    hoje_bd=pd.Timestamp(date.today())
    AGE_ORDER=["18-24","25-34","35-44","45-54","55-64","65+"]
    CONV_COLS_BD=["Action Omni Purchase","Action Omni Add To Cart","Action Omni Initiated Checkout"]

    def seg(agg, dim, metric="purchase"):
        agg=agg[agg["spend"]>0].copy()
        agg["cpv"]=(agg["spend"]/agg[metric]).where(agg[metric]>0).round(2)
        return [{"n":str(r[dim]),"spend":round(float(r["spend"]),2),
                 "pu":int(r.get("purchase",0)),"atc":int(r.get("add_to_cart",0)),
                 "cpv":safe(r["cpv"])} for _,r in agg.iterrows()]

    try:
        df_ga=pd.read_csv(URL_GA)
        df_ga["date"]=pd.to_datetime(df_ga["Date"],errors="coerce")
        df_ga["spend"]=to_num(df_ga["Spend (Cost, Amount Spent)"])
        df_ga["purchase"]=to_num(df_ga["Action Omni Purchase"]) if "Action Omni Purchase" in df_ga.columns else 0
        df_ga["add_to_cart"]=to_num(df_ga["Action Omni Add To Cart"]) if "Action Omni Add To Cart" in df_ga.columns else 0
        df_ga["age"]=df_ga["Age (Breakdown)"].astype(str)
        df_ga["gender"]=df_ga["Gender (Breakdown)"].astype(str)
        if "Campaign Name" in df_ga.columns and LANCAMENTO_COD:
            df_ga["is_lct"]=df_ga["Campaign Name"].str.contains(LANCAMENTO_COD,na=False,case=False)
        else:
            df_ga["is_lct"]=True
        df_ga=df_ga.dropna(subset=["date"])
    except Exception as e: print(f"  Aviso GA: {e}"); df_ga=pd.DataFrame()

    try:
        df_pt=pd.read_csv(URL_PT)
        df_pt["date"]=pd.to_datetime(df_pt["Date"],errors="coerce")
        df_pt["spend"]=to_num(df_pt["Spend (Cost, Amount Spent)"])
        df_pt["purchase"]=to_num(df_pt["Action Omni Purchase"]) if "Action Omni Purchase" in df_pt.columns else 0
        df_pt["add_to_cart"]=to_num(df_pt["Action Omni Add To Cart"]) if "Action Omni Add To Cart" in df_pt.columns else 0
        df_pt["platform"]=df_pt["Platform Position (Breakdown)"].astype(str)
        if "Campaign Name" in df_pt.columns and LANCAMENTO_COD:
            df_pt["is_lct"]=df_pt["Campaign Name"].str.contains(LANCAMENTO_COD,na=False,case=False)
        else:
            df_pt["is_lct"]=True
        df_pt=df_pt.dropna(subset=["date"])
    except Exception as e: print(f"  Aviso PT: {e}"); df_pt=pd.DataFrame()

    result={}
    for pname,n in [("1",1),("7",7),("14",14),("30",30),("all",0)]:
        start=hoje_bd-pd.Timedelta(days=n-1) if n>0 else None
        for lname,lct_filter in [("lct",True),("all",None)]:
            if len(df_ga)>0:
                pga=df_ga if lct_filter is None else df_ga[df_ga["is_lct"]]
                pga=pga[(pga["date"]>=start)&(pga["date"]<=hoje_bd)] if n>0 else pga
            else: pga=df_ga
            if len(df_pt)>0:
                ppt=df_pt if lct_filter is None else df_pt[df_pt["is_lct"]]
                ppt=ppt[(ppt["date"]>=start)&(ppt["date"]<=hoje_bd)] if n>0 else ppt
            else: ppt=df_pt
            age_d=[]; gen_d=[]; plat_d=[]
            if len(pga)>0:
                ag_age=pga[pga["age"].isin(AGE_ORDER)].groupby("age").agg(spend=("spend","sum"),purchase=("purchase","sum"),add_to_cart=("add_to_cart","sum")).reset_index()
                ag_age["_o"]=ag_age["age"].apply(lambda x:AGE_ORDER.index(x) if x in AGE_ORDER else 99)
                age_d=seg(ag_age.sort_values("_o"),"age")
                ag_gen=pga[pga["gender"].isin(["female","male"])].groupby("gender").agg(spend=("spend","sum"),purchase=("purchase","sum"),add_to_cart=("add_to_cart","sum")).reset_index().sort_values("purchase",ascending=False)
                gen_d=seg(ag_gen,"gender")
            if len(ppt)>0:
                ag_pt=ppt.groupby("platform").agg(spend=("spend","sum"),purchase=("purchase","sum"),add_to_cart=("add_to_cart","sum")).reset_index().sort_values("purchase",ascending=False).head(8)
                plat_d=seg(ag_pt,"platform")
            if lname not in result: result[lname]={}
            result[lname][pname]={"age":age_d,"gender":gen_d,"platform":plat_d}

    # Raw para filtros dinâmicos no frontend
    raw_ga=[]
    if len(df_ga)>0:
        for _,r in df_ga.iterrows():
            if pd.isna(r['date']): continue
            raw_ga.append({'d':r['date'].strftime('%d/%m'),'age':str(r['age']),'gen':str(r['gender']),
                           'sp':round(float(r['spend']),2),'pu':int(r['purchase']),'atc':int(r['add_to_cart']),
                           'lct':bool(r['is_lct']),'camp':str(r['Campaign Name']) if 'Campaign Name' in r.index else ''})
    raw_pt=[]
    if len(df_pt)>0:
        for _,r in df_pt.iterrows():
            if pd.isna(r['date']): continue
            raw_pt.append({'d':r['date'].strftime('%d/%m'),'plat':str(r['platform']),
                           'sp':round(float(r['spend']),2),'pu':int(r['purchase']),'atc':int(r['add_to_cart']),
                           'lct':bool(r['is_lct']),'camp':str(r['Campaign Name']) if 'Campaign Name' in r.index else ''})
    result['_raw_ga']=raw_ga; result['_raw_pt']=raw_pt
    return result

def meta_monthly(df):
    PT_MONTHS={"Jan":"Jan","Feb":"Fev","Mar":"Mar","Apr":"Abr","May":"Mai",
                "Jun":"Jun","Jul":"Jul","Aug":"Ago","Sep":"Set","Oct":"Out","Nov":"Nov","Dec":"Dez"}
    df=df.copy(); df["ym"]=df["date"].dt.to_period("M")
    months=sorted(df["ym"].unique())
    out={"lbl":[],"totalS":[],"totalP":[],"cpvG":[],"cpmG":[],"ctrG":[],"camps":[]}
    for m in months:
        p=df[df["ym"]==m]
        sp=round(float(p["spend"].sum()),2); pu=int(p["purchase"].sum())
        imp=float(p["impressions"].sum()); lc=float(p["link_clicks"].sum())
        raw_lbl=pd.Period(m,"M").strftime("%b/%y")
        pt_lbl=PT_MONTHS.get(raw_lbl[:3],raw_lbl[:3])+raw_lbl[3:]
        out["lbl"].append(pt_lbl); out["totalS"].append(sp); out["totalP"].append(pu)
        out["cpvG"].append(round(sp/pu,2) if pu>0 else None)
        out["cpmG"].append(round(sp/imp*1000,2) if imp>0 else None)
        out["ctrG"].append(round(lc/imp*100,2) if imp>0 else None)
        ag=p.groupby("campaign").agg(spend=("spend","sum"),purchase=("purchase","sum"),
            impressions=("impressions","sum"),link_clicks=("link_clicks","sum"),
            add_to_cart=("add_to_cart","sum")).reset_index()
        for _,r in ag.iterrows():
            out["camps"].append({"n":str(r["campaign"]),"spend":round(float(r["spend"]),2),
                "purchase":int(r["purchase"]),"imp":int(r["impressions"]),
                "lc":int(r["link_clicks"]),"atc":int(r["add_to_cart"])})
    print(f"     Meta Mensal: {len(months)} meses")
    return out

# ══ INJEÇÃO ════════════════════════════════════════════
def replace_js_const(html, name, value):
    replacement = f"const {name} = {json.dumps(value, ensure_ascii=False)};"
    pattern_start = re.compile(rf"const {name}\s*=\s*")
    m = pattern_start.search(html)
    if not m:
        print(f"  AVISO: não encontrou const {name}")
        return html
    start = m.start(); val_start = m.end()
    i = val_start; depth = 0; in_str = False; str_char = None
    while i < len(html):
        ch = html[i]
        if in_str:
            if ch == '\\': i += 2; continue
            if ch == str_char: in_str = False
        else:
            if ch in ('"', "'", '`'): in_str = True; str_char = ch
            elif ch in ('{', '['): depth += 1
            elif ch in ('}', ']'): depth -= 1
            elif ch == ';' and depth == 0: break
        i += 1
    end = i + 1
    html = html[:start] + replacement + html[end:]
    return html

def inject_all(tpl, meta_k, meta_d, meta_dc, meta_raw_c, meta_t, meta_bd, meta_month):
    html=Path(tpl).read_text(encoding="utf-8")
    html=replace_js_const(html,"META_KPIS",      meta_k)
    html=replace_js_const(html,"META_DAILY",      meta_d)
    html=replace_js_const(html,"META_DAILY_CAMPS",meta_dc)
    html=replace_js_const(html,"META_RAW_CAMP",   meta_raw_c)
    html=replace_js_const(html,"META_TABLES",     meta_t)
    html=replace_js_const(html,"META_BD",         meta_bd)
    html=replace_js_const(html,"META_MONTHLY",    meta_month)
    html=replace_js_const(html,"DATA_GERACAO",    date.today().strftime("%Y-%m-%d"))
    for k,v in [
        ("NOME_CLIENTE", f"'{NOME_CLIENTE}'"),
        ("LOGO_LETRA",   f"'{LOGO_LETRA}'"),
        ("COR_ACENTO",   f"'{COR_ACENTO}'"),
        ("LANCAMENTO_COD",f"'{LANCAMENTO_COD}'"),
        ("CPV_BOM",  str(CPV_BOM)),  ("CPV_MEDIO",  str(CPV_MEDIO)),
        ("CTR_BOM",  str(CTR_BOM)),  ("CTR_MEDIO",  str(CTR_MEDIO)),
        ("CPM_BOM",  str(CPM_BOM)),  ("CPM_MEDIO",  str(CPM_MEDIO)),
        ("CR_BOM",   str(CR_BOM)),   ("CR_MEDIO",   str(CR_MEDIO)),
        ("VC_BOM",   str(VC_BOM)),   ("VC_MEDIO",   str(VC_MEDIO)),
        ("ATC_BOM",  str(ATC_BOM)),  ("ATC_MEDIO",  str(ATC_MEDIO)),
        ("IC_BOM",   str(IC_BOM)),   ("IC_MEDIO",   str(IC_MEDIO)),
        ("PURCH_BOM",str(PURCH_BOM)),("PURCH_MEDIO",str(PURCH_MEDIO)),
    ]:
        html=re.sub(rf"const {k}\s*=\s*[^;]+;",f"const {k}={v};",html,count=1)
    html=re.sub(r"\d{2}/\d{2}/\d{4} · via planilha",date.today().strftime("%d/%m/%Y")+" · via planilha",html)
    return html

# ══ MAIN ═══════════════════════════════════════════════
def main():
    print("="*60)
    print(f"Dashboard E-commerce — {NOME_CLIENTE}")
    print("="*60)
    img_dir=Path("imgs"); img_dir.mkdir(exist_ok=True)

    print("\n[META ADS]")
    df_meta=load_meta()
    m_k=meta_kpis(df_meta)
    m_d=meta_daily(df_meta)
    m_dc=meta_daily_camps(df_meta)
    m_raw=meta_raw(df_meta)
    m_t=meta_tables(df_meta,img_dir)
    m_bd=meta_breakdowns(df_meta)
    m_month=meta_monthly(df_meta)

    total_pu=m_k["lct"]["purchase"] if LANCAMENTO_COD else m_k["all"]["purchase"]
    total_sp=m_k["lct"]["spend"]    if LANCAMENTO_COD else m_k["all"]["spend"]
    print(f"  ✓ {total_pu} compras | R$ {total_sp:,.2f} invest.")

    print("\n[HTML]")
    if not Path(TEMPLATE_FILE).exists():
        print(f"  ERRO: {TEMPLATE_FILE} não encontrado"); return
    html=inject_all(TEMPLATE_FILE,m_k,m_d,m_dc,m_raw,m_t,m_bd,m_month)
    Path(OUTPUT_FILE).write_text(html,encoding="utf-8")
    print(f"  ✓ {OUTPUT_FILE} ({len(html)//1024}KB)")

    data_json={"cliente":NOME_CLIENTE,"cor":COR_ACENTO,"letra":LOGO_LETRA,
               "lancamento":LANCAMENTO_COD,"atualizado":date.today().strftime("%d/%m/%Y"),
               "kpis":{"spend":total_sp,"purchase":total_pu,
                       "cpv":m_k["lct"].get("cpv") if LANCAMENTO_COD else m_k["all"].get("cpv")}}
    Path("data.json").write_text(json.dumps(data_json,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"  ✓ data.json\n{'='*60}")

if __name__=="__main__":
    main()
