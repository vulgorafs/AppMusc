# -*- coding: utf-8 -*-
"""
db.py
=====

Este módulo é responsável por TODO o acesso a dados do aplicativo:

1. Leitura do arquivo CSV ``data/exercicios.csv``, que é o banco de exercícios
   (somente leitura, vem junto com o app).
2. Criação e acesso a um banco de dados SQLite local (``treino.db``), onde o
   app guarda:
   - Os treinos que o usuário gerou e salvou (tabela ``treinos``);
   - O diário de peso corporal do usuário (tabela ``peso_diario``);
   - As preferências do usuário, como o tema escolhido (tabela ``config``).

Importante sobre segurança: TODAS as consultas SQL usam parâmetros
(placeholders ``?``) em vez de concatenação de strings. Isso evita por
completo o risco de SQL Injection, mesmo que o app receba qualquer tipo de
texto digitado pelo usuário (ex.: nome de treino).

O banco SQLite fica salvo dentro da pasta de dados do próprio app
(``App.user_data_dir`` quando empacotado pelo Kivy/Buildozer), então cada
usuário tem seus próprios dados, isolados do resto do sistema do celular.
"""

import csv          # Biblioteca padrão do Python para ler arquivos CSV
import sqlite3       # Biblioteca padrão do Python para banco de dados SQLite (não precisa instalar nada)
import os            # Para checar caminhos de arquivos/pastas
import json          # Para serializar a lista de exercícios de um treino salvo (lista de dicts) em texto


# ---------------------------------------------------------------------------
# CARREGAMENTO DO BANCO DE EXERCÍCIOS (CSV)
# ---------------------------------------------------------------------------

def carregar_exercicios(caminho_csv):
    """
    Lê o arquivo CSV de exercícios e retorna uma lista de dicionários.

    Cada dicionário representa uma linha (um exercício) com as chaves:
    ``exercicio``, ``grupo_muscular``, ``musculo_principal``, ``equipamento``,
    ``tipo`` e ``nivel`` (essas são exatamente as colunas do CSV fornecido).

    Parameters
    ----------
    caminho_csv : str
        Caminho completo (ou relativo) para o arquivo ``exercicios.csv``.

    Returns
    -------
    list[dict]
        Lista de exercícios, cada um representado como dicionário.

    Raises
    ------
    FileNotFoundError
        Se o arquivo não existir no caminho informado.
    """
    # Verifica se o arquivo realmente existe antes de tentar abrir, para dar
    # uma mensagem de erro clara em vez de um traceback confuso.
    if not os.path.isfile(caminho_csv):
        raise FileNotFoundError(f"Arquivo de exercícios não encontrado: {caminho_csv}")

    exercicios = []  # Lista que vai acumular todos os exercícios lidos

    # newline='' é recomendado pela documentação do módulo csv para evitar
    # problemas com quebras de linha duplicadas (\r\n) em arquivos do Windows.
    # encoding='utf-8' garante que os acentos (á, é, í, ô, ç...) sejam lidos corretamente.
    with open(caminho_csv, newline='', encoding='utf-8') as arquivo:
        leitor = csv.DictReader(arquivo)  # DictReader já usa a primeira linha como cabeçalho
        for linha in leitor:
            # Remove espaços em branco extras no início/fim de cada valor,
            # caso o CSV tenha sido editado manualmente em algum momento.
            linha_limpa = {chave: valor.strip() for chave, valor in linha.items()}
            exercicios.append(linha_limpa)

    return exercicios


# ---------------------------------------------------------------------------
# BANCO DE DADOS SQLITE (treinos salvos + diário de peso + configurações)
# ---------------------------------------------------------------------------

