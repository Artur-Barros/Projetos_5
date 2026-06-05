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
    if not text:
        return 0.0
    text = text.replace("R$", "").replace("\xa0", "").strip()
    text = re.sub(r"[^\d.,]", "", text)
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


_CATEGORIA_MAP = {
    "Informática": [
        "notebook", "laptop", "computador", "desktop", "processador",
        "placa de video", "placa mãe", "placa-mae", "memoria", "memória", "ssd", "hdd",
        "nvme", "fonte atx", "gabinete", "cooler", "monitor", "teclado", "headset",
        "webcam", "impressora", "scanner", "roteador", "switch de rede", "nobreak",
        "servidor", "server", "periférico", "periferico", "informatica", "informática",
        "hardware", "componente", "mesa digitalizadora", "computação", "computacao",
    ],
    "Eletrônicos": [
        "televisor", "televisão", "televisao", "áudio", "audio", "caixa de som",
        "headphone", "projetor", "blu-ray", "câmera", "camera", "fotografica",
        "fotográfica", "drone", "filmadora", "eletronico", "eletrônico",
        "eletronicos", "eletrônicos", "home theater",
    ],
    "Celulares & Tablets": [
        "smartphone", "celular", "iphone", "android", "tablet", "ipad",
        "smartwatch", "wearable",
    ],
    "Eletrodomésticos": [
        "geladeira", "refrigerador", "fogão", "fogao", "microondas", "lavadora",
        "secadora", "aspirador", "ventilador", "ar condicionado", "ar-condicionado",
        "purificador", "batedeira", "liquidificador", "cafeteira", "forno eletrico",
        "churrasqueira eletrica", "eletrodomestico", "eletrodoméstico",
        "eletrodomesticos", "eletrodomésticos",
    ],
    "Móveis & Decoração": [
        "móveis", "moveis", "móvel", "movel", "sofá", "sofa", "poltrona",
        "rack", "estante", "criado-mudo", "criado mudo", "buffet", "aparador",
        "cômoda", "comoda", "cabeceira", "painel de tv", "tapete",
        "cortina", "luminária", "luminaria", "decoração", "decoracao",
        "colchão", "colchao", "armário", "armario", "prateleira",
    ],
    "Roupas & Moda": [
        "camisa", "camiseta", "calça", "calca", "shorts", "vestido", "bermuda",
        "sapato", "tênis", "tenis", "bota", "sandália", "sandalia", "chinelo",
        "bolsa feminina", "mochila escolar", "jaqueta", "casaco", "blusa",
        "moda feminina", "moda masculina", "vestuário", "vestuario",
        "calçado", "calcado", "lingerie", "meia", "cueca", "sutiã", "sutia",
    ],
    "Games": [
        "videogame", "playstation", "xbox", "nintendo", "console",
        "jogo para", "jogos para", "game pass", "steam deck",
    ],
}

_REGEX_PRIORIDADE = [
    ("Móveis & Decoração", [
        r"guarda[\s-]?roupas?",
        r"roupeiro",
        r"criado[\s-]?mudo",
        r"\bsof[aá]\b",
        r"\bcolch[aã]o\b",
        r"\bestante\b",
        r"\bpoltrona\b",
        r"\bcomoda\b",
        r"\bc[oô]moda\b",
        r"\bbuffet\b",
        r"\baparador\b",
        r"\bmesa\s+de\s+jantar\b",
        r"\bmesa\s+de\s+centro\b",
        r"\bmesa\s+redonda\b",
        r"\bmesa\s+quadrada\b",
    ]),
    ("Informática", [
        r"\bmesa\s+gamer\b",
        r"\bmesa\s+escrit[oó]rio\b",
        r"\bcadeira\s+gamer\b",
        r"\bcadeira\s+de\s+escrit[oó]rio\b",
        r"\bcadeira\s+escrit[oó]rio\b",
        r"mouse[\s-]?pad",
        r"mousepad",
        r"\bmouse\b",
        r"\bnotebook\b",
        r"\bteclado\b",
        r"\bmonitor\b",
        r"\bssd\b",
        r"\bgabinete\b",
        r"\bplaca\s+de\s+video\b",
        r"\bplaca\s+m[aã]e\b",
        r"\bprocessador\b",
        r"\bmem[oó]ria\b",
        r"\bheadset\b",
        r"\bwebcam\b",
        r"\bnobreak\b",
        r"mesa\s+digitalizadora",
    ]),
    ("Roupas & Moda", [
        r"\bcamiseta\b",
        r"\bcamisa\b",
        r"\bcal[cç]a\b",
        r"\bvestido\b",
        r"\bbermuda\b",
        r"\bjaqueta\b",
        r"\bcasaco\b",
        r"\bblusa\b",
        r"\bshorts\b",
        r"\btenis\b",
        r"\bt[eê]nis\b",
        r"\bsapato\b",
        r"\bbota\b",
        r"\bchinelo\b",
        r"\blingerie\b",
        r"\bmoda\b",
        r"\bbody\b",
        r"\bbon[eé]\b",
        r"\bbolsa\b",
        r"\bmochila\b",
        r"\bmacac[aã]o\b",
        r"\bsaia\b",
        r"\bmoda\s+(feminina|masculina|infantil)\b",
        r"\bvestu[aá]rio\b",
        r"\bfashion\b",
    ]),
    ("Games", [
        r"\bplaystation\b",
        r"\bxbox\b",
        r"\bnintendo\b",
        r"\bvideogame\b",
        r"\bconsole\b",
        r"\bgame\s+pass\b",
    ]),
    ("Celulares & Tablets", [
        r"\bsmartphone\b",
        r"\bcelular\b",
        r"\biphone\b",
        r"\btablet\b",
        r"\bipad\b",
        r"\bsmartwatch\b",
    ]),
    ("Eletrodomésticos", [
        r"\bgeladeira\b",
        r"\bmicroondas\b",
        r"\blavadora\b",
        r"\bsecadora\b",
        r"\bar[\s-]?condicionado\b",
    ]),
    ("Eletrônicos", [
        r"\btelevis(o|ão|ao)\b",
        r"\btv\b",
        r"\bhome\s+theater\b",
        r"\bcaixa\s+de\s+som\b",
    ]),
]

