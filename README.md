# Monta Treino 🏋️

Aplicativo mobile (Android) para montagem de treinos de academia, escrito
**100% em Python**, usando o framework **Kivy** para a interface gráfica e
**SQLite** (biblioteca padrão do Python) para armazenamento local.

O app monta treinos aleatórios a partir de um banco de exercícios em CSV,
de acordo com o tipo de treino, nível de dificuldade e grupo muscular
escolhidos pelo usuário.

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

## 🧠 Como a lógica de geração de treino funciona

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

---

## 🚀 Como gerar o `.apk` (passo a passo)

Você vai precisar de um computador com **Linux** (pode ser uma máquina
virtual ou o **WSL** no Windows) com acesso à internet. O Buildozer só
funciona em Linux/macOS.

### 1. Instale as dependências do sistema

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

### 3. Copie a pasta para essa máquina Linux

(Copie a pasta inteira deste projeto, mantendo a estrutura de arquivos.)

### 4. Gere o APK

Dentro da pasta, rode:

```bash
buildozer -v android debug
```
