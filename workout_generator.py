# -*- coding: utf-8 -*-
"""
workout_generator.py
=====================

Este módulo contém toda a LÓGICA de montagem dos treinos. Ele não sabe nada
sobre interface gráfica (Kivy) nem sobre banco de dados SQLite — ele só
recebe a lista de exercícios (vinda do CSV) e devolve listas de exercícios
sorteados, já organizadas conforme as regras pedidas:

- **Grupo muscular**: 5 exercícios aleatórios daquele grupo + nível, 3 séries cada.
- **A/B**: 6 exercícios de membros superiores (dia A) e 6 de membros
  inferiores (dia B), 3 séries cada, com a perna do dia B contendo pelo
  menos 1 exercício de panturrilha.
- **Full body**: 6 exercícios no total — 2 de perna (sendo pelo menos 1 de
  panturrilha), 2 de costas/bíceps (1 majoritariamente costas + 1
  majoritariamente bíceps) e 2 de peito/tríceps (1 majoritariamente peito +
  1 majoritariamente tríceps).

Sempre que não houver exercícios suficientes no banco para cumprir uma regra
exatamente (por exemplo, pediram um nível "Avançado" para um grupo que só
tem 2 exercícios avançados), o código tenta se adaptar, completando com
exercícios de outros níveis mais próximos, em vez de travar com um erro -
mas avisa isso através do campo "avisos" do resultado.
"""

import random  # Biblioteca padrão usada para todos os sorteios aleatórios deste módulo


# Número de séries fixo que cada exercício deve ter, conforme pedido.
SERIES_PADRAO = 3

# Lista oficial dos níveis de dificuldade existentes no banco de exercícios.
# A ordem é importante: usamos essa ordem para "subir" ou "descer" de nível
# quando não há exercícios suficientes no nível exato pedido pelo usuário.
NIVEIS = ["Iniciante", "Intermediário", "Avançado"]

# Lista oficial dos grupos musculares principais, exatamente como aparecem
# na coluna "grupo_muscular" do CSV. É essa lista que alimenta o seletor de
# "grupo muscular específico" na aba "Montar novo treino".
GRUPOS_MUSCULARES = ["Peito", "Costas", "Ombros", "Braços", "Pernas", "Abdômen/Core"]


def _filtrar(exercicios, **filtros):
    """
    Função auxiliar interna que filtra a lista de exercícios por qualquer
    combinação de colunas (ex.: grupo_muscular="Pernas", nivel="Iniciante").

    Parameters
    ----------
    exercicios : list[dict]
        Lista completa (ou já parcialmente filtrada) de exercícios.
    **filtros : dict
        Pares coluna=valor para filtrar. A comparação não diferencia
        maiúsculas/minúsculas, para evitar bugs bobos de digitação.

    Returns
    -------
    list[dict]
        Apenas os exercícios que combinam com TODOS os filtros informados.
    """
    resultado = exercicios
    for coluna, valor_esperado in filtros.items():
        if valor_esperado is None:
            continue  # Filtro vazio = não filtra por essa coluna
        resultado = [
            ex for ex in resultado
            if ex.get(coluna, "").lower() == valor_esperado.lower()
        ]
    return resultado


def _contem_musculo(exercicio, palavra):
    """
    Verifica se a coluna 'musculo_principal' de um exercício contém uma
    determinada palavra (ex.: "Bíceps"), ignorando maiúsculas/minúsculas.

    Isso é necessário porque um mesmo exercício pode trabalhar mais de um
    músculo, com valores como "Bíceps/Antebraço" ou "Costas/Peito/Tríceps".

    Parameters
    ----------
    exercicio : dict
        O exercício a ser verificado.
    palavra : str
        A palavra-chave a procurar dentro do campo 'musculo_principal'.

    Returns
    -------
    bool
        True se a palavra aparecer no campo, False caso contrário.
    """
    return palavra.lower() in exercicio.get("musculo_principal", "").lower()


