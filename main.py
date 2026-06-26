# -*- coding: utf-8 -*-
"""
main.py
=======

Ponto de entrada do aplicativo "Monta Treino", feito em Kivy (Python puro).

Este arquivo define:

- ``IconWidget``: desenha, à mão (com Line/Color do Canvas do Kivy), os 4
  ícones usados na barra de navegação inferior (casa, halteres, "+", engrenagem).
  Os ícones são vetoriais (não usam imagens nem fontes de emoji), então
  ficam nítidos em qualquer tamanho de tela e não dependem de a fonte do
  aparelho suportar emoji.
- ``BottomNavItem``: um item clicável da barra de navegação inferior
  (ícone + texto), no estilo comum de apps mobile.
- ``GraficoPeso``: widget que desenha um gráfico de linha simples mostrando
  a evolução do peso corporal, também sem depender de bibliotecas externas.
- ``TelaHome``, ``TelaExercicios``, ``TelaNovoTreino``, ``TelaConfiguracoes``:
  as 4 telas do app (agora como ``Screen``, trocadas via ``ScreenManager``
  e navegadas pela barra inferior, em vez de abas no topo).
- ``TreinoApp``: a classe principal do aplicativo.

Todo o app funciona 100% OFFLINE: não há nenhuma chamada de rede, nenhuma
permissão de internet é solicitada no ``buildozer.spec``, e os únicos dados
gravados no aparelho são o banco SQLite local (treinos salvos e diário de
peso), dentro da pasta de dados privada do próprio app.
"""

import os                      # Para montar caminhos de arquivos de forma compatível entre sistemas
import math                    # Usado para calcular os "dentes" do ícone de engrenagem (config)
import datetime                 # Para registrar data/hora de criação de treinos e registros de peso

from kivy.app import App                          # Classe base de qualquer aplicativo Kivy
from kivy.uix.boxlayout import BoxLayout           # Layout em caixa (vertical ou horizontal)
from kivy.uix.floatlayout import FloatLayout       # Layout livre, usado para sobrepor a seta nos seletores e os rótulos no gráfico
from kivy.uix.anchorlayout import AnchorLayout     # Usado para centralizar verticalmente as barrinhas do gráfico de músculos
from kivy.uix.label import Label                   # Texto simples na tela
from kivy.uix.button import Button                 # Botão clicável
from kivy.uix.checkbox import CheckBox             # Caixinha de marcar (usada para marcar exercícios como concluídos)
from kivy.uix.scrollview import ScrollView         # Permite rolar conteúdo maior que a tela
from kivy.uix.widget import Widget                 # Widget genérico, usado como base dos ícones
from kivy.uix.popup import Popup                   # Janelas de aviso/confirmação
from kivy.uix.screenmanager import Screen          # Cada aba do app agora é uma "Screen" do ScreenManager
from kivy.uix.behaviors import ButtonBehavior      # Mixin que torna qualquer layout clicável
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle, Mesh  # Primitivas de desenho (Mesh é usado para desenhar triângulos preenchidos)
from kivy.metrics import dp                         # Conversão de pixels independente de densidade de tela
from kivy.properties import ListProperty, StringProperty, BooleanProperty, NumericProperty  # Propriedades reativas do Kivy
from kivy.factory import Factory                    # Usado para registrar manualmente classes customizadas (ver final do arquivo)
from kivy.clock import Clock                         # Usado para mostrar o aviso de saúde só depois que a tela inicial termina de aparecer

# Módulos próprios do projeto (lógica de dados e de geração de treinos).
from db import BancoDeDados, carregar_exercicios
from workout_generator import (
    gerar_treino_grupo_muscular,
    gerar_treino_ab,
    gerar_treino_full_body,
)


# ---------------------------------------------------------------------------
# CORES DOS TEMAS (claro / escuro)
# ---------------------------------------------------------------------------
# Cada tema tem: cor de fundo das telas, cor do texto principal, cor de
# destaque (barra de título / item de navegação ativo), cor da barra de
# navegação inferior e cor dos ícones/textos INATIVOS dessa barra.
TEMAS = {
    "claro": {
        "fundo": (0.95, 0.96, 0.98, 1),
        "superficie": (1.0, 1.0, 1.0, 1),
        "texto": (0.14, 0.15, 0.20, 1),
        "texto_suave": (0.46, 0.48, 0.55, 1),
        "destaque": (0.36, 0.42, 0.94, 1),
        "destaque_escura": (0.28, 0.33, 0.80, 1),
        "barra_nav": (1.0, 1.0, 1.0, 1),
        "nav_inativo": (0.58, 0.59, 0.65, 1),
        "borda": (0.0, 0.0, 0.0, 0.08),
    },
    "escuro": {
        "fundo": (0.06, 0.07, 0.10, 1),
        "superficie": (0.13, 0.14, 0.18, 1),
        "texto": (0.94, 0.95, 0.97, 1),
        "texto_suave": (0.64, 0.65, 0.72, 1),
        "destaque": (0.47, 0.54, 0.98, 1),
        "destaque_escura": (0.38, 0.45, 0.90, 1),
        "barra_nav": (0.10, 0.11, 0.15, 1),
        "nav_inativo": (0.50, 0.51, 0.58, 1),
        "borda": (1.0, 1.0, 1.0, 0.10),
    },
}


def _hex(cor):
    """
    Converte uma cor RGBA (lista/tupla de floats entre 0 e 1, como as usadas
    pelas ``ListProperty`` do Kivy) para uma string hexadecimal "RRGGBB",
    formato exigido pelo markup de cores do Kivy (ex.: ``[color=#5a6dfa]``).

    Parameters
    ----------
    cor : list[float] or tuple[float]
        Cor no formato (r, g, b, a), com cada valor entre 0 e 1.

    Returns
    -------
    str
        Cor em formato hexadecimal, sem o "#" (ex.: "5a6dfa").
    """
    return "".join(f"{int(max(0, min(1, c)) * 255):02x}" for c in cor[:3])


# ---------------------------------------------------------------------------
# ÍCONES VETORIAIS DA BARRA DE NAVEGAÇÃO INFERIOR
# ---------------------------------------------------------------------------

