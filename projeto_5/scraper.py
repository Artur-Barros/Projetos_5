"""
Módulo de scraping para coleta de preços em lojas online.
Fontes: Kabum, Terabyte e Zoom (agregador de lojas como Amazon, Magalu, etc).
"""
import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _parse_price_br(text):
    """Converte texto de preço brasileiro (R$ 1.234,56) para float."""
    if not text:
        return 0.0
    text = text.replace("R$", "").replace("\xa0", "").strip()
    text = re.sub(r"[^\d.,]", "", text)
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


# ── Mapeamento de categorias brutas → categorias amplas ──────────────────────
# As chaves são as categorias amplas exibidas ao usuário.
# Os valores são listas de substrings buscadas na categoria bruta scraped.
_CATEGORIA_MAP = {
    "Informática": [
        "notebook", "laptop", "computador", "desktop", "pc", "processador",
        "placa", "memoria", "memória", "ssd", "hdd", "nvme", "fonte", "gabinete",
        "cooler", "monitor", "teclado", "mouse", "headset", "webcam", "impressora",
        "scanner", "roteador", "switch", "rede", "cabo", "hub", "nobreak",
        "servidor", "server", "periférico", "periferico", "informatica", "informática",
        "hardware", "componente",
    ],
    "Eletrônicos": [
        "tv", "televisor", "televisão", "audio", "áudio", "som", "caixa de som",
        "fone", "headphone", "projetor", "dvd", "blu-ray", "camera", "câmera",
        "fotografica", "fotográfica", "drone", "filmadora", "eletronico", "eletrônico",
        "eletronicos", "eletrônicos", "home theater",
    ],
    "Celulares & Tablets": [
        "smartphone", "celular", "iphone", "android", "tablet", "ipad",
        "smartwatch", "wearable", "watch",
    ],
    "Eletrodomésticos": [
        "geladeira", "refrigerador", "fogao", "fogão", "microondas", "lavadora",
        "lavar", "secadora", "aspirador", "ventilador", "ar condicionado", "ar-condicionado",
        "purificador", "batedeira", "liquidificador", "cafeteira", "forno",
        "churrasqueira", "eletrodomestico", "eletrodoméstico", "eletrodomesticos",
        "eletrodomésticos", "cozinha", "utilidade",
    ],
    "Móveis & Decoração": [
        "guarda-roupa", "guarda roupa", "roupeiro",
        "movel", "móvel", "moveis", "móveis", "sofa", "sofá", "mesa", "cadeira",
        "cama", "armario", "armário", "estante", "prateleira", "tapete",
        "cortina", "luminaria", "luminária", "decoracao", "decoração", "colchao",
        "colchão",
    ],
    "Roupas & Moda": [
        "roupas", "camisa", "camiseta", "calca", "calça", "shorts", "vestido",
        "sapato", "tenis", "tênis", "bota", "bolsa", "mochila", "carteira",
        "oculos", "óculos", "relogio", "relógio", "joia", "joias", "jóias",
        "moda", "vestuario", "vestuário", "calcado", "calçado",
    ],
    "Games": [
        "game", "jogo", "console", "playstation", "xbox", "nintendo",
        "controle", "games", "gamer",
    ],
}


def _normalizar_categoria(categoria_bruta: str) -> str:
    """
    Normaliza uma categoria bruta (URL slug, label JSON, path hierárquico)
    para uma das categorias amplas definidas em _CATEGORIA_MAP.
    Retorna 'Outros' se nenhum mapeamento for encontrado.
    """
    if not categoria_bruta:
        return "Outros"
    texto = categoria_bruta.lower()
    for categoria_ampla, keywords in _CATEGORIA_MAP.items():
        for kw in keywords:
            if kw in texto:
                return categoria_ampla
    return "Outros"