def _sortear_com_fallback(pool_por_nivel, nivel_desejado, quantidade, avisos, descricao):
    """
    Sorteia 'quantidade' exercícios distintos de uma lista, tentando primeiro
    o nível exato pedido. Se não houver exercícios suficientes, "empresta"
    exercícios dos níveis vizinhos (mais fácil primeiro, depois mais difícil),
    registrando um aviso para o usuário sobre essa adaptação.

    Parameters
    ----------
    pool_por_nivel : list[dict]
        Lista de exercícios já filtrada pelo grupo/músculo desejado, mas
        ainda contendo todos os níveis de dificuldade.
    nivel_desejado : str
        Nível de dificuldade que o usuário escolheu.
    quantidade : int
        Quantos exercícios diferentes deveriam ser sorteados.
    avisos : list[str]
        Lista (mutável) onde avisos de "faltou exercício" são adicionados.
    descricao : str
        Texto descritivo usado na mensagem de aviso (ex.: "panturrilha").

    Returns
    -------
    list[dict]
        Lista com até 'quantidade' exercícios sorteados, sem repetição.
    """
    # Começa filtrando exatamente pelo nível pedido.
    candidatos_nivel_exato = [ex for ex in pool_por_nivel if ex.get("nivel") == nivel_desejado]

    # Se já tiver exercícios suficientes no nível exato, sorteia direto.
    if len(candidatos_nivel_exato) >= quantidade:
        return random.sample(candidatos_nivel_exato, quantidade)

    # Caso contrário, monta uma lista de "níveis em ordem de prioridade" a
    # partir do nível desejado, começando pelos vizinhos mais próximos.
    indice_desejado = NIVEIS.index(nivel_desejado)
    ordem_prioridade = sorted(NIVEIS, key=lambda n: abs(NIVEIS.index(n) - indice_desejado))

    escolhidos = list(candidatos_nivel_exato)  # Já aproveita os do nível exato
    nomes_escolhidos = {ex["exercicio"] for ex in escolhidos}

    for nivel in ordem_prioridade:
        if len(escolhidos) >= quantidade:
            break
        candidatos = [
            ex for ex in pool_por_nivel
            if ex.get("nivel") == nivel and ex["exercicio"] not in nomes_escolhidos
        ]
        random.shuffle(candidatos)
        for ex in candidatos:
            if len(escolhidos) >= quantidade:
                break
            escolhidos.append(ex)
            nomes_escolhidos.add(ex["exercicio"])

    if len(escolhidos) < quantidade:
        avisos.append(
            f"Não há exercícios suficientes de '{descricao}' no banco de dados "
            f"para completar a quantidade pedida ({quantidade}). "
            f"Foram incluídos apenas {len(escolhidos)}."
        )

    return escolhidos


def _formatar_exercicio(exercicio, dia=None):
    """
    Transforma um exercício do banco (dict do CSV) em um item de treino
    pronto para exibição, já incluindo o número de séries padrão e,
    opcionalmente, o "dia" do treino (usado no tipo A/B).

    Parameters
    ----------
    exercicio : dict
        Exercício original vindo do CSV.
    dia : str or None
        "A" ou "B" para treinos do tipo A/B; None para os demais tipos.

    Returns
    -------
    dict
        Dicionário com os campos prontos para exibição e armazenamento.
    """
    item = {
        "exercicio": exercicio["exercicio"],
        "grupo_muscular": exercicio["grupo_muscular"],
        "musculo_principal": exercicio["musculo_principal"],
        "equipamento": exercicio["equipamento"],
        "nivel": exercicio["nivel"],
        "series": SERIES_PADRAO,
    }
    if dia is not None:
        item["dia"] = dia
    return item


# ---------------------------------------------------------------------------
# GERADOR 1: TREINO POR GRUPO MUSCULAR ESPECÍFICO
# ---------------------------------------------------------------------------

