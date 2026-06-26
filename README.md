# Monta Treino 🏋️

Aplicativo mobile (Android) para montagem de treinos de academia, escrito
**100% em Python**, usando o framework **Kivy** para a interface gráfica e
**SQLite** (biblioteca padrão do Python) para armazenamento local.

O app monta treinos aleatórios a partir de um banco de exercícios em CSV,
de acordo com o tipo de treino, nível de dificuldade e grupo muscular
escolhidos pelo usuário.

---

## ⚠️ Sobre o APK — leia antes de tudo

Este pacote contém o **código-fonte completo e funcional** do app, pronto
para gerar o `.apk`. **O `.apk` em si não está incluído** neste pacote,
porque a geração dele exige o **Android SDK + NDK** (vários gigabytes de
ferramentas baixadas da Google), algo que só pode ser feito numa máquina
com acesso à internet — o que não estava disponível no ambiente onde este
código foi escrito.

A boa notícia: gerar o APK a partir daqui é **simples e direto**, leva uns
20-40 minutos na primeira vez (a maior parte é download automático de
ferramentas), e está detalhado no passo a passo abaixo.

---

## 📁 Estrutura do projeto

```
treino_app/
├── main.py                 # App Kivy: telas, gráfico de peso, troca de tema
├── db.py                   # Acesso a dados: CSV de exercícios + SQLite local
├── workout_generator.py    # Lógica de sorteio dos treinos (as "regras de negócio")
├── treino.kv               # Layout visual das 4 abas (linguagem KV do Kivy)
├── buildozer.spec          # Configuração para gerar o .apk com o Buildozer
├── requirements.txt        # Dependências Python (para rodar no PC, sem ser .apk)
└── data/
    └── exercicios.csv      # Banco de exercícios (o CSV que você enviou)
```

### Por que essa separação?

- **`db.py`** cuida só de dados (ler CSV, ler/gravar SQLite). Nenhuma linha
  de interface gráfica aqui — isso facilita testar e dar manutenção.
- **`workout_generator.py`** cuida só das *regras* de montagem de treino.
  Também não depende de interface gráfica, então pode ser testado
  isoladamente (e foi: veja a seção de testes abaixo).
- **`main.py` + `treino.kv`** cuidam só da interface (telas, botões,
  gráfico). Eles chamam as funções dos dois módulos acima, mas não
  reimplementam nenhuma regra de negócio.

Essa separação em camadas (dados / regras / interface) é uma boa prática
que facilita muito a manutenção e a geração de documentação a partir das
docstrings (todas as funções e classes têm docstring em formato NumPy).

---

## 🧠 Como a lógica de geração de treino funciona

Todas as regras pedidas foram implementadas em `workout_generator.py`:

| Tipo de treino | Regra |
|---|---|
| **Grupo muscular específico** | Sorteia 5 exercícios daquele grupo + nível, 3 séries cada. Se o grupo for "Pernas", pelo menos 1 dos 5 é obrigatoriamente de panturrilha. |
| **Treino A/B** | Dia A: 6 exercícios de membros superiores (Peito, Costas, Ombros, Braços). Dia B: 6 exercícios de Pernas, com pelo menos 1 de panturrilha. 3 séries cada. |
| **Full body** | 6 exercícios: 2 de perna (≥1 panturrilha), 1 de costas + 1 de bíceps, 1 de peito + 1 de tríceps. |

Quando o nível escolhido não tem exercícios suficientes no banco para
cumprir a regra (por exemplo, "Avançado" tem poucos exercícios de
panturrilha), o código **completa automaticamente** com exercícios de
níveis vizinhos e mostra um aviso (⚠) na tela explicando a adaptação — ele
nunca trava ou mostra um treino incompleto sem avisar.

A separação entre Bíceps/Tríceps (que no CSV ficam dentro do grupo
"Braços") é feita lendo a coluna `musculo_principal`, que indica qual é o
músculo realmente trabalhado por cada exercício daquele grupo.

### Testes da lógica (já executados)

A lógica de `workout_generator.py` foi testada diretamente com o CSV
fornecido (sem precisar de interface gráfica), gerando exemplos reais de
treino de Pernas/Iniciante, A/B/Intermediário e Full Body/Avançado — todos
respeitando as regras (panturrilha obrigatória, equilíbrio costas/bíceps e
peito/tríceps, etc.), sem nenhum aviso de falta de exercícios.

---

## 🎨 Visual / UI

> **Atualização**: o app passou por uma repaginada visual. Em vez do
> visual "cinza/quadrado" padrão do Kivy, agora ele usa:
> - Cantos arredondados em botões, cards, campos e seletores;
> - Uma paleta de cores mais suave (fundo levemente azulado, superfícies
>   brancas/escuras com sombra leve, um azul-violeta como cor de destaque);
> - Uma seta "▾" sempre visível em **todos** os campos de seleção (Tipo de
>   treino, Nível, Grupo muscular, e os filtros da aba Exercícios), deixando
>   claro que são campos clicáveis que abrem uma lista de opções;
> - Botões preenchidos com a cor de destaque (em vez do cinza padrão), e um
>   estilo "segmentado" nos botões de tema (o tema ativo aparece preenchido,
>   o outro só com contorno);
> - Texto secundário (nível, equipamento, número de séries) em uma cor mais
>   suave do que o nome do exercício, criando uma hierarquia visual mais
>   fácil de escanear.

