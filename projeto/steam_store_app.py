from urllib.parse import urljoin

import requests
import streamlit as st
from bs4 import BeautifulSoup

STEAM_SEARCH_URL = "https://store.steampowered.com/search/results/"
STEAM_DETAILS_URL = "https://store.steampowered.com/api/appdetails/"
TAMANHO_PAGINA = 20
PAISES = {
    "Brasil (BRL)": ("br", "brazilian"),
    "Estados Unidos (USD)": ("us", "english"),
    "Portugal (EUR)": ("pt", "portuguese"),
}
PLATAFORMAS = {
    "win": "Windows",
    "mac": "macOS",
    "linux": "Linux",
}

st.set_page_config(
    page_title="Loja Steam - Busca de jogos",
    page_icon="🎮",
    layout="wide",
)


def obter_json(url, parametros):
    try:
        resposta = requests.get(
            url,
            params=parametros,
            timeout=25,
            headers={"User-Agent": "Mozilla/5.0 SteamStoreGameSearch/1.0"},
        )
    except requests.Timeout as exc:
        raise RuntimeError("A loja Steam demorou demais para responder.") from exc
    except requests.RequestException as exc:
        raise RuntimeError("Não foi possível conectar à loja Steam.") from exc

    if not resposta.ok:
        raise RuntimeError(f"A loja Steam respondeu com HTTP {resposta.status_code}.")

    try:
        return resposta.json()
    except ValueError as exc:
        raise RuntimeError("A loja Steam retornou uma resposta inválida.") from exc


def interpretar_resultados(html):
    sopa = BeautifulSoup(html, "html.parser")
    jogos = []
    ids_encontrados = set()

    for linha in sopa.select("a.search_result_row"):
        app_id = linha.get("data-ds-appid", "").split(",")[0].strip()
        titulo = linha.select_one(".title")
        if not app_id.isdigit() or titulo is None or app_id in ids_encontrados:
            continue

        ids_encontrados.add(app_id)
        imagem = linha.select_one(".search_capsule img")
        lancamento = linha.select_one(".search_released")
        plataformas = {
            nome
            for elemento in linha.select(".search_platforms .platform_img")
            for classe, nome in PLATAFORMAS.items()
            if classe in elemento.get("class", [])
        }
        jogos.append(
            {
                "id": int(app_id),
                "name": titulo.get_text(" ", strip=True),
                "image": imagem.get("src") if imagem else None,
                "release": lancamento.get_text(" ", strip=True) if lancamento else None,
                "platforms": sorted(plataformas),
                "url": urljoin("https://store.steampowered.com/", f"app/{app_id}/"),
            }
        )
    return jogos


@st.cache_data(ttl=900, show_spinner=False)
def pesquisar_jogos(termo, inicio, pais, idioma):
    parametros = {
        "query": termo,
        "term": termo,
        "start": inicio,
        "count": TAMANHO_PAGINA,
        "cc": pais,
        "l": idioma,
        "json": 1,
        "infinite": 1,
    }
    dados = obter_json(STEAM_SEARCH_URL, parametros)
    if not isinstance(dados, dict) or not dados.get("success"):
        raise RuntimeError("A busca da Steam não conseguiu retornar resultados.")
    try:
        total = int(dados.get("total_count", 0))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("A Steam retornou uma quantidade de resultados inválida.") from exc
    return {"total": total, "results": interpretar_resultados(dados.get("results_html", ""))}


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_detalhes_jogo(app_id, pais, idioma):
    resposta = obter_json(
        STEAM_DETAILS_URL,
        {"appids": app_id, "cc": pais, "l": idioma},
    )
    item = resposta.get(str(app_id), {}) if isinstance(resposta, dict) else {}
    if not item.get("success") or not isinstance(item.get("data"), dict):
        raise RuntimeError("Os detalhes deste jogo não estão disponíveis na Steam.")
    return item["data"]


def formatar_preco(detalhe):
    preco = detalhe.get("price_overview")
    if isinstance(preco, dict) and preco.get("final_formatted"):
        return preco["final_formatted"]
    if detalhe.get("is_free"):
        return "Gratuito"
    return "Preço não informado"


st.title("🎮 Busca de jogos na Steam")
st.write(
    "Pesquise jogos no catálogo da loja oficial Steam, consulte detalhes e abra a página de cada jogo."
)
st.markdown("Dados e links fornecidos pela [Steam](https://store.steampowered.com/).")

with st.sidebar:
    st.header("Preferências")
    pais_selecionado = st.selectbox("Região e moeda", options=list(PAISES))
    pais, idioma = PAISES[pais_selecionado]
    st.caption("A disponibilidade e o preço podem variar conforme a região.")

st.session_state.setdefault("steam_page", 1)
st.session_state.setdefault("steam_query", "")
st.session_state.setdefault("steam_detail_id", None)