_PALAVRAS_CURTAS = frozenset({
    "tv", "pc", "ssd", "hdd", "nvme", "hub", "dvd", "ipad",
})


def _texto_classificacao(produto: str, categoria_bruta: str) -> str:
    partes = [categoria_bruta or "", produto or ""]
    texto = " ".join(partes).lower()
    return re.sub(r"\s+", " ", texto).strip()


def _keyword_casa(texto: str, kw: str) -> bool:
    if " " in kw or "-" in kw:
        return kw in texto
    if kw in _PALAVRAS_CURTAS:
        return re.search(rf"\b{re.escape(kw)}\b", texto) is not None
    return re.search(rf"\b{re.escape(kw)}\b", texto) is not None


def classificar_produto(produto: str = "", categoria_bruta: str = "") -> str:
    texto = _texto_classificacao(produto, categoria_bruta)
    if not texto:
        return "Outros"

    for categoria, padroes in _REGEX_PRIORIDADE:
        for padrao in padroes:
            if re.search(padrao, texto, re.IGNORECASE):
                return categoria

    for categoria_ampla, keywords in _CATEGORIA_MAP.items():
        for kw in sorted(keywords, key=len, reverse=True):
            if _keyword_casa(texto, kw):
                return categoria_ampla

    return "Outros"


def _normalizar_categoria(categoria_bruta: str, produto: str = "") -> str:
    return classificar_produto(produto, categoria_bruta)


def _normalizar_loja(nome: str) -> str:
    if not nome:
        return nome
    chave = re.sub(r"[^a-z0-9]", "", nome.lower())
    if chave in {"kabum", "kabumbr"}:
        return "Kabum"
    return nome.strip()


def _kabum_avaliacao_produto(code) -> tuple:
    cache_key = ("kabum", str(code))
    if cache_key in _AVALIACAO_CACHE:
        return _AVALIACAO_CACHE[cache_key]

    try:
        url = f"https://www.kabum.com.br/produto/{code}"
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        script = BeautifulSoup(resp.text, "html.parser").find("script", {"id": "__NEXT_DATA__"})
        if not script:
            result = (None, 0)
        else:
            rating = (
                json.loads(script.string)
                .get("props", {})
                .get("pageProps", {})
                .get("product", {})
                .get("rating")
                or {}
            )
            score = rating.get("score")
            count = int(rating.get("count") or 0)
            if count <= 0 or score is None:
                result = (None, 0)
            else:
                result = (float(score), count)
    except Exception:
        result = (None, 0)

    _AVALIACAO_CACHE[cache_key] = result
    return result


def _avaliacao_kabum(produto: dict) -> tuple:
    count = int(produto.get("ratingCount") or 0)
    score = produto.get("rating")
    if count > 0 and score is not None:
        return float(score), count
    code = produto.get("code")
    if code:
        return _kabum_avaliacao_produto(code)
    return None, 0


