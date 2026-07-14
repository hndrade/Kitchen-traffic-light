# Kitchen-traffic-light

Semáforo virtual para a cozinha — um widget de área de trabalho para Windows
que mostra um semáforo realista (estilo poste de rua) sempre no topo da tela.

- 🟢 **Verde** — cozinha aberta (estado padrão)
- 🟡 **Amarelo** — faltam 5 minutos para um período de fechamento
- 🔴 **Vermelho** — cozinha fechada (limpeza em andamento)

Horários padrão: **segunda e terça**, das **09:30 às 10:30** e das **14:00 às 15:00**.

## Como usar

Requer apenas Python 3 (Tkinter já vem incluído no instalador do Windows).
Nenhuma dependência externa para rodar.

```
pythonw semaforo.py
```

(`pythonw` executa sem abrir janela de console; `python semaforo.py` também funciona.)

- **Arrastar**: clique e arraste em qualquer ponto do semáforo para movê-lo.
- **Configurar**: clique na engrenagem (⚙) no canto inferior direito da caixa.
- **Botão direito** no semáforo: menu com *Minimizar para a bandeja*,
  *Configurações* e *Sair*.

## Bandeja do sistema (ao lado do relógio)

O app mantém um ícone de mini-semáforo na área de notificação, colorido
conforme o estado atual:

- Em **dias sem agendamento** (por padrão, quarta a domingo), o app abre
  **minimizado na bandeja** — sem janela na tela.
- **Clique no ícone da bandeja** para mostrar/ocultar o semáforo a qualquer
  momento. A escolha manual vale até a virada do dia; depois a regra
  automática volta a valer.

## Configurações

Na janela de configurações:

- **Dias da semana** — linha de botões `S T Q Q S S D` (Seg → Dom);
  selecione os dias em que os horários de fechamento valem.
- **Períodos de fechamento** — lista de faixas como `09:30 às 10:30`,
  com `x` para excluir cada uma.
- **+** — adiciona uma nova faixa (seletores de hora/minuto para início e fim).
- **Iniciar com o Windows** — marca/desmarca a inicialização automática ao
  ligar o PC (grava na chave `Run` do registro do usuário; vale tanto para o
  script quanto para o .exe compilado).
- **Salvar** — grava tudo em `settings.json` na mesma pasta do script (ou do
  .exe).

## Compilar o executável (.exe)

No Windows, basta rodar:

```
build_exe.bat
```

O script instala o PyInstaller se necessário, gera o ícone (`semaforo.ico`,
criado por `gen_icon.py` — só biblioteca padrão) e produz
**`dist\SemaforoCozinha.exe`** (arquivo único, sem console).

Para abrir automaticamente ao ligar o PC: execute o .exe uma vez, abra as
configurações (⚙) e marque **Iniciar com o Windows**. (Alternativa manual:
criar um atalho do .exe na pasta `shell:startup`.)

> Observação: mova o .exe para a pasta definitiva **antes** de marcar a
> inicialização automática — o caminho gravado no registro é o do executável
> no momento em que a opção é salva. O `settings.json` é criado ao lado do
> .exe.

## settings.json

```json
{
  "days": ["S", "T"],
  "day_indices": [0, 1],
  "schedules": [
    {"start": "09:30", "end": "10:30"},
    {"start": "14:00", "end": "15:00"}
  ]
}
```

`days` guarda as letras posicionais da semana (formato legível); como as
letras `S` e `Q` se repetem, o campo `day_indices` (0 = segunda … 6 = domingo)
é a forma não ambígua usada pelo programa. Se `day_indices` não existir,
as letras são resolvidas pela posição na sequência da semana.
