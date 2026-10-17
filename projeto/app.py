import os

import requests
import streamlit as st
from bs4 import BeautifulSoup

RAWG_API_URL = "https://api.rawg.io/api"
TAMANHO_PAGINA = 20
TAMANHO_PAGINA_CATALOGO = 40
ORDENACOES = {
    "Mais relevantes": "",
    "Mais recentes": "-released",
    "Melhor avaliados": "-rating",
    "Mais populares": "-added",
}

st.set_page_config(
    page_title="Enciclopédia de Jogos RAWG",
    page_icon="🎮",
    layout="wide",
)


def obter_chave_api():
    chave = os.environ.get("RAWG_API_KEY", "").strip()
    if chave:
        return chave

    try:
        return str(st.secrets.get("RAWG_API_KEY", "")).strip()
    except Exception:
        return ""


def consultar_rawg(endpoint, chave, parametros=None):
    parametros = dict(parametros or {})
    parametros["key"] = chave

    try:
        resposta = requests.get(
            f"{RAWG_API_URL}/{endpoint.lstrip('/')}",
            params=parametros,
            timeout=25,
        )
    except requests.Timeout as exc:
        raise RuntimeError("A API RAWG demorou demais para responder.") from exc
    except requests.RequestException as exc:
        raise RuntimeError("Não foi possível conectar à API RAWG.") from exc

    if resposta.status_code in (401, 403):
        raise RuntimeError("A RAWG recusou a chave. Confira a chave e o acesso da sua conta.")
    if not resposta.ok:
        raise RuntimeError(f"A API RAWG respondeu com HTTP {resposta.status_code}.")

    try:
        return resposta.json()
    except ValueError as exc:
        raise RuntimeError("A API RAWG retornou uma resposta inválida.") from exc


@st.cache_data(ttl=86400, show_spinner=False)
def carregar_catalogo(endpoint, chave):
    itens = []
    for pagina in range(1, 101):
        dados = consultar_rawg(
            endpoint,
            chave,
            {"page": pagina, "page_size": TAMANHO_PAGINA_CATALOGO},
        )
        resultados = dados.get("results", [])
        itens.extend(resultados)
        if not dados.get("next") or not resultados:
            break
    return itens


@st.cache_data(ttl=900, show_spinner=False)
def pesquisar_jogos(chave, termo, plataformas, generos, ordenacao, pagina):
    parametros = {"page": pagina, "page_size": TAMANHO_PAGINA}
    if termo:
        parametros["search"] = termo
    if plataformas:
        parametros["platforms"] = ",".join(str(item) for item in plataformas)
    if generos:
        parametros["genres"] = ",".join(str(item) for item in generos)
    if ordenacao:
        parametros["ordering"] = ordenacao

    return consultar_rawg("games", chave, parametros)


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_detalhes_jogo(chave, jogo_id):
    return consultar_rawg(f"games/{jogo_id}", chave)


st.title("🎮 Enciclopédia Aberta de Jogos")
st.write("Pesquise o catálogo da RAWG por título, plataforma e gênero, com resultados paginados.")
st.markdown("Dados fornecidos pela [RAWG](https://rawg.io).")

chave_api = obter_chave_api()
if not chave_api:
    st.info("A interface está em preview. Configure sua chave RAWG para habilitar as buscas.")
    st.code('RAWG_API_KEY = "SUA_CHAVE_RAWG"', language="toml")
    st.caption("Salve em .streamlit/secrets.toml. Esse arquivo é ignorado pelo Git.")

plataformas_catalogo = []
generos_catalogo = []
if chave_api:
    try:
        with st.spinner("Carregando plataformas e gêneros disponíveis..."):
            plataformas_catalogo = carregar_catalogo("platforms", chave_api)
            generos_catalogo = carregar_catalogo("genres", chave_api)
    except RuntimeError as erro:
        st.error(str(erro))

plataformas_por_nome = {
    item["name"]: item["id"]
    for item in plataformas_catalogo
    if item.get("name") and item.get("id") is not None
}
generos_por_nome = {
    item["name"]: item["slug"]
    for item in generos_catalogo
    if item.get("name") and item.get("slug")
}

st.sidebar.header("Filtros")
if chave_api:
    st.sidebar.caption(
        f"{len(plataformas_por_nome)} plataformas e {len(generos_por_nome)} gêneros carregados"
    )
else:
    st.sidebar.caption("Filtros disponíveis após configurar a chave RAWG")

st.session_state.setdefault("rawg_page", 1)
st.session_state.setdefault("rawg_detail_id", None)

with st.form("pesquisa_rawg"):
    termo_input = st.text_input("Nome do jogo (deixe vazio para explorar o catálogo):")
    plataformas_input = st.multiselect(
        "Plataformas (nenhuma selecionada = todas):",
        options=sorted(plataformas_por_nome),
        disabled=not chave_api,
    )
    generos_input = st.multiselect(
        "Gêneros (nenhum selecionado = todos):",
        options=sorted(generos_por_nome),
        disabled=not chave_api,
    )
    ordenacao_input = st.selectbox("Ordenar por:", options=list(ORDENACOES))
    pesquisar = st.form_submit_button("Pesquisar", disabled=not chave_api)

