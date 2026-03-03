import logging
import os

import google.generativeai as genai
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("La variable de entorno TELEGRAM_BOT_TOKEN no está definida.")
if not GEMINI_API_KEY:
    raise ValueError("La variable de entorno GEMINI_API_KEY no está definida.")

genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-1.5-pro"

# Cache of GenerativeModel instances keyed by model name
_model_cache: dict[str, genai.GenerativeModel] = {}


def get_model(model_name: str) -> genai.GenerativeModel:
    if model_name not in _model_cache:
        _model_cache[model_name] = genai.GenerativeModel(model_name)
    return _model_cache[model_name]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "¡Hola! Soy un bot impulsado por Google Gemini.\n"
        "Modelo activo por defecto: gemini-1.5-pro\n\n"
        "Comandos disponibles:\n"
        "  /pro   — Cambiar a gemini-1.5-pro\n"
        "  /flash — Cambiar a gemini-1.5-flash\n\n"
        "Envíame cualquier mensaje y te responderé con Gemini."
    )


async def set_pro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data["model"] = "gemini-1.5-pro"
    await update.message.reply_text("Modelo cambiado a gemini-1.5-pro ✅")


async def set_flash(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data["model"] = "gemini-1.5-flash"
    await update.message.reply_text("Modelo cambiado a gemini-1.5-flash ✅")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    model_name = context.chat_data.get("model", DEFAULT_MODEL)

    try:
        model = get_model(model_name)
        response = model.generate_content(user_text)
        reply = getattr(response, "text", None)
        if not reply:
            await update.message.reply_text(
                "La respuesta de Gemini no contiene texto (puede que el contenido haya sido bloqueado)."
            )
            return
        await update.message.reply_text(reply)
    except Exception as exc:
        logger.exception("Error al llamar a Gemini: %s", exc)
        await update.message.reply_text(
            "Lo siento, ocurrió un error al procesar tu consulta. Por favor, inténtalo de nuevo."
        )


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pro", set_pro))
    app.add_handler(CommandHandler("flash", set_flash))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot iniciado. Esperando mensajes...")
    app.run_polling()


if __name__ == "__main__":
    main()