def _montar_resultado(produto, preco, loja, categoria, link, avaliacao=None, qtd_avaliacoes=0):
    score, count = _validar_avaliacao(avaliacao, qtd_avaliacoes)
    return {
        "Produto": produto,
        "Preço (R$)": float(preco),
        "Loja": _normalizar_loja(loja),
        "Categoria": categoria,
        "Link": link,
        "Avaliação": score,
        "Qtd. avaliações": count,
    }


_AVALIACAO_CACHE = {}
_MAX_ENRIQUECIMENTO = 20


def _limpar_cache_avaliacao():
    _AVALIACAO_CACHE.clear()


def _validar_avaliacao(score, count=0):
    if score is None:
        return None, 0
    try:
        score = float(score)
    except (TypeError, ValueError):
        return None, 0
    if score <= 0:
        return None, 0
    return score, int(count or 0)


def _codigo_kabum_link(link):
    match = re.search(r"kabum\.com\.br/produto/(\d+)", link or "", re.I)
    return match.group(1) if match else None


def _zoom_avaliacao_produto(url_ou_path):
    if not url_ou_path:
        return None, 0
    cache_key = ("zoom", url_ou_path)
    if cache_key in _AVALIACAO_CACHE:
        return _AVALIACAO_CACHE[cache_key]

    try:
        url = url_ou_path if str(url_ou_path).startswith("http") else f"https://www.zoom.com.br{url_ou_path}"
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        script = BeautifulSoup(resp.text, "html.parser").find("script", {"id": "__NEXT_DATA__"})
        if not script:
            result = (None, 0)
        else:
            products = (
                json.loads(script.string)
                .get("props", {})
                .get("initialReduxState", {})
                .get("products")
                or {}
            )
            result = (None, 0)
            if isinstance(products, dict):
                for val in products.values():
                    if not isinstance(val, dict):
                        continue
                    prod = val.get("product") or {}
                    if not isinstance(prod, dict):
                        continue
                    score, count = _validar_avaliacao(
                        prod.get("rating"),
                        val.get("countOfComments") or prod.get("countOfComments"),
                    )
                    if score is not None:
                        result = (score, count)
                        break
    except Exception:
        result = (None, 0)

    _AVALIACAO_CACHE[cache_key] = result
    return result


def _avaliacao_zoom(hit):
    return _validar_avaliacao(hit.get("rating"), hit.get("countOfComments"))


def _avaliacao_terabyte_card(card):
    img = card.select_one(".ratings img[alt]")
    if not img:
        return None, 0
    match = re.match(r"(\d)_(\d)", img.get("alt", ""))
    if not match:
        return None, 0
    score = float(f"{match.group(1)}.{match.group(2)}")
    count = 0
    for span in card.select(".ratings span"):
        cm = re.search(r"\((\d+)\)", span.get_text(strip=True))
        if cm:
            count = int(cm.group(1))
            break
    return _validar_avaliacao(score, count)


def _tokens_produto(nome):
    stop = {"de", "da", "do", "com", "para", "em", "e", "o", "a", "os", "as", "por"}
    return {
        w for w in re.findall(r"\w{3,}", (nome or "").lower())
        if w not in stop
    }