if pesquisar:
    st.session_state.rawg_query = termo_input.strip()
    st.session_state.rawg_platforms = tuple(
        plataformas_por_nome[nome] for nome in plataformas_input
    )
    st.session_state.rawg_genres = tuple(
        generos_por_nome[nome] for nome in generos_input
    )
    st.session_state.rawg_order = ORDENACOES[ordenacao_input]
    st.session_state.rawg_page = 1
    st.session_state.rawg_detail_id = None

if chave_api:
    try:
        with st.spinner("Buscando jogos na RAWG..."):
            resposta_jogos = pesquisar_jogos(
                chave_api,
                st.session_state.get("rawg_query", ""),
                st.session_state.get("rawg_platforms", ()),
                st.session_state.get("rawg_genres", ()),
                st.session_state.get("rawg_order", ""),
                st.session_state.rawg_page,
            )
    except RuntimeError as erro:
        st.error(str(erro))
        resposta_jogos = {"count": 0, "results": []}
else:
    resposta_jogos = {"count": 0, "results": []}

jogos = resposta_jogos.get("results", [])
total_jogos = resposta_jogos.get("count", 0)
total_paginas = max(1, (total_jogos + TAMANHO_PAGINA - 1) // TAMANHO_PAGINA)

if chave_api:
    st.success(
        f"{total_jogos:,} resultados encontrados. "
        f"Página {st.session_state.rawg_page} de {total_paginas}."
    )

if jogos:
    colunas = st.columns(2)
    for indice, jogo in enumerate(jogos):
        plataformas_jogo = [
            item.get("platform", {}).get("name")
            for item in jogo.get("platforms", [])
            if item.get("platform", {}).get("name")
        ]
        generos_jogo = [
            item.get("name") for item in jogo.get("genres", []) if item.get("name")
        ]

        with colunas[indice % 2]:
            with st.container(border=True):
                imagem = jogo.get("background_image")
                if imagem:
                    st.image(imagem, use_container_width=True)
                st.subheader(jogo.get("name", "Jogo sem título"))
                st.write(f"**Lançamento:** {jogo.get('released') or 'Não informado'}")
                st.write(f"**Plataformas:** {', '.join(plataformas_jogo) or 'Não informado'}")
                st.write(f"**Gêneros:** {', '.join(generos_jogo) or 'Não informado'}")
                avaliacao = jogo.get("rating")
                metacritic = jogo.get("metacritic")
                st.write(
                    f"**Avaliação RAWG:** {avaliacao if avaliacao is not None else 'N/A'}/5  |  "
                    f"**Metacritic:** {metacritic if metacritic is not None else 'N/A'}"
                )
                if st.button("Mais informações", key=f"detalhes_{jogo['id']}"):
                    st.session_state.rawg_detail_id = jogo["id"]
                    st.rerun()

    coluna_anterior, coluna_pagina, coluna_proxima = st.columns([1, 2, 1])
    with coluna_anterior:
        if st.button("⬅️ Anterior", disabled=st.session_state.rawg_page <= 1):
            st.session_state.rawg_page -= 1
            st.rerun()
    with coluna_pagina:
        st.write(f"Página {st.session_state.rawg_page} de {total_paginas}")
    with coluna_proxima:
        if st.button("Próxima ➡️", disabled=st.session_state.rawg_page >= total_paginas):
            st.session_state.rawg_page += 1
            st.rerun()
elif chave_api:
    st.info("Nenhum jogo encontrado com esses filtros. Tente outro termo ou plataforma.")

if chave_api and st.session_state.rawg_detail_id is not None:
    try:
        detalhe = carregar_detalhes_jogo(chave_api, st.session_state.rawg_detail_id)
    except RuntimeError as erro:
        st.error(str(erro))
    else:
        with st.expander(f"Detalhes: {detalhe.get('name', 'Jogo')}", expanded=True):
            descricao = BeautifulSoup(
                detalhe.get("description", ""), "html.parser"
            ).get_text(" ", strip=True)
            if descricao:
                st.write(descricao)
            desenvolvedores = [
                item.get("name")
                for item in detalhe.get("developers", [])
                if item.get("name")
            ]
            distribuidoras = [
                item.get("name")
                for item in detalhe.get("publishers", [])
                if item.get("name")
            ]
            st.write(f"**Desenvolvedora(s):** {', '.join(desenvolvedores) or 'Não informado'}")
            st.write(f"**Distribuidora(s):** {', '.join(distribuidoras) or 'Não informado'}")
            st.write(f"**Site oficial:** {detalhe.get('website') or 'Não informado'}")
            slug = detalhe.get("slug")
            if slug:
                st.link_button("Abrir na RAWG", f"https://rawg.io/games/{slug}")