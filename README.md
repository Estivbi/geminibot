# geminibot

Bot de Telegram integrado con la API de Google Gemini. Usa por defecto el modelo **gemini-1.5-pro** y permite cambiar dinámicamente al modelo **gemini-1.5-flash**.

## Requisitos

- Python 3.10 o superior
- Una cuenta de [Telegram](https://telegram.org/) y un bot creado mediante [@BotFather](https://t.me/BotFather)
- Una clave de API de [Google Gemini](https://aistudio.google.com/app/apikey)

## Instalación

1. Clona el repositorio:

   ```bash
   git clone https://github.com/Estivbi/geminibot.git
   cd geminibot
   ```

2. Crea y activa un entorno virtual (recomendado):

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # En Windows: .venv\Scripts\activate
   ```

3. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Copia el archivo de ejemplo de variables de entorno y rellena tus credenciales:

   ```bash
   cp .env.example .env
   ```

   Edita `.env` y reemplaza los valores de ejemplo:

   ```
   TELEGRAM_BOT_TOKEN=tu_token_de_telegram
   GEMINI_API_KEY=tu_clave_de_api_gemini
   ```

## Ejecución

```bash
python bot.py
```

## Comandos disponibles

| Comando  | Descripción                                      |
|----------|--------------------------------------------------|
| `/start` | Muestra el mensaje de bienvenida e instrucciones |
| `/pro`   | Cambia el modelo activo a **gemini-1.5-pro**     |
| `/flash` | Cambia el modelo activo a **gemini-1.5-flash**   |

Cualquier otro mensaje de texto es enviado directamente al modelo activo y se devuelve la respuesta generada por Gemini.

## Variables de entorno

| Variable             | Descripción                              |
|----------------------|------------------------------------------|
| `TELEGRAM_BOT_TOKEN` | Token del bot obtenido desde @BotFather  |
| `GEMINI_API_KEY`     | Clave de API de Google Gemini            |