def _similaridade_produto(nome_a, nome_b):
    ta, tb = _tokens_produto(nome_a), _tokens_produto(nome_b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _aplicar_avaliacao(item, score, count):
    score, count = _validar_avaliacao(score, count)
    if score is None:
        return
    item["Avaliação"] = score
    item["Qtd. avaliações"] = count


def _propagar_avaliacoes(resultados):
    com_avaliacao = [
        item for item in resultados
        if item.get("Avaliação") is not None
    ]
    if not com_avaliacao:
        return resultados

    for item in resultados:
        if item.get("Avaliação") is not None:
            continue
        melhor_score = None
        melhor_count = 0
        melhor_sim = 0.0
        for ref in com_avaliacao:
            sim = _similaridade_produto(item.get("Produto", ""), ref.get("Produto", ""))
            if sim >= 0.55 and sim > melhor_sim:
                melhor_sim = sim
                melhor_score = ref["Avaliação"]
                melhor_count = ref["Qtd. avaliações"]
        if melhor_score is not None:
            _aplicar_avaliacao(item, melhor_score, melhor_count)
    return resultados


def _enriquecer_avaliacoes(resultados):
    resultados = _propagar_avaliacoes(resultados)
    requisicoes = 0

    for item in resultados:
        if item.get("Avaliação") is not None:
            continue
        if requisicoes >= _MAX_ENRIQUECIMENTO:
            break

        link = item.get("Link") or ""
        score, count = None, 0

        if "zoom.com.br" in link:
            score, count = _zoom_avaliacao_produto(link)
            requisicoes += 1
        elif code := _codigo_kabum_link(link):
            score, count = _kabum_avaliacao_produto(code)
            requisicoes += 1

        _aplicar_avaliacao(item, score, count)

    return _propagar_avaliacoes(resultados)


def search_kabum(query, limit=5):
    url = f"https://www.kabum.com.br/busca/{urllib.parse.quote(query)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script:
            return []

        outer = json.loads(script.string)
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

            avaliacao, qtd_avaliacoes = _avaliacao_kabum(p)

            results.append(_montar_resultado(
                produto=p.get("name", ""),
                preco=price,
                loja="Kabum",
                categoria=classificar_produto(p.get("name", ""), raw_cat),
                link=f"https://www.kabum.com.br/produto/{p.get('code', '')}",
                avaliacao=avaliacao,
                qtd_avaliacoes=qtd_avaliacoes,
            ))
        return results
    except Exception:
        return []


def search_terabyte(query, limit=5):
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

                raw_cat = ""
                try:
                    from urllib.parse import urlparse
                    partes = urlparse(link).path.strip("/").split("/")
                    if len(partes) >= 2 and partes[0] == "produto":
                        raw_cat = partes[1].replace("-", " ")
                except Exception:
                    pass

                avaliacao, qtd_avaliacoes = _avaliacao_terabyte_card(card)

                results.append(_montar_resultado(
                    produto=name,
                    preco=price,
                    loja="Terabyte",
                    categoria=classificar_produto(name, raw_cat),
                    link=link,
                    avaliacao=avaliacao,
                    qtd_avaliacoes=qtd_avaliacoes,
                ))
            except (ValueError, AttributeError):
                continue
        return results
    except Exception:
        return []


def search_zoom(query, limit=5):
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

                raw_cat = ""
                cat_path = h.get("categoryPath") or h.get("category") or ""
                if isinstance(cat_path, str) and cat_path:
                    raw_cat = cat_path
                elif isinstance(cat_path, list) and cat_path:
                    raw_cat = " ".join(str(c) for c in cat_path)
                else:
                    breadcrumbs = h.get("breadcrumbs") or []
                    if breadcrumbs:
                        raw_cat = " ".join(b.get("name", "") for b in breadcrumbs if b.get("name"))

                avaliacao, qtd_avaliacoes = _avaliacao_zoom(h)

                results.append(_montar_resultado(
                    produto=name,
                    preco=price,
                    loja=merchant,
                    categoria=classificar_produto(name, raw_cat),
                    link=link,
                    avaliacao=avaliacao,
                    qtd_avaliacoes=qtd_avaliacoes,
                ))
            except (ValueError, TypeError):
                continue
        return results
    except Exception:
        return []


_CATEGORIA_BUSCA = {
    "Roupas & Moda": {
        "queries": ["camiseta", "calça", "tênis", "vestido", "blusa", "moda feminina"],
        "apenas_zoom": True,
        "limite_por_query": 20,
    },
    "Móveis & Decoração": {
        "queries": ["sofá", "guarda-roupa", "estante", "mesa de jantar", "rack móvel"],
        "apenas_zoom": True,
        "limite_por_query": 20,
    },
}


def _dedupe_resultados(resultados):
    vistos = set()
    unicos = []
    for item in resultados:
        chave = (item.get("Link") or item.get("Produto", ""), item.get("Loja", ""))
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(item)
    return _enriquecer_avaliacoes(unicos)


def search_for_category(categoria: str, limit_por_query=None):
    cfg = _CATEGORIA_BUSCA.get(categoria)
    if not cfg:
        return search_all(categoria, limit=10)

    limite = limit_por_query or cfg.get("limite_por_query", 20)
    acumulado = []
    for termo in cfg["queries"]:
        try:
            if cfg.get("apenas_zoom"):
                acumulado.extend(search_zoom(termo, limite))
            else:
                acumulado.extend(search_all(termo, limit=limite))
        except Exception:
            pass
    return _dedupe_resultados(acumulado)


def search_for_categories(categorias: list[str]):
    _limpar_cache_avaliacao()
    acumulado = []
    for cat in categorias:
        acumulado.extend(search_for_category(cat))
    return _dedupe_resultados(acumulado)


def search_all(query, limit=10):
    _limpar_cache_avaliacao()
    all_results = []
    sources = [search_zoom, search_kabum, search_terabyte]
    for func in sources:
        try:
            current_limit = limit * 2 if func == search_zoom else limit
            all_results.extend(func(query, current_limit))
        except Exception:
            pass
    return _dedupe_resultados(all_results)