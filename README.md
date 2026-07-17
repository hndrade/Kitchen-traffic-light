# Kitchen Traffic Light

Aplicativo Windows que gerencia os dias e horários de impedimento da cozinha e avisa a equipe por meio de **notificações nativas do Windows** — sem precisar manter um widget/farol aberto na tela.

Para cada dia da semana é possível configurar até dois períodos em que a cozinha fica indisponível (por padrão: 09:30–10:30 e 14:00–15:00). Fora desses períodos a cozinha é considerada liberada.

## Notificações

- `Cozinha liberada!` — ao final de cada período de impedimento.
- `A cozinha abre em 5 minutos` — 5 minutos antes do fim de um período de impedimento.
- `A cozinha fecha em 5 minutos` — 5 minutos antes do início de um período de impedimento.

## Uso

1. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

2. Rode o app:

   ```bash
   python main.py
   ```

3. Na janela, configure para cada dia da semana se ele está ativo e o início/fim dos dois períodos de impedimento (formato `HH:MM`). Marque **Iniciar com o Windows** se quiser que o app abra automaticamente no login. Clique em **Salvar**.

O app roda em segundo plano verificando o horário e disparando as notificações configuradas — a janela pode ficar minimizada/fechada em segundo plano enquanto o processo estiver ativo.

## Estrutura

- `app/config.py` — leitura/gravação da configuração (`~/.kitchen_traffic_light/config.json`).
- `app/scheduler.py` — laço em background que dispara as notificações no horário certo.
- `app/notifier.py` — envio das notificações nativas do Windows (via `winotify`).
- `app/startup.py` — registra/remove o app da inicialização do Windows.
- `app/gui.py` — janela de configuração dos dias e horários.
- `main.py` — ponto de entrada.