class IconWidget(Widget):
    """
    Widget que desenha, com linhas vetoriais simples, um dos 4 ícones usados
    na barra de navegação inferior do app.

    Desenhar os ícones "à mão" (em vez de usar imagens .png ou uma fonte de
    ícones/emoji) evita depender de arquivos externos ou da fonte instalada
    no aparelho do usuário, garantindo um visual consistente em qualquer
    tela e qualquer Android.

    Attributes
    ----------
    icon_name : str
        Qual ícone desenhar: "home", "exercicios", "novo_treino" ou "config".
    cor : list[float]
        Cor RGBA usada para desenhar as linhas do ícone (já reage a mudanças
        de tema, pois é "amarrada" no arquivo treino.kv a uma cor do app).
    """

    icon_name = StringProperty("home")
    cor = ListProperty([0, 0, 0, 1])

    def __init__(self, **kwargs):
        """Inicializa o widget e liga os eventos que disparam o redesenho do ícone."""
        super().__init__(**kwargs)
        self.bind(pos=self._desenhar, size=self._desenhar, cor=self._desenhar, icon_name=self._desenhar)

    def _desenhar(self, *args):
        """Limpa o canvas e redesenha o ícone correspondente a ``icon_name``."""
        self.canvas.clear()
        if self.width <= 1 or self.height <= 1:
            return  # Evita desenhar antes do widget ter um tamanho real definido

        with self.canvas:
            Color(*self.cor)
            espessura = dp(1.8)  # Espessura das linhas do ícone (estilo "outline", comum em apps modernos)

            if self.icon_name == "home":
                self._desenhar_casa(espessura)
            elif self.icon_name == "exercicios":
                self._desenhar_halteres(espessura)
            elif self.icon_name == "novo_treino":
                self._desenhar_mais(espessura)
            elif self.icon_name == "config":
                self._desenhar_engrenagem(espessura)
            elif self.icon_name == "seta_baixo":
                self._desenhar_seta(espessura, para_baixo=True)
            elif self.icon_name == "seta_cima":
                self._desenhar_seta(espessura, para_baixo=False)
            elif self.icon_name == "lixeira":
                self._desenhar_lixeira(espessura)

    def _desenhar_casa(self, espessura):
        """Desenha um ícone simples de casa (telhado triangular + corpo quadrado), para a aba Home."""
        x, y, w, h = self.x, self.y, self.width, self.height
        # Telhado: duas linhas formando um "telhado" triangular (sem fechar a base).
        Line(points=[x, y + h * 0.45, x + w * 0.5, y + h * 0.95, x + w, y + h * 0.45], width=espessura)
        # Corpo da casa: um retângulo abaixo do telhado.
        Line(rectangle=(x + w * 0.18, y + h * 0.05, w * 0.64, h * 0.45), width=espessura)
        # Pequena "porta" para dar mais identidade visual ao ícone.
        Line(points=[x + w * 0.5, y + h * 0.05, x + w * 0.5, y + h * 0.28], width=espessura)

    def _desenhar_halteres(self, espessura):
        """Desenha um ícone de halteres (barra com pesos nas pontas), para a aba Exercícios."""
        x, y, w, h = self.x, self.y, self.width, self.height
        # Barra central horizontal conectando os dois pesos.
        Line(points=[x + w * 0.22, y + h * 0.5, x + w * 0.78, y + h * 0.5], width=espessura * 1.4)
        # Peso (anilha) da esquerda e da direita, cada um como um retângulo vertical.
        Line(rectangle=(x, y + h * 0.22, w * 0.18, h * 0.56), width=espessura)
        Line(rectangle=(x + w * 0.82, y + h * 0.22, w * 0.18, h * 0.56), width=espessura)

    def _desenhar_mais(self, espessura):
        """Desenha um ícone de "+" (mais), para a aba Montar Novo Treino."""
        x, y, w, h = self.x, self.y, self.width, self.height
        # Uma linha vertical e uma horizontal, cruzando no centro, formando o "+".
        Line(points=[x + w * 0.5, y + h * 0.15, x + w * 0.5, y + h * 0.85], width=espessura * 1.6)
        Line(points=[x + w * 0.15, y + h * 0.5, x + w * 0.85, y + h * 0.5], width=espessura * 1.6)

    def _desenhar_engrenagem(self, espessura):
        """Desenha um ícone simplificado de engrenagem (círculo + 'dentes'), para a aba Configurações."""
        x, y, w, h = self.x, self.y, self.width, self.height
        centro_x, centro_y = x + w / 2, y + h / 2
        raio = min(w, h) * 0.30

        # Círculo externo principal da engrenagem.
        Line(circle=(centro_x, centro_y, raio), width=espessura)
        # Círculo pequeno no centro (o "furo" da engrenagem).
        Line(circle=(centro_x, centro_y, raio * 0.35), width=espessura)

        # Desenha 8 pequenos "dentes" ao redor do círculo, distribuídos a
        # cada 45 graus, usando seno/cosseno para calcular as posições.
        quantidade_dentes = 8
        for i in range(quantidade_dentes):
            angulo = math.radians(i * (360 / quantidade_dentes))
            x_interno = centro_x + raio * math.cos(angulo)
            y_interno = centro_y + raio * math.sin(angulo)
            x_externo = centro_x + (raio * 1.35) * math.cos(angulo)
            y_externo = centro_y + (raio * 1.35) * math.sin(angulo)
            Line(points=[x_interno, y_interno, x_externo, y_externo], width=espessura)

    def _desenhar_seta(self, espessura, para_baixo=True):
        """
        Desenha uma pequena seta triangular preenchida, apontando para
        baixo ou para cima, usada para indicar que um campo é clicável e
        abre uma lista de opções (seletores), ou o estado de um elemento
        expansível (cards da Home).

        Importante: a seta é desenhada como um TRIÂNGULO VETORIAL (usando
        ``Mesh``), e não como um caractere de texto (como "▾"). Isso evita
        um problema comum em apps Android: a fonte padrão do sistema pode
        não ter esse caractere Unicode específico, fazendo aparecer um
        quadrado com um "x" no lugar — exatamente o problema relatado pelo
        usuário ao testar o app já compilado no celular. Desenhando a seta
        como uma forma geométrica, ela sempre aparece corretamente, em
        qualquer aparelho, independente da fonte instalada.

        Parameters
        ----------
        espessura : float
            Não usado diretamente aqui (mantido por consistência de
            assinatura com os outros métodos "_desenhar_*"), já que o
            triângulo é preenchido (sem contorno).
        para_baixo : bool, optional
            Se True (padrão), desenha a seta apontando para baixo (▾).
            Se False, desenha apontando para cima (▴).
        """
        x, y, w, h = self.x, self.y, self.width, self.height
        if para_baixo:
            pontos = [x + w * 0.20, y + h * 0.65, x + w * 0.80, y + h * 0.65, x + w * 0.50, y + h * 0.30]
        else:
            pontos = [x + w * 0.20, y + h * 0.35, x + w * 0.80, y + h * 0.35, x + w * 0.50, y + h * 0.70]

        # O formato "vertices" do Mesh é uma sequência plana de (x, y, u, v)
        # para cada ponto — u,v são coordenadas de textura, deixadas como 0
        # porque não estamos usando nenhuma imagem/textura aqui.
        vertices = []
        for i in range(0, len(pontos), 2):
            vertices.extend([pontos[i], pontos[i + 1], 0, 0])

        Mesh(vertices=vertices, indices=[0, 1, 2], mode="triangle_fan")

    def _desenhar_lixeira(self, espessura):
        """Desenha um ícone simples de lixeira, usado no botão de excluir um registro de peso."""
        x, y, w, h = self.x, self.y, self.width, self.height
        Line(points=[
            x + w * 0.22, y + h * 0.78,
            x + w * 0.28, y + h * 0.15,
            x + w * 0.72, y + h * 0.15,
            x + w * 0.78, y + h * 0.78,
        ], width=espessura, close=True)
        Line(points=[x + w * 0.12, y + h * 0.78, x + w * 0.88, y + h * 0.78], width=espessura)
        Line(points=[x + w * 0.38, y + h * 0.78, x + w * 0.38, y + h * 0.88,
                     x + w * 0.62, y + h * 0.88, x + w * 0.62, y + h * 0.78], width=espessura)
        Line(points=[x + w * 0.40, y + h * 0.68, x + w * 0.42, y + h * 0.25], width=espessura * 0.8)
        Line(points=[x + w * 0.60, y + h * 0.68, x + w * 0.58, y + h * 0.25], width=espessura * 0.8)


def mostrar_popup(titulo, mensagem):
    """
    Exibe uma janela pop-up de aviso/confirmação totalmente customizada —
    SEM usar o título, separador ou fundo padrão do widget ``Popup`` do
    Kivy. Isso é necessário porque o estilo padrão do Kivy tem suas
    próprias cores internas para o título e o texto, que entraram em
    conflito com as cores do nosso tema e faziam o texto ficar invisível
    (texto escuro sobre fundo escuro, por exemplo).

    Em vez disso, este pop-up usa: ``title=""`` e ``separator_height=0``
    para desligar completamente o cabeçalho padrão do Kivy, e
    ``background=""`` para desligar a imagem de fundo padrão — sobrando
    apenas o nosso próprio conteúdo (construído com ``Label`` e cores
    explícitas do nosso tema), mais um botão "OK" para fechar.

    Parameters
    ----------
    titulo : str
        Título exibido no topo do pop-up (ex.: "Treino salvo!").
    mensagem : str
        Texto exibido no corpo do pop-up.
    """
    app = App.get_running_app()

    altura_popup = dp(170) if len(mensagem) < 110 else dp(240)

    # Container com TODO o conteúdo visual do pop-up, desenhado por nós —
    # incluindo o próprio fundo arredondado, no estilo do resto do app.
    conteudo = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(12))
    with conteudo.canvas.before:
        Color(*app.cor_superficie)
        fundo_popup = RoundedRectangle(pos=conteudo.pos, size=conteudo.size, radius=[dp(16)])
    conteudo.bind(
        pos=lambda inst, val: setattr(fundo_popup, "pos", val),
        size=lambda inst, val: setattr(fundo_popup, "size", val),
    )

    rotulo_titulo = Label(
        text=titulo,
        bold=True,
        font_size="17sp",
        color=app.cor_texto,
        size_hint_y=None,
        height=dp(28),
        halign="center",
        valign="middle",
    )
    rotulo_titulo.bind(size=lambda lbl, *_: setattr(lbl, "text_size", lbl.size))

    rotulo_mensagem = Label(
        text=mensagem,
        color=app.cor_texto_suave,
        halign="center",
        valign="middle",
        font_size="13sp",
    )
    # 'text_size' precisa ser amarrado ao tamanho do próprio Label para que
    # o texto quebre em várias linhas em vez de vazar para fora do pop-up.
    rotulo_mensagem.bind(size=lambda lbl, *_: setattr(lbl, "text_size", (lbl.width, None)))

    botao_ok = BotaoEstilizado(texto="OK", size_hint_y=None, height=dp(42))

    conteudo.add_widget(rotulo_titulo)
    conteudo.add_widget(rotulo_mensagem)
    conteudo.add_widget(botao_ok)

    popup = Popup(
        title="",                 # Desliga o título padrão do Kivy (usamos nosso próprio rótulo acima)
        separator_height=0,       # Desliga a linha separadora padrão
        background="",            # Desliga a imagem de fundo padrão do Kivy
        background_color=(0, 0, 0, 0),  # Deixa transparente — o fundo visível é o nosso RoundedRectangle
        content=conteudo,
        size_hint=(0.85, None),
        height=altura_popup,
        auto_dismiss=True,
    )
    botao_ok.bind(on_release=popup.dismiss)
    popup.open()