def gerar_treino_grupo_muscular(exercicios, grupo_muscular, nivel):
    """
    Gera um treino sorteando 5 exercícios aleatórios de um grupo muscular
    específico e nível de dificuldade escolhidos pelo usuário.

    Regra especial: se o grupo escolhido for "Pernas", pelo menos 1 dos 5
    exercícios sorteados deve ser de panturrilha.

    Parameters
    ----------
    exercicios : list[dict]
        Lista completa de exercícios (carregada do CSV).
    grupo_muscular : str
        Um dos valores em GRUPOS_MUSCULARES (ex.: "Costas").
    nivel : str
        Um dos valores em NIVEIS (ex.: "Iniciante").

    Returns
    -------
    dict
        {
            "exercicios": list[dict]  -> os 5 exercícios sorteados (já formatados),
            "avisos": list[str]       -> mensagens sobre eventuais adaptações.
        }
    """
    avisos = []  # Lista que vai acumular avisos sobre eventuais limitações de dados

    # Filtra apenas os exercícios do grupo muscular pedido (em qualquer nível,
    # para permitir o "fallback" de nível dentro de _sortear_com_fallback).
    pool_grupo = _filtrar(exercicios, grupo_muscular=grupo_muscular)

    selecionados = []

    # Regra especial: treino de pernas precisa ter ao menos 1 exercício de panturrilha.
    if grupo_muscular.lower() == "pernas":
        pool_panturrilha = [ex for ex in pool_grupo if _contem_musculo(ex, "Panturrilha")]
        panturrilha_sorteada = _sortear_com_fallback(pool_panturrilha, nivel, 1, avisos, "panturrilha")
        selecionados.extend(panturrilha_sorteada)

        # Remove a(s) panturrilha(s) já escolhidas do pool para não repetir,
        # e sorteia o restante (4 exercícios) entre os demais exercícios de perna.
        nomes_usados = {ex["exercicio"] for ex in selecionados}
        pool_restante = [ex for ex in pool_grupo if ex["exercicio"] not in nomes_usados]
        restantes = _sortear_com_fallback(pool_restante, nivel, 5 - len(selecionados), avisos, "pernas")
        selecionados.extend(restantes)
    else:
        # Para os demais grupos musculares, sorteia 5 exercícios livremente.
        selecionados = _sortear_com_fallback(pool_grupo, nivel, 5, avisos, grupo_muscular)

    # Converte os exercícios brutos do CSV para o formato final de exibição.
    exercicios_formatados = [_formatar_exercicio(ex) for ex in selecionados]

    return {"exercicios": exercicios_formatados, "avisos": avisos}


# ---------------------------------------------------------------------------
# GERADOR 2: TREINO A/B (SUPERIORES / INFERIORES)
# ---------------------------------------------------------------------------

def gerar_treino_ab(exercicios, nivel):
    """
    Gera o famoso "treino A/B": 6 exercícios de membros superiores para o
    dia A e 6 exercícios de membros inferiores (pernas) para o dia B, ambos
    com 3 séries cada. O dia B deve obrigatoriamente conter pelo menos 1
    exercício de panturrilha.

    Parameters
    ----------
    exercicios : list[dict]
        Lista completa de exercícios.
    nivel : str
        Nível de dificuldade escolhido pelo usuário.

    Returns
    -------
    dict
        {
            "dia_a": list[dict],   -> 6 exercícios de superiores,
            "dia_b": list[dict],   -> 6 exercícios de inferiores,
            "avisos": list[str],
        }
    """
    avisos = []

    # Membros superiores = Peito, Costas, Ombros e Braços (bíceps/tríceps/antebraço).
    pool_superiores = [
        ex for ex in exercicios
        if ex.get("grupo_muscular") in ("Peito", "Costas", "Ombros", "Braços")
    ]
    # Membros inferiores = tudo que está marcado como "Pernas" no CSV.
    pool_inferiores = _filtrar(exercicios, grupo_muscular="Pernas")

    # --- Dia A (superiores): sorteia 6 exercícios, sem regra extra de proporção ---
    selecionados_a = _sortear_com_fallback(pool_superiores, nivel, 6, avisos, "membros superiores")

    # --- Dia B (inferiores): precisa ter pelo menos 1 exercício de panturrilha ---
    pool_panturrilha = [ex for ex in pool_inferiores if _contem_musculo(ex, "Panturrilha")]
    panturrilha_sorteada = _sortear_com_fallback(pool_panturrilha, nivel, 1, avisos, "panturrilha (dia B)")

    nomes_usados_b = {ex["exercicio"] for ex in panturrilha_sorteada}
    pool_inferiores_restante = [ex for ex in pool_inferiores if ex["exercicio"] not in nomes_usados_b]
    restantes_b = _sortear_com_fallback(
        pool_inferiores_restante, nivel, 6 - len(panturrilha_sorteada), avisos, "membros inferiores"
    )
    selecionados_b = panturrilha_sorteada + restantes_b

    return {
        "dia_a": [_formatar_exercicio(ex, dia="A") for ex in selecionados_a],
        "dia_b": [_formatar_exercicio(ex, dia="B") for ex in selecionados_b],
        "avisos": avisos,
    }


