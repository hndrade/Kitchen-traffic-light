# Kitchen Traffic Light

Aplicativo Windows que gerencia os dias e horários de funcionamento da cozinha e avisa a equipe por meio de **notificações nativas do Windows** — sem precisar manter um widget/farol aberto na tela.

## Notificações

- `Cozinha liberada!` — no horário de abertura.
- `A cozinha abre em 5 minutos` — 5 minutos antes da abertura.
- `A cozinha fecha em 5 minutos` — 5 minutos antes do fechamento.

## Uso

1. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

2. Rode o app:

   ```bash
   python main.py
   ```

3. Na janela, configure para cada dia da semana se ele está ativo e os horários de abertura/fechamento (formato `HH:MM`). Marque **Iniciar com o Windows** se quiser que o app abra automaticamente no login. Clique em **Salvar**.

O app roda em segundo plano verificando o horário e disparando as notificações configuradas — a janela pode ficar minimizada/fechada em segundo plano enquanto o processo estiver ativo.

## Estrutura

- `app/config.py` — leitura/gravação da configuração (`~/.kitchen_traffic_light/config.json`).
- `app/scheduler.py` — laço em background que dispara as notificações no horário certo.
- `app/notifier.py` — envio das notificações nativas do Windows (via `winotify`).
- `app/startup.py` — registra/remove o app da inicialização do Windows.
- `app/gui.py` — janela de configuração dos dias e horários.
- `main.py` — ponto de entrada.