## 🖥️ As 4 abas do app

> **Atualização**: as abas agora ficam em uma **barra de navegação
> inferior** (como a maioria dos apps mobile), com **ícones desenhados
> vetorialmente** (casa, halteres, "+" e engrenagem) em vez de texto/emoji —
> isso garante que os ícones fiquem nítidos em qualquer aparelho, sem
> depender de fontes de emoji ou imagens externas.

1. **Home** — lista todos os treinos já gerados e salvos como **cards
   expansíveis**: toque no card para abrir e ver cada exercício listado
   (um abaixo do outro) com a quantidade de séries, e um botão de excluir
   dentro do card expandido.
2. **Exercícios** — lista todos os exercícios do banco, com filtro por
   grupo muscular e por nível de dificuldade.
3. **Montar novo treino** — formulário em 3 passos: tipo de treino → nível
   → grupo muscular (esse último só aparece se o tipo escolhido for "Grupo
   muscular"). Depois de gerar, é possível salvar o treino.
4. **Configurações** — diário de peso corporal: campo para registrar o
   peso atual + gráfico de linha mostrando a evolução (desenhado à mão com
   o Canvas do Kivy, sem depender de bibliotecas externas de gráfico) e
   botões para trocar entre tema claro e tema escuro.

---

## 🔒 Sobre segurança / vulnerabilidades

Algumas decisões de projeto foram tomadas especificamente para minimizar
riscos de segurança:

- **Nenhuma permissão de internet, câmera, localização ou contatos** é
  solicitada (`android.permissions` vazio no `buildozer.spec`). O app não
  faz nenhuma chamada de rede.
- **Todas as consultas SQL usam parâmetros (`?`)**, nunca concatenação de
  strings — isso elimina por completo o risco de SQL Injection, mesmo que
  o usuário digite qualquer texto nos campos do app.
- Os dados (treinos salvos, diário de peso) ficam guardados apenas na
  pasta de dados privada do próprio app (`user_data_dir` do Kivy), isolada
  do restante do sistema e de outros apps.
- O app usa só **bibliotecas padrão do Python** (`sqlite3`, `csv`, `json`,
  `random`, `datetime`, `os`) + o framework **Kivy**, evitando
  dependências extras que aumentariam a superfície de ataque.
- `android.allow_backup = False` no `buildozer.spec` evita que ferramentas
  de backup automático do Android copiem os dados do app sem necessidade.

---

## 🚀 Como gerar o `.apk` (passo a passo)

Você vai precisar de um computador com **Linux** (pode ser uma máquina
virtual ou o **WSL** no Windows) com acesso à internet. O Buildozer só
funciona em Linux/macOS.

### 1. Instale as dependências do sistema (uma vez só)

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git zip unzip openjdk-17-jdk \
    autoconf libtool pkg-config zlib1g-dev libncurses5-dev cmake \
    libffi-dev libssl-dev build-essential
```

### 2. Instale o Buildozer

```bash
pip install --user buildozer cython==0.29.36
```

### 3. Copie a pasta `treino_app/` para essa máquina Linux

(Copie a pasta inteira deste projeto, mantendo a estrutura de arquivos.)

### 4. Gere o APK

Dentro da pasta `treino_app/`, rode:

```bash
buildozer -v android debug
```

Na primeira execução, o Buildozer vai **baixar automaticamente** o Android
SDK, o NDK e todas as ferramentas necessárias (por isso é importante ter
internet e ter paciência — pode levar de 20 a 40 minutos na primeira vez).

Ao final, o arquivo `.apk` vai aparecer em:

```
treino_app/bin/montatreino-1.0-arm64-v8a_armeabi-v7a-debug.apk
```

### 5. Instale no celular

Transfira esse `.apk` para o celular (por cabo USB, e-mail, Google Drive,
etc.) e toque nele para instalar. Talvez seja necessário permitir
"instalar de fontes desconhecidas" nas configurações do Android — isso é
normal para qualquer APK que não veio da Google Play.

### Dica: testar no PC antes de gerar o APK

Para testar o app rapidamente no próprio computador (sem precisar gerar
o APK a cada mudança), instale o Kivy e rode direto:

```bash
pip install -r requirements.txt
python3 main.py
```

A janela do app vai abrir no PC, exatamente com a mesma interface que vai
aparecer no celular.

---

## 🛠️ Possíveis próximos passos (sugestões)

- Adicionar um ícone customizado (`icon.filename` no `buildozer.spec`).
- Adicionar opção de editar/excluir um registro de peso específico.
- Adicionar exportação dos treinos salvos para um arquivo de texto.
- Gerar uma versão "release" assinada do APK (em vez de "debug") para
  publicar na Google Play, usando `buildozer android release` + assinatura
  com `apksigner` (etapa adicional não incluída aqui, pois exige gerar e
  guardar uma chave de assinatura própria).