class BotaoEstilizado(ButtonBehavior, BoxLayout):
    """
    Botão customizado com cantos arredondados e cor de destaque (definida
    pelo tema atual), usado em todo o app no lugar do ``Button`` cinza e
    quadrado padrão do Kivy — deixando a interface com uma cara mais
    moderna e "de aplicativo mobile de verdade".

    Pode ser usado em dois estilos:
    - **Preenchido** (``selecionado=True``, o padrão): fundo colorido e
      texto branco. Usado nas ações principais (ex.: "Gerar treino").
    - **Contornado** (``selecionado=False``): só a borda é colorida, fundo
      transparente. Usado, por exemplo, no botão de tema que NÃO está
      selecionado atualmente, criando um efeito de "botão segmentado".

    Attributes
    ----------
    texto : str
        Texto exibido dentro do botão.
    selecionado : bool
        Controla o estilo preenchido (True) ou contornado (False).
    cor_personalizada : list[float]
        Cor RGBA customizada (ex.: vermelho para um botão de "excluir").
        Se vazia (padrão), o botão usa a cor de destaque do tema atual.
    """

    texto = StringProperty("")
    selecionado = BooleanProperty(True)
    cor_personalizada = ListProperty([])



class BottomNavItem(ButtonBehavior, BoxLayout):
    """
    Item clicável da barra de navegação inferior: um ícone (``IconWidget``)
    com um texto pequeno embaixo, exatamente como em apps mobile populares.

    A combinação ``ButtonBehavior + BoxLayout`` faz com que toda a área do
    item (ícone + texto) seja clicável, disparando o evento ``on_release``
    (usado no ``treino.kv`` para chamar ``app.trocar_tela(...)``).

    Attributes
    ----------
    icon_name : str
        Qual ícone exibir (ver ``IconWidget``).
    texto : str
        Texto exibido abaixo do ícone (ex.: "Home").
    active : bool
        Se True, o item é destacado com a cor de destaque do tema (indica
        que esta é a aba atualmente selecionada).
    """

    icon_name = StringProperty("home")
    texto = StringProperty("")
    active = BooleanProperty(False)


# ---------------------------------------------------------------------------
# GRÁFICO DE PESO (diário de peso, aba Configurações)
# ---------------------------------------------------------------------------

class GraficoPeso(FloatLayout):
    """
    Widget customizado que desenha um gráfico de linha mostrando a evolução
    do peso corporal ao longo do tempo, COM os eixos: a data de cada
    registro no eixo X (embaixo) e o valor do peso no eixo Y (na lateral
    esquerda) — usando apenas as primitivas de desenho nativas do Kivy
    (Canvas) mais alguns ``Label`` para os números/datas dos eixos, sem
    depender de bibliotecas externas de gráficos.
    """

    # Cada item de 'registros' é um dict {"peso_kg": float, "data_registro": str},
    # exatamente como retornado por ``BancoDeDados.listar_pesos``.
    registros = ListProperty([])

    def __init__(self, **kwargs):
        """Inicializa o widget, cria os rótulos dos eixos e liga os eventos de redesenho."""
        super().__init__(**kwargs)

        # Os 4 rótulos dos eixos (peso máximo/mínimo no eixo Y, primeira/
        # última data no eixo X) são criados uma única vez aqui e apenas
        # têm o texto e a posição atualizados a cada redesenho — assim
        # evitamos recriar widgets repetidamente.
        self.rotulo_peso_maximo = Label(size_hint=(None, None), size=(dp(56), dp(16)), font_size="10sp", halign="left", valign="middle")
        self.rotulo_peso_minimo = Label(size_hint=(None, None), size=(dp(56), dp(16)), font_size="10sp", halign="left", valign="middle")
        self.rotulo_data_inicio = Label(size_hint=(None, None), size=(dp(74), dp(16)), font_size="10sp", halign="left", valign="middle")
        self.rotulo_data_fim = Label(size_hint=(None, None), size=(dp(74), dp(16)), font_size="10sp", halign="right", valign="middle")

        for rotulo in (self.rotulo_peso_maximo, self.rotulo_peso_minimo, self.rotulo_data_inicio, self.rotulo_data_fim):
            rotulo.bind(size=lambda lbl, *_: setattr(lbl, "text_size", lbl.size))
            self.add_widget(rotulo)

        self.bind(pos=self._desenhar, size=self._desenhar, registros=self._desenhar)

    def definir_dados(self, registros):
        """
        Atualiza os dados exibidos no gráfico.

        Parameters
        ----------
        registros : list[dict]
            Lista de registros de peso, cada um com ``peso_kg`` e
            ``data_registro``, em ordem cronológica (do mais antigo para o
            mais recente) — exatamente como retornado por
            ``BancoDeDados.listar_pesos``.
        """
        self.registros = list(registros)

    def _desenhar(self, *args):
        """Redesenha a linha do gráfico e atualiza o texto/posição dos rótulos dos eixos."""
        self.canvas.before.clear()

        # Margens assimétricas: mais espaço à esquerda (para o valor do
        # peso) e embaixo (para a data), e um respiro menor nos outros lados.
        margem_esquerda = dp(42)
        margem_direita = dp(10)
        margem_topo = dp(12)
        margem_baixo = dp(20)

        with self.canvas.before:
            Color(0.5, 0.5, 0.5, 0.12)
            Rectangle(pos=self.pos, size=self.size)

            if len(self.registros) < 2:
                # Sem dados suficientes: limpa os rótulos e não desenha a linha.
                for rotulo in (self.rotulo_peso_maximo, self.rotulo_peso_minimo,
                               self.rotulo_data_inicio, self.rotulo_data_fim):
                    rotulo.text = ""
                return

            largura_util = self.width - margem_esquerda - margem_direita
            altura_util = self.height - margem_topo - margem_baixo

            pesos = [r["peso_kg"] for r in self.registros]
            minimo, maximo = min(pesos), max(pesos)
            faixa = (maximo - minimo) or 1.0

            # Linhas finas dos eixos (vertical à esquerda, horizontal embaixo).
            Color(0.6, 0.6, 0.65, 0.5)
            Line(points=[self.x + margem_esquerda, self.y + margem_baixo,
                         self.x + margem_esquerda, self.y + self.height - margem_topo], width=1)
            Line(points=[self.x + margem_esquerda, self.y + margem_baixo,
                         self.x + self.width - margem_direita, self.y + margem_baixo], width=1)

            pontos = []
            quantidade = len(self.registros)
            for indice, peso in enumerate(pesos):
                x = self.x + margem_esquerda + (indice / (quantidade - 1)) * largura_util
                proporcao = (peso - minimo) / faixa
                y = self.y + margem_baixo + proporcao * altura_util
                pontos.extend([x, y])

            Color(0.20, 0.60, 0.95, 1)
            Line(points=pontos, width=dp(2))

        # Atualiza o texto e a posição dos rótulos dos eixos.
        app = App.get_running_app()
        for rotulo in (self.rotulo_peso_maximo, self.rotulo_peso_minimo,
                       self.rotulo_data_inicio, self.rotulo_data_fim):
            rotulo.color = app.cor_texto_suave

        self.rotulo_peso_maximo.text = f"{maximo:.1f} kg"
        self.rotulo_peso_maximo.pos = (self.x + dp(2), self.y + self.height - margem_topo - dp(8))

        self.rotulo_peso_minimo.text = f"{minimo:.1f} kg"
        self.rotulo_peso_minimo.pos = (self.x + dp(2), self.y + margem_baixo - dp(2))

        self.rotulo_data_inicio.text = self.registros[0]["data_registro"]
        self.rotulo_data_inicio.pos = (self.x + margem_esquerda - dp(4), self.y + dp(2))

        self.rotulo_data_fim.text = self.registros[-1]["data_registro"]
        self.rotulo_data_fim.pos = (self.x + self.width - margem_direita - dp(74), self.y + dp(2))