def search_kabum(query, limit=5):
    """Busca produtos no Kabum extraindo dados do __NEXT_DATA__."""
    url = f"https://www.kabum.com.br/busca/{urllib.parse.quote(query)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script:
            return []

        outer = json.loads(script.string)
        # Handle cases where data might be nested differently or is a string
        page_props = outer.get("props", {}).get("pageProps", {})
        data_raw = page_props.get("data")
        
        if isinstance(data_raw, str):
            inner = json.loads(data_raw)
        else:
            inner = data_raw

        products = inner.get("catalogServer", {}).get("data", [])

        results = []
        for p in products[:limit]:
            price = p.get("priceWithDiscount", p.get("price", 0))
            if not price or price <= 0:
                continue

            # Extrai categoria bruta do JSON do Kabum e normaliza
            category_obj = p.get("category") or {}
            if isinstance(category_obj, dict):
                raw_cat = category_obj.get("name") or category_obj.get("friendlyName") or ""
            else:
                raw_cat = str(category_obj)
            if not raw_cat:
                raw_cat = (
                    p.get("categoryName")
                    or p.get("departmentFriendlyName")
                    or p.get("sectionName")
                    or ""
                )

            results.append({
                "Produto": p.get("name", ""),
                "Preço (R$)": float(price),
                "Loja": "Kabum",
                "Categoria": _normalizar_categoria(raw_cat),
                "Link": f"https://www.kabum.com.br/produto/{p.get('code', '')}",
            })
        return results
    except Exception:
        return []


def search_terabyte(query, limit=5):
    """Busca produtos na Terabyte Shop via scraping HTML."""
    url = f"https://www.terabyteshop.com.br/busca?str={urllib.parse.quote(query)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(".product-item")

        results = []
        for card in cards[:limit]:
            try:
                name_el = card.select_one("a.product-item__name h2")
                price_el = card.select_one(".product-item__new-price")
                link_el = card.select_one("a.product-item__name")

                if not name_el or not price_el:
                    continue

                name = name_el.get_text(strip=True)
                price_text = price_el.get_text(strip=True).split("à")[0].split("À")[0]
                price = _parse_price_br(price_text)
                link = link_el["href"] if link_el else ""
                if link and not link.startswith("http"):
                    link = "https://www.terabyteshop.com.br" + link

                # Extrai categoria bruta da URL do produto e normaliza
                # Formato típico: /produto/<categoria-slug>/<nome>
                raw_cat = ""
                try:
                    from urllib.parse import urlparse
                    partes = urlparse(link).path.strip("/").split("/")
                    if len(partes) >= 2 and partes[0] == "produto":
                        raw_cat = partes[1].replace("-", " ")
                except Exception:
                    pass

                results.append({
                    "Produto": name,
                    "Preço (R$)": price,
                    "Loja": "Terabyte",
                    "Categoria": _normalizar_categoria(raw_cat),
                    "Link": link,
                })
            except (ValueError, AttributeError):
                continue
        return results
    except Exception:
        return []


def search_zoom(query, limit=5):
    """Busca produtos no Zoom (agregador de Amazon, Magalu, etc) via __NEXT_DATA__."""
    url = f"https://www.zoom.com.br/search?q={urllib.parse.quote(query)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script:
            return []

        data = json.loads(script.string)
        hits = data.get("props", {}).get("initialReduxState", {}).get("hits", {}).get("hits", [])

        results = []
        for h in hits[:limit]:
            try:
                name = h.get("name")
                price = h.get("price")
                merchant = h.get("bestOffer", {}).get("merchantName", "Zoom")
                link = h.get("url", "")
                if link and not link.startswith("http"):
                    link = "https://www.zoom.com.br" + link

                if not name or not price:
                    continue

                # Extrai categoria bruta do JSON do Zoom e normaliza
                raw_cat = ""
                cat_path = h.get("categoryPath") or h.get("category") or ""
                if isinstance(cat_path, str) and cat_path:
                    # "Informatica > Componentes > Processadores" → concatena tudo para o mapeamento
                    raw_cat = cat_path
                elif isinstance(cat_path, list) and cat_path:
                    raw_cat = " ".join(str(c) for c in cat_path)
                else:
                    breadcrumbs = h.get("breadcrumbs") or []
                    if breadcrumbs:
                        raw_cat = " ".join(b.get("name", "") for b in breadcrumbs if b.get("name"))

                results.append({
                    "Produto": name,
                    "Preço (R$)": float(price),
                    "Loja": merchant,
                    "Categoria": _normalizar_categoria(raw_cat),
                    "Link": link,
                })
            except (ValueError, TypeError):
                continue
        return results
    except Exception:
        return []


def search_all(query, limit=10):
    """Busca em todas as fontes disponíveis e retorna lista agregada."""
    all_results = []
    # Usando Zoom primeiro pois agrega muitas lojas, depois Kabum e Terabyte para cobertura tech
    sources = [search_zoom, search_kabum, search_terabyte]
    for func in sources:
        try:
            # Aumentando um pouco o limite individual para o agregador
            current_limit = limit * 2 if func == search_zoom else limit
            all_results.extend(func(query, current_limit))
        except Exception:
            pass
    return all_results