with st.form("pesquisa_steam"):
    termo_input = st.text_input(
        "Nome do jogo (deixe vazio para explorar a loja):",
        value=st.session_state.steam_query,
    )
    pesquisar = st.form_submit_button("Pesquisar")

if pesquisar:
    st.session_state.steam_query = termo_input.strip()
    st.session_state.steam_page = 1
    st.session_state.steam_detail_id = None

inicio = (st.session_state.steam_page - 1) * TAMANHO_PAGINA
try:
    with st.spinner("Pesquisando na loja Steam..."):
        resposta_jogos = pesquisar_jogos(
            st.session_state.steam_query,
            inicio,
            pais,
            idioma,
        )
except RuntimeError as erro:
    st.error(str(erro))
    resposta_jogos = {"total": 0, "results": []}

jogos = resposta_jogos["results"]
total_jogos = resposta_jogos["total"]
total_paginas = max(1, (total_jogos + TAMANHO_PAGINA - 1) // TAMANHO_PAGINA)
st.success(
    f"{total_jogos:,} resultados encontrados. "
    f"Página {st.session_state.steam_page} de {total_paginas}."
)

if jogos:
    colunas = st.columns(2)
    for indice, jogo in enumerate(jogos):
        with colunas[indice % 2]:
            with st.container(border=True):
                if jogo["image"]:
                    st.image(jogo["image"], use_container_width=True)
                st.subheader(jogo["name"])
                st.write(f"**Lançamento:** {jogo['release'] or 'Não informado'}")
                st.write(
                    f"**Plataformas:** {', '.join(jogo['platforms']) or 'Não informado'}"
                )
                coluna_detalhes, coluna_loja = st.columns(2)
                with coluna_detalhes:
                    if st.button(
                        "Mais informações",
                        key=f"detalhes_{st.session_state.steam_page}_{indice}_{jogo['id']}",
                    ):
                        st.session_state.steam_detail_id = jogo["id"]
                        st.rerun()
                with coluna_loja:
                    st.link_button("Abrir na Steam", jogo["url"], use_container_width=True)

    coluna_anterior, coluna_pagina, coluna_proxima = st.columns([1, 2, 1])
    with coluna_anterior:
        if st.button("⬅️ Anterior", disabled=st.session_state.steam_page <= 1):
            st.session_state.steam_page -= 1
            st.rerun()
    with coluna_pagina:
        st.write(f"Página {st.session_state.steam_page} de {total_paginas}")
    with coluna_proxima:
        if st.button(
            "Próxima ➡️",
            disabled=st.session_state.steam_page >= total_paginas,
        ):
            st.session_state.steam_page += 1
            st.rerun()
else:
    st.info("Nenhum jogo encontrado. Tente outro título.")

if st.session_state.steam_detail_id is not None:
    try:
        detalhe = carregar_detalhes_jogo(
            st.session_state.steam_detail_id,
            pais,
            idioma,
        )
    except RuntimeError as erro:
        st.error(str(erro))
    else:
        with st.expander(f"Detalhes: {detalhe.get('name', 'Jogo')}", expanded=True):
            descricao_html = detalhe.get("short_description") or detalhe.get("about_the_game", "")
            descricao = BeautifulSoup(descricao_html, "html.parser").get_text(" ", strip=True)
            if descricao:
                st.write(descricao)

            generos = [
                item["description"]
                for item in detalhe.get("genres", [])
                if item.get("description")
            ]
            desenvolvedores = detalhe.get("developers", [])
            distribuidoras = detalhe.get("publishers", [])
            data_lancamento = detalhe.get("release_date", {}).get("date")
            plataformas = [
                nome
                for chave, nome in PLATAFORMAS.items()
                if detalhe.get("platforms", {}).get(chave)
            ]
            metacritic = detalhe.get("metacritic", {}).get("score")
            st.write(f"**Preço na região selecionada:** {formatar_preco(detalhe)}")
            st.write(f"**Lançamento:** {data_lancamento or 'Não informado'}")
            st.write(f"**Plataformas:** {', '.join(plataformas) or 'Não informado'}")
            st.write(f"**Gêneros:** {', '.join(generos) or 'Não informado'}")
            st.write(
                f"**Desenvolvedora(s):** {', '.join(desenvolvedores) or 'Não informado'}"
            )
            st.write(
                f"**Distribuidora(s):** {', '.join(distribuidoras) or 'Não informado'}"
            )
            st.write(
                f"**Avaliação Metacritic:** {metacritic if metacritic is not None else 'N/A'}"
            )
            st.write(f"**Site oficial:** {detalhe.get('website') or 'Não informado'}")
            st.link_button(
                "Abrir na Steam",
                f"https://store.steampowered.com/app/{st.session_state.steam_detail_id}/",
            )
