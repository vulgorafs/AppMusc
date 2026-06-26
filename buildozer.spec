[app]

# Nome do app que aparece no celular, embaixo do ícone.
title = Monta Treino

# Nome do pacote Android (sem espaços, sem acentos, tudo minúsculo).
package.name = montatreino

# Domínio invertido do pacote (padrão usado para identificar o app de forma única).
package.domain = org.treinoapp

# Pasta onde está o código-fonte (a raiz deste mesmo projeto).
source.dir = .

# Arquivo principal que o Android deve executar ao abrir o app.
source.main = main.py

# Extensões de arquivo que devem ser incluídas dentro do pacote final
# (inclui o .kv de layout, o .csv do banco de exercícios e imagens, se houver).
source.include_exts = py,kv,csv,png,jpg,kv,atlas

# Versão do app exibida para o usuário.
version = 1.0

# Dependências Python que o app precisa para funcionar dentro do Android.
# - python3: interpretador Python embutido no app
# - kivy: framework de interface gráfica usado neste projeto
# sqlite3, csv, json, random, datetime e os já vêm na biblioteca padrão do
# Python, então NÃO precisam ser listados aqui.
requirements = python3,kivy

# Orientação de tela. "portrait" trava o app no modo retrato (vertical),
# que é o mais comum para apps de produtividade/uso cotidiano como este.
orientation = portrait

# Ícone e splash screen (opcionais). Deixe comentado se não tiver os
# arquivos de imagem; o buildozer usa um ícone padrão do Kivy nesse caso.
# icon.filename = %(source.dir)s/data/icone.png
# presplash.filename = %(source.dir)s/data/splash.png

[buildozer]

# Nível de detalhe dos logs durante o build (0 = silencioso, 2 = bem detalhado).
log_level = 2

# Pasta usada pelo buildozer para arquivos temporários de build.
build_dir = ./.buildozer

# Pasta onde o .apk final será colocado depois de compilado.
bin_dir = ./bin

[app:android]

# --- PERMISSÕES DO ANDROID ---
# Esta linha está DE PROPÓSITO vazia / comentada: o app NÃO PRECISA de
# nenhuma permissão especial (sem internet, sem câmera, sem localização,
# sem acesso a contatos). Isso reduz drasticamente a superfície de
# vulnerabilidade do aplicativo, já que ele não pode acessar nada sensível
# do aparelho além do seu próprio espaço de armazenamento privado (usado
# apenas pelo banco SQLite local).
android.permissions =

# API mínima e API alvo do Android. Usar uma API alvo recente é importante
# para passar pelas regras de segurança mais atuais da Google Play e dos
# próprios aparelhos Android (ex.: TLS, sandboxing de apps, etc.).
android.minapi = 21
android.api = 34

# Arquiteturas de processador suportadas (cobre praticamente 100% dos
# celulares Android vendidos nos últimos anos).
android.archs = arm64-v8a, armeabi-v7a

# Garante que o app só seja instalável a partir do próprio usuário/loja,
# sem permitir backup automático de dados sensíveis por outros apps.
android.allow_backup = False