class GraficoBarras(BoxLayout):
    """
    Widget customizado que desenha um gráfico de barras horizontais simples
    — usado na aba Configurações para mostrar quantos exercícios concluídos
    existem para cada músculo ("Músculos mais treinados"), sem depender de
    bibliotecas externas de gráficos.

    Cada "linha" do gráfico (nome do músculo + barra colorida + número) é um
    ``BoxLayout`` horizontal comum, e o ``GraficoBarras`` em si é um
    ``BoxLayout`` VERTICAL que simplesmente empilha essas linhas uma abaixo
    da outra — exatamente como as outras listas deste app (treinos salvos,
    exercícios, pesos). Isso é importante: uma versão anterior deste widget
    usava posicionamento livre (``FloatLayout``) com a posição de cada linha
    calculada manualmente em Python, o que causava um bug visual sério (as
    linhas apareciam "vazando" para fora da caixa, no canto da tela). Usar
    um ``BoxLayout`` comum elimina esse problema por completo, já que o
    próprio Kivy cuida de posicionar cada linha corretamente, com seu
    algoritmo de layout já testado e usado em todo o resto do app.
    """

    dados = ListProperty([])  # Lista de tuplas (nome_do_musculo, quantidade)

    def __init__(self, **kwargs):
        """Inicializa o widget como um BoxLayout vertical e religa o redesenho quando a largura muda."""
        kwargs.setdefault("orientation", "vertical")
        super().__init__(**kwargs)
        # A largura das barras é proporcional à largura disponível do
        # widget, então precisamos reconstruir as barras sempre que a
        # largura mudar (por exemplo, na primeira vez que a tela é
        # desenhada, quando a largura passa do valor padrão para a largura
        # real da tela do usuário).
        self.bind(width=self._renderizar)

    def definir_dados(self, dados):
        """
        Atualiza as barras exibidas no gráfico.

        Parameters
        ----------
        dados : list[tuple[str, int]]
            Lista de pares (nome_do_musculo, quantidade), já ordenada da
            maior para a menor quantidade (ver
            ``BancoDeDados.contar_exercicios_concluidos_por_musculo``).
        """
        self.dados = list(dados)
        self._renderizar()

    def _renderizar(self, *args):
        """Reconstrói todas as linhas do gráfico a partir de ``self.dados``."""
        app = App.get_running_app()
        self.clear_widgets()

        if not self.dados:
            self.size_hint_y = None
            self.height = dp(50)
            rotulo_vazio = Label(
                text="Marque exercícios como concluídos na aba Home\npara ver esse gráfico.",
                color=app.cor_texto_suave,
                font_size="12sp",
                halign="center",
                valign="middle",
                size_hint_y=None,
                height=dp(50),
            )
            rotulo_vazio.bind(size=lambda lbl, *_: setattr(lbl, "text_size", lbl.size))
            self.add_widget(rotulo_vazio)
            return

        maior_valor = max(valor for _, valor in self.dados) or 1
        altura_linha = dp(28)
        self.size_hint_y = None
        self.height = altura_linha * len(self.dados)

        # Largura disponível para a barra colorida em si, descontando o
        # espaço reservado para o nome do músculo (à esquerda) e o número
        # da quantidade (à direita).
        largura_total = self.width or dp(300)
        largura_disponivel_barra = max(dp(20), largura_total - dp(86) - dp(34) - dp(16))

        # Adiciona uma linha por músculo, na ordem em que já vêm em
        # 'self.dados' (do mais treinado para o menos treinado) — como o
        # BoxLayout é vertical, a primeira linha adicionada aparece no topo.
        for musculo, quantidade in self.dados:
            linha = BoxLayout(orientation="horizontal", size_hint_y=None, height=altura_linha - dp(4), spacing=dp(8))

            rotulo_nome = Label(
                text=musculo,
                color=app.cor_texto,
                font_size="12sp",
                size_hint_x=None,
                width=dp(86),
                halign="left",
                valign="middle",
            )
            rotulo_nome.bind(size=lambda lbl, *_: setattr(lbl, "text_size", lbl.size))

            # A largura da barra colorida é proporcional à quantidade deste
            # músculo em relação ao músculo mais treinado da lista.
            proporcao = quantidade / maior_valor
            largura_barra = max(dp(4), largura_disponivel_barra * proporcao)

            # 'espaco_barra' é um AnchorLayout só para centralizar
            # verticalmente a barrinha colorida dentro da altura da linha
            # (pos_hint só funciona dentro de FloatLayout/AnchorLayout).
            espaco_barra = AnchorLayout(size_hint_x=1, anchor_x="left", anchor_y="center")
            barra = BoxLayout(size_hint=(None, None), size=(largura_barra, dp(16)))
            with barra.canvas.before:
                Color(*app.cor_destaque)
                retangulo_barra = RoundedRectangle(pos=barra.pos, size=barra.size, radius=[dp(6)])
            # IMPORTANTE: 'rect=retangulo_barra' como argumento padrão da
            # lambda é essencial aqui. Sem isso, como o Python reutiliza a
            # mesma variável 'retangulo_barra' a cada repetição do loop
            # 'for', TODAS as barras acabariam atualizando o retângulo da
            # ÚLTIMA barra criada (e não o seu próprio) — esse era
            # exatamente o bug visto no print, em que só a última barra
            # aparecia (e ainda incorretamente).
            barra.bind(pos=lambda inst, val, rect=retangulo_barra: setattr(rect, "pos", val),
                       size=lambda inst, val, rect=retangulo_barra: setattr(rect, "size", val))
            espaco_barra.add_widget(barra)

            rotulo_valor = Label(
                text=str(quantidade),
                color=app.cor_texto_suave,
                font_size="12sp",
                size_hint_x=None,
                width=dp(28),
                halign="right",
                valign="middle",
            )
            rotulo_valor.bind(size=lambda lbl, *_: setattr(lbl, "text_size", lbl.size))

            linha.add_widget(rotulo_nome)
            linha.add_widget(espaco_barra)
            linha.add_widget(rotulo_valor)
            self.add_widget(linha)


# ---------------------------------------------------------------------------
# TELA: HOME (lista de treinos salvos, com cards expansíveis)
# ---------------------------------------------------------------------------