class BancoDeDados:
    """
    Encapsula toda a comunicação com o banco SQLite local do aplicativo.

    Esta classe abre uma única conexão com o arquivo ``.db`` e oferece
    métodos de alto nível (salvar treino, listar treinos, registrar peso,
    etc.) para o resto do app, sem que nenhuma outra parte do código precise
    escrever SQL diretamente.
    """

    def __init__(self, caminho_db):
        """
        Abre (ou cria, se não existir) o arquivo de banco de dados SQLite e
        garante que todas as tabelas necessárias existam.

        Parameters
        ----------
        caminho_db : str
            Caminho completo onde o arquivo ``treino.db`` deve ficar salvo.
        """
        # check_same_thread=False permite que a conexão seja usada a partir
        # de callbacks do Kivy que podem rodar fora da thread principal de
        # criação do objeto (o Kivy é single-threaded por padrão, mas isso
        # evita um erro comum em apps que usam Clock.schedule_once, etc.)
        self.conexao = sqlite3.connect(caminho_db, check_same_thread=False)

        # Faz com que as linhas retornadas se comportem como dicionários
        # (acessíveis por nome de coluna), o que torna o código mais legível.
        self.conexao.row_factory = sqlite3.Row

        self._criar_tabelas()

    def _criar_tabelas(self):
        """
        Cria as tabelas do banco de dados, caso ainda não existam.

        Tabelas criadas:
        - ``treinos``: guarda cada treino gerado e salvo pelo usuário.
        - ``peso_diario``: guarda cada registro de peso corporal informado.
        - ``config``: guarda preferências simples do app (ex.: tema atual),
          em formato chave/valor.
        """
        cursor = self.conexao.cursor()

        # Tabela de treinos salvos.
        # 'exercicios_json' guarda a lista de exercícios do treino serializada
        # como texto JSON, já que cada treino pode ter um número e formato
        # variável de exercícios (não é uma estrutura "tabular" fixa).
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS treinos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                tipo TEXT NOT NULL,
                nivel TEXT NOT NULL,
                grupo_muscular TEXT,
                exercicios_json TEXT NOT NULL,
                data_criacao TEXT NOT NULL
            )
        """)

        # Tabela do diário de peso corporal.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS peso_diario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                peso_kg REAL NOT NULL,
                data_registro TEXT NOT NULL
            )
        """)

        # Tabela de configurações simples (chave -> valor), usada para
        # guardar, por exemplo, o tema escolhido ("claro" ou "escuro").
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        """)

        self.conexao.commit()  # Confirma a criação das tabelas no arquivo .db

    # ----------------------- TREINOS -----------------------

    def salvar_treino(self, titulo, tipo, nivel, grupo_muscular, lista_exercicios, data_criacao):
        """
        Salva um treino gerado pelo usuário no banco de dados.

        Parameters
        ----------
        titulo : str
            Nome de exibição do treino (ex.: "Treino de Costas - Iniciante").
        tipo : str
            Tipo do treino: "grupo_muscular", "ab" ou "full_body".
        nivel : str
            Nível de dificuldade escolhido: "Iniciante", "Intermediário" ou "Avançado".
        grupo_muscular : str or None
            Nome do grupo muscular, se o tipo escolhido foi "grupo_muscular".
            Pode ser None para os tipos "ab" e "full_body".
        lista_exercicios : list[dict]
            Lista de exercícios do treino. Cada item deve ser um dicionário
            (ex.: {"exercicio": "Supino reto", "series": 3, "dia": "A"}).
        data_criacao : str
            Data/hora de criação do treino, em formato texto (ex. ISO 8601).

        Returns
        -------
        int
            O ID do treino recém-criado no banco de dados.
        """
        cursor = self.conexao.cursor()
        # json.dumps converte a lista de dicionários Python em uma string
        # JSON, que pode ser armazenada em uma única coluna de texto.
        # ensure_ascii=False mantém os acentos legíveis dentro do banco.
        exercicios_json = json.dumps(lista_exercicios, ensure_ascii=False)

        # Observe o uso de "?" como placeholders: o sqlite3 substitui esses
        # pontos de interrogação pelos valores da tupla de forma segura,
        # protegendo contra SQL Injection.
        cursor.execute(
            """
            INSERT INTO treinos (titulo, tipo, nivel, grupo_muscular, exercicios_json, data_criacao)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (titulo, tipo, nivel, grupo_muscular, exercicios_json, data_criacao),
        )
        self.conexao.commit()
        return cursor.lastrowid  # ID gerado automaticamente pelo AUTOINCREMENT

    def listar_treinos(self):
        """
        Retorna todos os treinos salvos, do mais recente para o mais antigo.

        Returns
        -------
        list[dict]
            Lista de treinos. Cada treino é um dicionário com as colunas da
            tabela, e a chave ``exercicios`` já vem decodificada de volta
            para uma lista de dicionários Python (em vez do texto JSON bruto).
        """
        cursor = self.conexao.cursor()
        cursor.execute("SELECT * FROM treinos ORDER BY id DESC")
        linhas = cursor.fetchall()

        treinos = []
        for linha in linhas:
            treino = dict(linha)  # Converte sqlite3.Row em dict comum
            # Decodifica a string JSON de volta para uma lista de exercícios.
            treino["exercicios"] = json.loads(treino["exercicios_json"])
            treinos.append(treino)
        return treinos

    def excluir_treino(self, treino_id):
        """
        Remove um treino salvo pelo seu ID.

        Parameters
        ----------
        treino_id : int
            ID do treino a ser excluído (coluna ``id`` da tabela ``treinos``).
        """
        cursor = self.conexao.cursor()
        cursor.execute("DELETE FROM treinos WHERE id = ?", (treino_id,))
        self.conexao.commit()

    # ----------------------- DIÁRIO DE PESO -----------------------

    def registrar_peso(self, peso_kg, data_registro):
        """
        Adiciona um novo registro ao diário de peso corporal.

        Parameters
        ----------
        peso_kg : float
            Peso do usuário em quilogramas (ex.: 78.5).
        data_registro : str
            Data do registro, em formato texto (ex.: "2026-06-25").
        """
        cursor = self.conexao.cursor()
        cursor.execute(
            "INSERT INTO peso_diario (peso_kg, data_registro) VALUES (?, ?)",
            (peso_kg, data_registro),
        )
        self.conexao.commit()

    def listar_pesos(self):
        """
        Retorna todos os registros de peso, ordenados do mais antigo para o
        mais novo (ordem ideal para desenhar o gráfico de linha em sequência).

        Returns
        -------
        list[dict]
            Lista de registros, cada um com ``id``, ``peso_kg`` e ``data_registro``.
        """
        cursor = self.conexao.cursor()
        cursor.execute("SELECT * FROM peso_diario ORDER BY id ASC")
        return [dict(linha) for linha in cursor.fetchall()]

    def excluir_peso(self, peso_id):
        """
        Remove um registro específico do diário de peso pelo seu ID.

        Parameters
        ----------
        peso_id : int
            ID do registro a ser excluído (coluna ``id`` da tabela ``peso_diario``).
        """
        cursor = self.conexao.cursor()
        cursor.execute("DELETE FROM peso_diario WHERE id = ?", (peso_id,))
        self.conexao.commit()

    # ----------------------- ACOMPANHAMENTO DE EXERCÍCIOS CONCLUÍDOS -----------------------

    def atualizar_exercicios_treino(self, treino_id, lista_exercicios):
        """
        Sobrescreve a lista de exercícios de um treino já salvo — usado para
        persistir o campo "concluido" (True/False) quando o usuário marca ou
        desmarca a caixinha de um exercício na aba Home.

        Parameters
        ----------
        treino_id : int
            ID do treino a ser atualizado.
        lista_exercicios : list[dict]
            Lista completa de exercícios (com o campo "concluido" já
            atualizado), que substitui inteiramente a lista anterior.
        """
        cursor = self.conexao.cursor()
        exercicios_json = json.dumps(lista_exercicios, ensure_ascii=False)
        cursor.execute(
            "UPDATE treinos SET exercicios_json = ? WHERE id = ?",
            (exercicios_json, treino_id),
        )
        self.conexao.commit()

    def contar_exercicios_concluidos_por_musculo(self):
        """
        Percorre TODOS os treinos salvos e conta quantos exercícios
        marcados como concluídos ("concluido": True) existem para cada
        músculo, usado para montar o gráfico "Músculos mais treinados" na
        aba Configurações.

        Um mesmo exercício pode contar para mais de um músculo (ex.: um
        exercício com "musculo_principal" = "Peito/Tríceps" soma +1 tanto
        para "Peito" quanto para "Tríceps").

        Returns
        -------
        list[tuple[str, int]]
            Lista de pares (nome_do_musculo, quantidade), já ordenada da
            maior para a menor quantidade.
        """
        contagens = {}  # Dicionário {nome_do_musculo: quantidade_de_vezes_concluido}

        for treino in self.listar_treinos():
            for exercicio in treino["exercicios"]:
                if not exercicio.get("concluido"):
                    continue  # Só conta exercícios marcados como feitos
                # Um exercício pode trabalhar mais de um músculo (separados
                # por "/" no CSV original, ex.: "Peito/Tríceps").
                musculos = exercicio.get("musculo_principal", "").split("/")
                for musculo in musculos:
                    musculo = musculo.strip()
                    if not musculo:
                        continue
                    contagens[musculo] = contagens.get(musculo, 0) + 1

        # Ordena do músculo mais treinado para o menos treinado.
        return sorted(contagens.items(), key=lambda item: item[1], reverse=True)



    def definir_config(self, chave, valor):
        """
        Salva (ou atualiza) uma preferência simples de configuração.

        Usa ``INSERT ... ON CONFLICT`` para criar a chave se ela não existir,
        ou atualizar o valor se ela já existir — em uma única instrução.

        Parameters
        ----------
        chave : str
            Nome da configuração (ex.: "tema").
        valor : str
            Valor da configuração (ex.: "escuro").
        """
        cursor = self.conexao.cursor()
        cursor.execute(
            """
            INSERT INTO config (chave, valor) VALUES (?, ?)
            ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
            """,
            (chave, valor),
        )
        self.conexao.commit()

    def obter_config(self, chave, valor_padrao=None):
        """
        Lê o valor salvo de uma configuração.

        Parameters
        ----------
        chave : str
            Nome da configuração a ser lida.
        valor_padrao : str, optional
            Valor a retornar caso a configuração ainda não tenha sido salva.

        Returns
        -------
        str
            O valor salvo, ou ``valor_padrao`` se a chave não existir.
        """
        cursor = self.conexao.cursor()
        cursor.execute("SELECT valor FROM config WHERE chave = ?", (chave,))
        linha = cursor.fetchone()
        return linha["valor"] if linha is not None else valor_padrao

    def fechar(self):
        """Fecha a conexão com o banco de dados. Deve ser chamado ao sair do app."""
        self.conexao.close()
