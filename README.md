# Kitchen-traffic-light

Semáforo virtual para a cozinha — um widget de área de trabalho para Windows
que mostra um semáforo realista (estilo poste de rua) sempre no topo da tela.

- 🟢 **Verde** — cozinha aberta (estado padrão)
- 🟡 **Amarelo** — faltam 5 minutos para um período de fechamento
- 🔴 **Vermelho** — cozinha fechada (limpeza em andamento)

## Como usar

Requer apenas Python 3 (Tkinter já vem incluído no instalador do Windows).
Nenhuma dependência externa.

```
pythonw semaforo.py
```

(`pythonw` executa sem abrir janela de console; `python semaforo.py` também funciona.)

- **Arrastar**: clique e arraste em qualquer ponto do semáforo para movê-lo.
- **Configurar**: clique na engrenagem (⚙) no canto inferior direito da caixa.

## Configurações

Na janela de configurações:

- **Dias da semana** — linha de botões `S T Q Q S S D` (Seg → Dom);
  selecione os dias em que os horários de fechamento valem.
- **Períodos de fechamento** — lista de faixas como `09:30 às 10:30`,
  com `x` para excluir cada uma.
- **+** — adiciona uma nova faixa (seletores de hora/minuto para início e fim).
- **Salvar** — grava tudo em `settings.json` na mesma pasta do script.

## settings.json

```json
{
  "days": ["S", "T", "Q", "Q", "S"],
  "day_indices": [0, 1, 2, 3, 4],
  "schedules": [
    {"start": "09:30", "end": "10:30"},
    {"start": "14:00", "end": "15:30"}
  ]
}
```

`days` guarda as letras posicionais da semana (formato legível); como as
letras `S` e `Q` se repetem, o campo `day_indices` (0 = segunda … 6 = domingo)
é a forma não ambígua usada pelo programa. Se `day_indices` não existir,
as letras são resolvidas pela posição na sequência da semana.