class TelaHome(Screen):
    """
    Classe Python associada à aba "Home" definida em ``treino.kv``.

    Responsável por listar todos os treinos salvos pelo usuário em forma de
    "cards" que podem ser expandidos com um toque, revelando a lista
    completa de exercícios (um abaixo do outro) e a quantidade de séries de
    cada um, além de um botão para excluir o treino.
    """

    def atualizar_lista(self):
        """
        Recarrega a lista de treinos salvos a partir do banco de dados e
        reconstrói os cards exibidos na tela.

        Este método também é chamado sempre que o tema (claro/escuro) é
        alterado, para garantir que a cor do texto dos cards já existentes
        seja atualizada — caso contrário, os cards criados antes da troca de
        tema manteriam a cor antiga e ficariam difíceis de ler.
        """
        app = App.get_running_app()
        container = self.ids.lista_treinos_home
        container.clear_widgets()

        treinos = app.banco.listar_treinos()

        if not treinos:
            rotulo_vazio = Label(
                text="Nenhum treino salvo ainda. Vá até a aba 'Novo Treino' para criar um!",
                color=app.cor_texto,
                size_hint_y=None,
                height=dp(60),
                halign="left",
                valign="top",
            )
            # Sem 'text_size', o Label NUNCA quebra linha — ele apenas
            # desenha o texto inteiro em uma única linha, do tamanho que
            # for preciso. Isso "parecia" funcionar no PC porque a janela
            # ali é mais larga, mas no celular (tela mais estreita) o texto
            # vazava para fora da tela — exatamente o bug visto no print.
            rotulo_vazio.bind(size=lambda lbl, *_: setattr(lbl, "text_size", (lbl.width, None)))
            container.add_widget(rotulo_vazio)
            return

        for treino in treinos:
            container.add_widget(self._criar_card_treino(treino, app))

    def _criar_card_treino(self, treino, app):
        """
        Monta o "card" visual de um único treino salvo: um cabeçalho
        clicável (título + data + seta indicadora) que, ao ser tocado,
        expande ou recolhe a lista de exercícios daquele treino.

        Parameters
        ----------
        treino : dict
            Dicionário do treino, no formato retornado por
            ``BancoDeDados.listar_treinos``.
        app : TreinoApp
            Instância do app em execução (para acessar cores do tema e o banco).

        Returns
        -------
        BoxLayout
            Widget pronto para ser adicionado à lista da tela Home.
        """
        # 'cartao' é o container externo do card. Sua altura é amarrada
        # (via bind) à 'minimum_height', que o Kivy calcula automaticamente
        # somando a altura de todos os filhos — assim, o card cresce/encolhe
        # sozinho conforme o cabeçalho e o corpo (exercícios) mudam de altura.
        cartao = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2), padding=[0, dp(4)])
        cartao.bind(minimum_height=lambda inst, valor: setattr(inst, "height", valor))

        # Fundo do card com cantos arredondados (cor "superfície" do tema) e
        # uma sombra leve por baixo (retângulo arredondado escuro e
        # translúcido, desenhado um pouco mais abaixo), para dar uma
        # sensação sutil de profundidade/elevação — bem diferente do
        # antigo fundo cinza chapado e quadrado.
        with cartao.canvas.before:
            Color(0, 0, 0, 0.18)
            sombra_rect = RoundedRectangle(pos=cartao.pos, size=cartao.size, radius=[dp(14)])
            Color(*app.cor_superficie)
            fundo_rect = RoundedRectangle(pos=cartao.pos, size=cartao.size, radius=[dp(14)])

        def _atualizar_fundo(inst, valor):
            # Reposiciona a sombra com um pequeno deslocamento para baixo,
            # e o fundo principal exatamente sobre os limites do card.
            sombra_rect.pos = (inst.x, inst.y - dp(2))
            sombra_rect.size = inst.size
            fundo_rect.pos = inst.pos
            fundo_rect.size = inst.size

        cartao.bind(pos=_atualizar_fundo, size=_atualizar_fundo)

        # --- Cabeçalho clicável (título + data + seta) ---
        # Usamos um único ``Button`` real do Kivy como o cabeçalho inteiro
        # — não duas ou três camadas de widgets sobrepostos. Isso elimina
        # por completo qualquer ambiguidade sobre "qual parte responde ao
        # toque": a área clicável É exatamente a área visível do botão, do
        # início ao fim, sem exceção. O ícone da seta é apenas um detalhe
        # visual "pendurado" dentro do botão (não é clicável por si só, e
        # não precisa ser — o botão inteiro já responde a qualquer toque).
        cabecalho = Button(
            text=f"[b]{treino['titulo']}[/b]\n{treino['data_criacao']}",
            markup=True,
            color=app.cor_texto,
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(56),
            padding=(dp(8), 0),
        )
        # 'text_size' precisa considerar uma margem à direita, para o texto
        # não passar por baixo do ícone da seta.
        cabecalho.bind(size=lambda inst, *_: setattr(inst, "text_size", (inst.width - dp(40), inst.height)))
        cabecalho.bind(on_release=lambda *_: self._alternar_expansao(corpo, seta))

        seta = IconWidget(
            icon_name="seta_baixo",
            cor=app.cor_texto,
            size_hint=(None, None),
            size=(dp(20), dp(20)),
            pos_hint={"right": 0.96, "center_y": 0.5},
        )
        # Adiciona o ícone da seta DENTRO do próprio botão (apenas como
        # decoração visual — Button, por ser um Widget, aceita widgets
        # filhos normalmente, mesmo que isso não seja o uso mais comum).
        cabecalho.add_widget(seta)

        # --- Corpo expansível (lista de exercícios + botão excluir) ---
        # Começa "fechado": altura 0 e invisível, sem reagir a toques.
        corpo = BoxLayout(orientation="vertical", size_hint_y=None, height=0, opacity=0, disabled=True, padding=(dp(16), dp(4)))


        for indice, ex in enumerate(treino["exercicios"], start=1):
            # Cada exercício agora é uma linha horizontal com uma caixinha
            # de marcar ("já fiz esse exercício?") à esquerda e o texto do
            # exercício à direita. Marcar a caixinha persiste imediatamente
            # no banco de dados (campo "concluido" daquele exercício) e
            # alimenta o gráfico de "músculos mais treinados" da aba
            # Configurações.
            linha = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(34), spacing=dp(6))

            caixinha = CheckBox(
                active=bool(ex.get("concluido", False)),
                size_hint=(None, None),
                size=(dp(28), dp(28)),
                color=app.cor_destaque,
            )

            cor_suave_hex = _hex(app.cor_texto_suave)
            texto_linha = (
                f"{indice}. [b]{ex['exercicio']}[/b]  "
                f"[color={cor_suave_hex}]—  {ex['series']} séries[/color]"
            )
            rotulo_exercicio = Label(
                text=texto_linha,
                markup=True,
                color=app.cor_texto,
                halign="left",
                valign="middle",
            )
            rotulo_exercicio.bind(size=lambda lbl, *_: setattr(lbl, "text_size", lbl.size))

            # 'on_active' é disparado sempre que o usuário marca/desmarca a
            # caixinha. Usamos índice (posição na lista) para saber qual
            # exercício atualizar dentro da lista salva daquele treino.
            caixinha.bind(active=lambda inst, valor, idx=indice - 1: self._marcar_concluido(treino, idx, valor, app))

            linha.add_widget(caixinha)
            linha.add_widget(rotulo_exercicio)
            corpo.add_widget(linha)

        botao_excluir = BotaoEstilizado(
            texto="Excluir treino",
            size_hint_y=None,
            height=dp(40),
            cor_personalizada=(0.86, 0.32, 0.32, 1),  # Vermelho suave, indicando uma ação destrutiva
        )
        botao_excluir.bind(on_release=lambda *_: self._excluir(treino["id"], app))
        corpo.add_widget(botao_excluir)

        cartao.add_widget(cabecalho)
        cartao.add_widget(corpo)
        return cartao

    def _alternar_expansao(self, corpo, seta):
        """
        Expande o corpo do card (mostrando os exercícios) se ele estiver
        recolhido, ou recolhe se ele já estiver expandido.

        Parameters
        ----------
        corpo : BoxLayout
            O container com a lista de exercícios daquele treino.
        seta : IconWidget
            O ícone de seta indicador (▾ recolhido / ▴ expandido), cujo
            ``icon_name`` é trocado para refletir visualmente o novo estado.
        """
        esta_expandido = corpo.height > 0

        if esta_expandido:
            # Recolhe: altura zero, invisível e sem capturar toques.
            corpo.height = 0
            corpo.opacity = 0
            corpo.disabled = True
            seta.icon_name = "seta_baixo"
        else:
            # Expande: usa 'minimum_height' (já calculado a partir dos
            # filhos adicionados) como a altura final do corpo.
            corpo.height = corpo.minimum_height
            corpo.opacity = 1
            corpo.disabled = False
            seta.icon_name = "seta_cima"

    def _marcar_concluido(self, treino, indice_exercicio, concluido, app):
        """
        Atualiza o campo "concluido" de um exercício específico (dentro de
        um treino salvo) e persiste essa mudança no banco de dados.

        Esse dado é usado depois pelo gráfico "Músculos mais treinados" na
        aba Configurações, que conta quantos exercícios concluídos existem
        para cada músculo, em todos os treinos salvos.

        Parameters
        ----------
        treino : dict
            O dicionário do treino (como retornado por ``listar_treinos``),
            cuja lista de exercícios será atualizada em memória e no banco.
        indice_exercicio : int
            Posição do exercício dentro da lista ``treino["exercicios"]``.
        concluido : bool
            Novo valor marcado pelo usuário (True = concluído).
        app : TreinoApp
            Instância do app em execução (para acessar o banco de dados).
        """
        treino["exercicios"][indice_exercicio]["concluido"] = concluido
        app.banco.atualizar_exercicios_treino(treino["id"], treino["exercicios"])

    def _excluir(self, treino_id, app):
        """Exclui um treino do banco de dados e atualiza a lista exibida na tela."""
        app.banco.excluir_treino(treino_id)
        self.atualizar_lista()