# ---------------------------------------------------------------------------
# GERADOR 3: TREINO FULL BODY (CORPO TODO)
# ---------------------------------------------------------------------------

def gerar_treino_full_body(exercicios, nivel):
    """
    Gera um treino full body com 6 exercícios no total, divididos assim:

    - 2 exercícios de PERNA, sendo pelo menos 1 obrigatoriamente de panturrilha;
    - 2 exercícios de COSTAS/BÍCEPS, em quantidade igual: 1 majoritariamente
      costas + 1 majoritariamente bíceps;
    - 2 exercícios de PEITO/TRÍCEPS, em quantidade igual: 1 majoritariamente
      peito + 1 majoritariamente tríceps.

    Parameters
    ----------
    exercicios : list[dict]
        Lista completa de exercícios.
    nivel : str
        Nível de dificuldade escolhido pelo usuário.

    Returns
    -------
    dict
        {
            "exercicios": list[dict],  -> os 6 exercícios sorteados (já formatados),
            "avisos": list[str],
        }
    """
    avisos = []
    selecionados = []

    # --- Bloco de PERNA (2 exercícios, 1 panturrilha obrigatória) ---
    pool_pernas = _filtrar(exercicios, grupo_muscular="Pernas")
    pool_panturrilha = [ex for ex in pool_pernas if _contem_musculo(ex, "Panturrilha")]

    panturrilha = _sortear_com_fallback(pool_panturrilha, nivel, 1, avisos, "panturrilha (full body)")
    nomes_usados = {ex["exercicio"] for ex in panturrilha}
    pool_pernas_restante = [ex for ex in pool_pernas if ex["exercicio"] not in nomes_usados]
    outra_perna = _sortear_com_fallback(pool_pernas_restante, nivel, 1, avisos, "perna (full body)")

    selecionados.extend(panturrilha)
    selecionados.extend(outra_perna)

    # --- Bloco de COSTAS/BÍCEPS (1 costas + 1 bíceps) ---
    pool_costas = _filtrar(exercicios, grupo_muscular="Costas")
    pool_biceps = [
        ex for ex in exercicios
        if ex.get("grupo_muscular") == "Braços" and _contem_musculo(ex, "Bíceps")
    ]

    costas = _sortear_com_fallback(pool_costas, nivel, 1, avisos, "costas (full body)")
    biceps = _sortear_com_fallback(pool_biceps, nivel, 1, avisos, "bíceps (full body)")
    selecionados.extend(costas)
    selecionados.extend(biceps)

    # --- Bloco de PEITO/TRÍCEPS (1 peito + 1 tríceps) ---
    pool_peito = _filtrar(exercicios, grupo_muscular="Peito")
    pool_triceps = [
        ex for ex in exercicios
        if ex.get("grupo_muscular") == "Braços" and _contem_musculo(ex, "Tríceps")
    ]

    peito = _sortear_com_fallback(pool_peito, nivel, 1, avisos, "peito (full body)")
    triceps = _sortear_com_fallback(pool_triceps, nivel, 1, avisos, "tríceps (full body)")
    selecionados.extend(peito)
    selecionados.extend(triceps)

    exercicios_formatados = [_formatar_exercicio(ex) for ex in selecionados]
    return {"exercicios": exercicios_formatados, "avisos": avisos}