# Pequena classe auxiliar: um BoxLayout que também é clicável (dispara
# 'on_release'). É usada como cabeçalho dos cards de treino na Home, para
# que toda aquela área (não só um botão pequeno) responda ao toque.
# Pequena classe auxiliar: um AnchorLayout clicável, usado para botões que
# contêm apenas um ícone (sem texto), como o botão de excluir um registro
# de peso. O AnchorLayout garante que o ícone fique centralizado dentro da
# área clicável, em vez de "colado" em um canto.
class BotaoIcone(ButtonBehavior, FloatLayout):
    """AnchorLayout clicável usado para botões que contêm apenas um ícone centralizado, sem texto."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ButtonBehavior_BoxLayout(ButtonBehavior, BoxLayout):
    """BoxLayout clicável (mistura ``ButtonBehavior`` com ``BoxLayout``), usado como cabeçalho expansível dos cards de treino."""
    pass


# ---------------------------------------------------------------------------
# TELA: EXERCÍCIOS
# ---------------------------------------------------------------------------

class TelaExercicios(Screen):
    """
    Classe Python associada à aba "Exercícios" definida em ``treino.kv``.

    Mostra todos os exercícios do banco de dados, organizados por grupo
    muscular e nível de dificuldade, com filtros opcionais.
    """

    def preencher_filtros(self):
        """Preenche o Spinner de grupos musculares com os grupos disponíveis no CSV."""
        app = App.get_running_app()
        grupos = sorted({ex["grupo_muscular"] for ex in app.exercicios})
        self.ids.filtro_grupo_exercicios.values = ["Todos os grupos"] + grupos

    def aplicar_filtros(self):
        """
        Lê os filtros selecionados pelo usuário (grupo muscular e nível) e
        atualiza a lista de exercícios exibida na tela.

        Também é chamado ao trocar de tema, para que a cor do texto de cada
        linha de exercício seja redesenhada com a cor correta.
        """
        app = App.get_running_app()
        grupo_selecionado = self.ids.filtro_grupo_exercicios.text
        nivel_selecionado = self.ids.filtro_nivel_exercicios.text

        exercicios_filtrados = app.exercicios
        if grupo_selecionado not in ("", "Todos os grupos"):
            exercicios_filtrados = [
                ex for ex in exercicios_filtrados if ex["grupo_muscular"] == grupo_selecionado
            ]
        if nivel_selecionado not in ("", "Todos os níveis"):
            exercicios_filtrados = [
                ex for ex in exercicios_filtrados if ex["nivel"] == nivel_selecionado
            ]

        self._renderizar_lista(exercicios_filtrados, app)

    def _renderizar_lista(self, lista_exercicios, app):
        """Desenha a lista de exercícios filtrados na tela, agrupados por grupo muscular."""
        container = self.ids.lista_exercicios
        container.clear_widgets()

        grupos_ordenados = sorted({ex["grupo_muscular"] for ex in lista_exercicios})

        for grupo in grupos_ordenados:
            container.add_widget(self._criar_chip_grupo(grupo, app))
            for ex in [e for e in lista_exercicios if e["grupo_muscular"] == grupo]:
                # O nome do exercício fica em destaque (negrito, cor principal do
                # texto) e os detalhes (músculo/nível/equipamento) ficam em uma
                # cor mais suave, criando uma hierarquia visual mais clara do
                # que uma única linha de texto plano e uniforme.
                cor_texto_hex = _hex(app.cor_texto)
                cor_suave_hex = _hex(app.cor_texto_suave)
                texto = (
                    f"[b][color={cor_texto_hex}]{ex['exercicio']}[/color][/b]\n"
                    f"[color={cor_suave_hex}]{ex['musculo_principal']} • {ex['nivel']} • {ex['equipamento']}[/color]"
                )
                rotulo = Label(
                    text=texto,
                    markup=True,
                    color=app.cor_texto,
                    size_hint_y=None,
                    height=dp(42),
                    halign="left",
                    valign="middle",
                )
                rotulo.bind(size=lambda lbl, *_: setattr(lbl, "text_size", lbl.size))
                container.add_widget(rotulo)

    def _criar_chip_grupo(self, nome_grupo, app):
        """
        Cria um "chip" (etiqueta arredondada) com o nome do grupo muscular,
        usado como cabeçalho visual antes da lista de exercícios daquele
        grupo — uma alternativa mais amigável do que um texto em negrito solto.

        Parameters
        ----------
        nome_grupo : str
            Nome do grupo muscular (ex.: "Pernas").
        app : TreinoApp
            Instância do app em execução (para acessar as cores do tema).

        Returns
        -------
        BoxLayout
            O chip já pronto para ser adicionado à lista de exercícios.
        """
        chip = BoxLayout(size_hint_y=None, height=dp(30), size_hint_x=None, padding=[dp(12), 0])
        chip.width = dp(18) * len(nome_grupo) + dp(24)  # Largura aproximada conforme o tamanho do texto

        with chip.canvas.before:
            # Fundo do chip: a própria cor de destaque do tema, mas bem
            # translúcida, para criar um "tom sobre tom" suave e elegante.
            Color(app.cor_destaque[0], app.cor_destaque[1], app.cor_destaque[2], 0.16)
            retangulo_chip = RoundedRectangle(pos=chip.pos, size=chip.size, radius=[dp(15)])
        chip.bind(
            pos=lambda inst, val: setattr(retangulo_chip, "pos", val),
            size=lambda inst, val: setattr(retangulo_chip, "size", val),
        )

        chip.add_widget(Label(
            text=nome_grupo,
            bold=True,
            color=app.cor_destaque,
            font_size="13sp",
        ))
        return chip


# ---------------------------------------------------------------------------
# TELA: MONTAR NOVO TREINO
# ---------------------------------------------------------------------------

class TelaNovoTreino(Screen):
    """
    Classe Python associada à aba "Montar novo treino" definida em ``treino.kv``.

    Controla o formulário em 3 etapas (tipo de treino -> nível -> grupo
    muscular específico) e chama as funções de ``workout_generator`` para
    sortear os exercícios, exibindo o resultado e permitindo salvá-lo.
    """

    def atualizar_visibilidade_grupo(self):
        """
        Mostra ou esconde o campo de "grupo muscular específico" (etapa 3),
        já que ele só faz sentido quando o tipo de treino escolhido é
        "Grupo muscular" (nos tipos A/B e Full body esse campo é ignorado).

        Toda a visibilidade (altura do campo, opacidade do texto/seta e se
        ele responde a toques) é controlada aqui pelo Python, em vez de
        dentro do arquivo .kv, porque o Kivy resolve as expressões do
        ``canvas.before`` antes mesmo de os widgets-filhos (a Spinner)
        existirem — então uma referência a "spinner_grupo_treino" dentro do
        canvas geraria um erro ``NameError`` ao iniciar o app.
        """
        tipo = self.ids.spinner_tipo_treino.text
        mostrar = (tipo == "Grupo muscular")

        # Esconde tanto o rótulo "3. Grupo muscular específico" quanto o
        # campo em si (caixa arredondada + spinner + seta), ajustando a
        # altura para 0 quando escondido, para não deixar um vão vazio.
        self.ids.label_grupo_treino.opacity = 1 if mostrar else 0
        self.ids.label_grupo_treino.height = dp(22) if mostrar else 0

        self.ids.caixa_grupo_treino.height = dp(46) if mostrar else 0
        self.ids.caixa_grupo_treino.opacity = 1 if mostrar else 0

        self.ids.spinner_grupo_treino.opacity = 1 if mostrar else 0
        self.ids.spinner_grupo_treino.disabled = not mostrar

        self.ids.seta_grupo_treino.opacity = 1 if mostrar else 0

    def gerar_treino(self):
        """Lê as escolhas do usuário, gera o treino e exibe o resultado na tela."""
        app = App.get_running_app()
        tipo = self.ids.spinner_tipo_treino.text
        nivel = self.ids.spinner_nivel_treino.text
        grupo = self.ids.spinner_grupo_treino.text

        if tipo == "Grupo muscular":
            resultado = gerar_treino_grupo_muscular(app.exercicios, grupo, nivel)
            titulo = f"Treino de {grupo} - {nivel}"
            dados_para_salvar = {
                "tipo": "grupo_muscular",
                "grupo_muscular": grupo,
                "exercicios": resultado["exercicios"],
            }
            blocos = [("", resultado["exercicios"])]

        elif tipo == "Treino A/B (superior/inferior)":
            resultado = gerar_treino_ab(app.exercicios, nivel)
            titulo = f"Treino A/B - {nivel}"
            dados_para_salvar = {
                "tipo": "ab",
                "grupo_muscular": None,
                "exercicios": resultado["dia_a"] + resultado["dia_b"],
            }
            blocos = [("Dia A (Superiores)", resultado["dia_a"]), ("Dia B (Inferiores)", resultado["dia_b"])]

        else:  # "Full body (corpo todo)"
            resultado = gerar_treino_full_body(app.exercicios, nivel)
            titulo = f"Treino Full Body - {nivel}"
            dados_para_salvar = {
                "tipo": "full_body",
                "grupo_muscular": None,
                "exercicios": resultado["exercicios"],
            }
            blocos = [("", resultado["exercicios"])]

        self._ultimo_resultado = dados_para_salvar
        self._ultimo_titulo = titulo
        self._renderizar_resultado(titulo, blocos, resultado.get("avisos", []), app)

    def _renderizar_resultado(self, titulo, blocos, avisos, app):
        """Desenha o treino recém-gerado na tela, com título, avisos, exercícios e botão salvar."""
        container = self.ids.resultado_novo_treino
        container.clear_widgets()

        container.add_widget(Label(
            text=f"[b]{titulo}[/b]", markup=True, color=app.cor_destaque,
            size_hint_y=None, height=dp(30),
        ))

        for aviso in avisos:
            rotulo_aviso = Label(
                text=f"⚠ {aviso}", color=(0.9, 0.6, 0.1, 1),
                size_hint_y=None, height=dp(40), halign="left",
            )
            rotulo_aviso.bind(size=lambda lbl, *_: setattr(lbl, "text_size", lbl.size))
            container.add_widget(rotulo_aviso)

        for nome_bloco, exercicios_bloco in blocos:
            if nome_bloco:
                container.add_widget(Label(
                    text=f"[b]{nome_bloco}[/b]", markup=True, color=app.cor_texto,
                    size_hint_y=None, height=dp(26),
                ))
            for indice, ex in enumerate(exercicios_bloco, start=1):
                cor_suave_hex = _hex(app.cor_texto_suave)
                texto = (
                    f"{indice}. [b]{ex['exercicio']}[/b]\n"
                    f"[color={cor_suave_hex}]{ex['series']} séries • {ex['musculo_principal']}[/color]"
                )
                rotulo = Label(
                    text=texto, markup=True, color=app.cor_texto,
                    size_hint_y=None, height=dp(40), halign="left", valign="middle",
                )
                rotulo.bind(size=lambda lbl, *_: setattr(lbl, "text_size", lbl.size))
                container.add_widget(rotulo)

        botao_salvar = BotaoEstilizado(texto="Salvar este treino", size_hint_y=None, height=dp(44))
        botao_salvar.bind(on_release=lambda *_: self._salvar(app))
        container.add_widget(botao_salvar)

    def _salvar(self, app):
        """Persiste o último treino gerado no banco SQLite e mostra um pop-up de confirmação."""
        dados = self._ultimo_resultado

        # Adiciona o campo "concluido" (inicialmente False) em cada
        # exercício, usado depois para o usuário marcar quais exercícios já
        # realizou de fato (checkbox na aba Home), alimentando o gráfico de
        # "músculos mais treinados" na aba Configurações.
        for exercicio in dados["exercicios"]:
            exercicio["concluido"] = False

        app.banco.salvar_treino(
            titulo=self._ultimo_titulo,
            tipo=dados["tipo"],
            nivel=self.ids.spinner_nivel_treino.text,
            grupo_muscular=dados["grupo_muscular"],
            lista_exercicios=dados["exercicios"],
            data_criacao=datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        )
        mostrar_popup("Treino salvo!", "Seu treino foi salvo. Confira na aba Home.")
        app.root.ids.tela_home.atualizar_lista()


# ---------------------------------------------------------------------------
# TELA: CONFIGURAÇÕES
# ---------------------------------------------------------------------------

class TelaConfiguracoes(Screen):
    """
    Classe Python associada à aba "Configurações" definida em ``treino.kv``.

    Controla:
    - O diário de peso corporal: registro, gráfico de linha com eixos
      (data x peso) e uma lista dos registros com opção de excluir
      qualquer um deles;
    - O gráfico "Músculos mais treinados", construído a partir dos
      exercícios marcados como concluídos na aba Home;
    - A troca de tema do aplicativo (claro/escuro).
    """

    def on_pre_enter(self, *args):
        """
        Chamado automaticamente pelo Kivy um pouco antes desta aba ficar
        visível na tela (evento padrão de qualquer ``Screen``).

        Usado aqui para sempre recarregar os dados mais recentes — o
        gráfico de peso, a lista de pesos e o gráfico de músculos mais
        treinados —, já que esses dados podem ter mudado em outra aba (por
        exemplo, o usuário marcou um exercício como concluído na Home).
        """
        self.atualizar_grafico()
        self.atualizar_lista_pesos()
        self.atualizar_grafico_musculos()

    def registrar_peso(self):
        """Lê o peso digitado, valida, salva no banco e atualiza o gráfico e a lista."""
        app = App.get_running_app()
        texto_peso = self.ids.campo_peso.text.strip()

        if not texto_peso:
            return

        try:
            peso = float(texto_peso)
        except ValueError:
            return

        app.banco.registrar_peso(
            peso_kg=peso,
            data_registro=datetime.datetime.now().strftime("%d/%m/%Y"),
        )
        self.ids.campo_peso.text = ""
        self.atualizar_grafico()
        self.atualizar_lista_pesos()

    def atualizar_grafico(self):
        """Recarrega os registros de peso do banco e atualiza o gráfico de linha (com eixos)."""
        app = App.get_running_app()
        registros = app.banco.listar_pesos()
        self.ids.grafico_peso.definir_dados(registros)

    def atualizar_lista_pesos(self):
        """
        Recarrega e redesenha a lista de registros de peso (mais recente
        primeiro), cada um com um botão de excluir — permitindo ao usuário
        remover lançamentos feitos por engano.
        """
        app = App.get_running_app()
        container = self.ids.lista_pesos
        container.clear_widgets()

        registros = list(reversed(app.banco.listar_pesos()))  # Mais recente primeiro

        if not registros:
            rotulo_vazio = Label(
                text="Nenhum peso registrado ainda.",
                color=app.cor_texto_suave,
                size_hint_y=None,
                height=dp(30),
                font_size="12sp",
                halign="left",
                valign="middle",
            )
            rotulo_vazio.bind(size=lambda lbl, *_: setattr(lbl, "text_size", (lbl.width, None)))
            container.add_widget(rotulo_vazio)
            return

        for registro in registros:
            linha = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(34), spacing=dp(8))

            rotulo = Label(
                text=f"{registro['data_registro']}  —  {registro['peso_kg']:.1f} kg",
                color=app.cor_texto,
                halign="left",
                valign="middle",
            )
            rotulo.bind(size=lambda lbl, *_: setattr(lbl, "text_size", lbl.size))

            botao_excluir = BotaoIcone(size_hint=(None, None), size=(dp(34), dp(34)))
            icone_lixeira = IconWidget(
                icon_name="lixeira",
                cor=(0.86, 0.32, 0.32, 1),
                size_hint=(None, None),
                size=(dp(20), dp(20)),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
            )
            botao_excluir.add_widget(icone_lixeira)
            botao_excluir.bind(on_release=lambda *_, rid=registro["id"]: self._excluir_peso(rid, app))

            linha.add_widget(rotulo)
            linha.add_widget(botao_excluir)
            container.add_widget(linha)

    def _excluir_peso(self, peso_id, app):
        """Remove um registro de peso do banco e atualiza o gráfico e a lista na tela."""
        app.banco.excluir_peso(peso_id)
        self.atualizar_grafico()
        self.atualizar_lista_pesos()

    def atualizar_grafico_musculos(self):
        """
        Recarrega as contagens de exercícios concluídos por músculo (a
        partir de todos os treinos salvos) e atualiza o gráfico de barras
        "Músculos mais treinados".
        """
        app = App.get_running_app()
        contagens = app.banco.contar_exercicios_concluidos_por_musculo()
        self.ids.grafico_musculos.definir_dados(contagens)


# ---------------------------------------------------------------------------
# WIDGET RAIZ E APP PRINCIPAL
# ---------------------------------------------------------------------------

class RootLayout(BoxLayout):
    """Widget raiz de toda a interface (barra de título + ScreenManager + barra de navegação inferior)."""
    pass


# ---------------------------------------------------------------------------
# REGISTRO DAS CLASSES CUSTOMIZADAS NO FACTORY DO KIVY
# ---------------------------------------------------------------------------
# O arquivo treino.kv referencia várias classes Python definidas neste
# arquivo (ex.: a tag "BottomNavItem:" dentro do .kv precisa saber qual
# classe Python instanciar). Em alguns casos — especialmente classes que
# usam herança múltipla, como as que combinam ``ButtonBehavior`` com um
# Layout (``BottomNavItem``, ``BotaoEstilizado``, ``ButtonBehavior_BoxLayout``)
# — o mecanismo automático de descoberta de classes do Kivy pode não
# conseguir localizá-las, resultando no erro
# "kivy.factory.FactoryException: Unknown class <...>" ao iniciar o app.
#
# Para evitar esse problema de forma definitiva, registramos manualmente
# TODAS as classes customizadas usadas no arquivo .kv. Isso garante que o
# Kivy sempre saiba qual classe Python instanciar para cada tag usada no
# arquivo de layout, independente desse comportamento automático.
Factory.register("IconWidget", cls=IconWidget)
Factory.register("BotaoEstilizado", cls=BotaoEstilizado)
Factory.register("BottomNavItem", cls=BottomNavItem)
Factory.register("BotaoIcone", cls=BotaoIcone)
Factory.register("GraficoPeso", cls=GraficoPeso)
Factory.register("GraficoBarras", cls=GraficoBarras)
Factory.register("TelaHome", cls=TelaHome)
Factory.register("ButtonBehavior_BoxLayout", cls=ButtonBehavior_BoxLayout)
Factory.register("TelaExercicios", cls=TelaExercicios)
Factory.register("TelaNovoTreino", cls=TelaNovoTreino)
Factory.register("TelaConfiguracoes", cls=TelaConfiguracoes)
Factory.register("RootLayout", cls=RootLayout)


class TreinoApp(App):
    """
    Classe principal do aplicativo Kivy.

    Responsável por:
    - Inicializar o banco de dados SQLite (criando-o se necessário);
    - Carregar a lista de exercícios a partir do arquivo CSV;
    - Manter as propriedades de cor do tema atual (claro/escuro);
    - Controlar qual tela está ativa (``tela_atual``) e trocar entre elas
      através da barra de navegação inferior;
    - Disparar a atualização inicial de cada aba quando o app é aberto.
    """

    cor_fundo = ListProperty(TEMAS["claro"]["fundo"])
    cor_superficie = ListProperty(TEMAS["claro"]["superficie"])
    cor_texto = ListProperty(TEMAS["claro"]["texto"])
    cor_texto_suave = ListProperty(TEMAS["claro"]["texto_suave"])
    cor_destaque = ListProperty(TEMAS["claro"]["destaque"])
    cor_destaque_escura = ListProperty(TEMAS["claro"]["destaque_escura"])
    cor_barra_nav = ListProperty(TEMAS["claro"]["barra_nav"])
    cor_nav_inativo = ListProperty(TEMAS["claro"]["nav_inativo"])
    cor_borda = ListProperty(TEMAS["claro"]["borda"])

    # Nome do tema atualmente ativo ("claro" ou "escuro"), usado para saber
    # qual dos dois botões de tema na aba Configurações deve aparecer
    # "selecionado" (preenchido) e qual deve aparecer só com a borda.
    nome_tema = StringProperty("claro")

    # Nome da tela atualmente exibida (usado pela barra de navegação
    # inferior para saber qual ícone deve aparecer "ativo"/destacado).
    tela_atual = StringProperty("home")

    def build(self):
        """
        Método chamado automaticamente pelo Kivy ao iniciar o app.

        Returns
        -------
        RootLayout
            O widget raiz de toda a interface, carregado a partir do
            arquivo ``treino.kv``.
        """
        caminho_db = os.path.join(self.user_data_dir, "treino.db")
        self.banco = BancoDeDados(caminho_db)

        caminho_csv = os.path.join(os.path.dirname(__file__), "data", "exercicios.csv")
        self.exercicios = carregar_exercicios(caminho_csv)

        tema_salvo = self.banco.obter_config("tema", valor_padrao="claro")
        self.definir_tema(tema_salvo, salvar=False)

        raiz = RootLayout()
        return raiz

    def on_start(self):
        """Popula as abas com os dados iniciais, já que isso só pode ser feito depois que os widgets existem."""
        self.root.ids.tela_home.atualizar_lista()
        self.root.ids.tela_exercicios.preencher_filtros()
        self.root.ids.tela_exercicios.aplicar_filtros()
        self.root.ids.tela_configuracoes.atualizar_grafico()
        self.root.ids.tela_configuracoes.atualizar_lista_pesos()
        self.root.ids.tela_configuracoes.atualizar_grafico_musculos()

        # Mostra o aviso de saúde toda vez que o app é aberto. O pequeno
        # atraso (Clock.schedule_once) garante que o pop-up apareça DEPOIS
        # que a tela inicial já está visível, em vez de aparecer durante a
        # transição de abertura do app (o que poderia parecer um "flash"
        # estranho ou até não aparecer corretamente em alguns aparelhos).
        Clock.schedule_once(lambda *_: self._mostrar_aviso_saude(), 0.3)

    def _mostrar_aviso_saude(self):
        """
        Exibe um pop-up de aviso informando que o app foi desenvolvido sem
        consulta a profissionais de educação física, fisioterapia ou
        medicina — importante para deixar claro ao usuário que os treinos
        sugeridos são apenas um ponto de partida, e não substituem
        orientação profissional especializada.
        """
        mostrar_popup(
            "Aviso importante",
            "Este aplicativo foi desenvolvido de forma independente, sem "
            "consulta a profissionais de educação física, fisioterapia ou "
            "medicina. Os treinos sugeridos têm caráter apenas "
            "informativo. Consulte um profissional qualificado antes de "
            "iniciar qualquer programa de exercícios.",
        )

    def trocar_tela(self, nome_tela):
        """
        Troca a tela exibida no ``ScreenManager`` e atualiza qual ícone da
        barra de navegação inferior deve aparecer destacado.

        Parameters
        ----------
        nome_tela : str
            Nome da tela de destino: "home", "exercicios", "novo_treino" ou
            "configuracoes" (deve corresponder ao atributo ``name`` definido
            para cada ``Screen`` em ``treino.kv``).
        """
        self.root.ids.gerenciador_telas.current = nome_tela
        self.tela_atual = nome_tela

    def definir_tema(self, nome_tema, salvar=True):
        """
        Troca o tema visual do app (claro ou escuro) e, opcionalmente, salva
        essa preferência no banco de dados.

        Além de mudar as cores (que a maioria dos widgets do ``treino.kv``
        já segue automaticamente, pois são "amarradas" a ``app.cor_*``),
        este método também força a reconstrução dos cards da Home e da
        lista de Exercícios — que são montados dinamicamente em Python, e
        por isso não acompanhariam a troca de tema automaticamente.

        Parameters
        ----------
        nome_tema : str
            "claro" ou "escuro".
        salvar : bool, optional
            Se True (padrão), grava a escolha no banco de dados.
        """
        tema = TEMAS.get(nome_tema, TEMAS["claro"])
        self.cor_fundo = tema["fundo"]
        self.cor_superficie = tema["superficie"]
        self.cor_texto = tema["texto"]
        self.cor_texto_suave = tema["texto_suave"]
        self.cor_destaque = tema["destaque"]
        self.cor_destaque_escura = tema["destaque_escura"]
        self.cor_barra_nav = tema["barra_nav"]
        self.cor_nav_inativo = tema["nav_inativo"]
        self.cor_borda = tema["borda"]
        self.nome_tema = nome_tema

        if salvar:
            self.banco.definir_config("tema", nome_tema)

        # Reconstrói os widgets criados dinamicamente em Python, para que a
        # cor do texto deles também seja atualizada (e fique legível no
        # tema escuro). Só faz isso se o app já tiver terminado de montar a
        # tela (ou seja, não durante a primeira chamada dentro de build()).
        if self.root is not None and "tela_home" in self.root.ids:
            self.root.ids.tela_home.atualizar_lista()
            self.root.ids.tela_exercicios.aplicar_filtros()

    def on_stop(self):
        """Chamado automaticamente quando o app é encerrado; fecha a conexão com o banco."""
        self.banco.fechar()


if __name__ == "__main__":
    # Permite executar o app diretamente no PC com "python main.py", sem
    # precisar empacotar nada, para testes rápidos durante o desenvolvimento.
    TreinoApp().run()
