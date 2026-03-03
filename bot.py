import asyncio
import logging
import os
import re

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

PREFERRED_MODELS = (
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
)
DEFAULT_MODEL = "gemini-1.5-flash"

# Cache of GenerativeModel instances keyed by model name
_model_cache: dict[str, genai.GenerativeModel] = {}
available_models: set[str] = set()


def list_supported_models() -> set[str]:
    supported: set[str] = set()
    for model in genai.list_models():
        if "generateContent" in model.supported_generation_methods:
            supported.add(model.name.replace("models/", "", 1))
    return supported


def choose_default_model(models: set[str]) -> str:
    for model_name in PREFERRED_MODELS:
        if model_name in models:
            return model_name

    if not models:
        raise RuntimeError(
            "No hay modelos compatibles con generateContent para esta API key."
        )
    return sorted(models)[0]


def model_label(model_name: str) -> str:
    return model_name if model_name in available_models else f"{model_name} (no disponible)"


def get_model(model_name: str) -> genai.GenerativeModel:
    if model_name not in _model_cache:
        _model_cache[model_name] = genai.GenerativeModel(model_name)
    return _model_cache[model_name]


def parse_retry_seconds(error_text: str) -> int | None:
    match = re.search(r"Please retry in ([0-9]+(?:\.[0-9]+)?)s", error_text)
    if not match:
        return None
    return int(float(match.group(1)))


def fallback_models(current_model: str) -> list[str]:
    preferred_available = [model for model in PREFERRED_MODELS if model in available_models]
    others = [model for model in sorted(available_models) if model not in preferred_available]
    ordered = [current_model] + [
        model for model in (preferred_available + others) if model != current_model
    ]
    return ordered


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "¡Hola! Soy un bot impulsado por Google Gemini.\n"
        f"Modelo activo por defecto: {DEFAULT_MODEL}\n\n"
        "Comandos disponibles:\n"
        f"  /pro   — Cambiar a {model_label('gemini-1.5-pro')}\n"
        f"  /flash — Cambiar a {model_label('gemini-1.5-flash')}\n\n"
        "Envíame cualquier mensaje y te responderé con Gemini."
    )


async def set_pro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    model_name = "gemini-1.5-pro"
    if model_name not in available_models:
        await update.message.reply_text(
            "Tu API key no tiene disponible gemini-1.5-pro. Usa /flash o prueba otro modelo."
        )
        return

    context.chat_data["model"] = model_name
    await update.message.reply_text("Modelo cambiado a gemini-1.5-pro ✅")


async def set_flash(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    model_name = "gemini-1.5-flash"
    if model_name not in available_models:
        await update.message.reply_text(
            "Tu API key no tiene disponible gemini-1.5-flash. Prueba /pro si está habilitado."
        )
        return

    context.chat_data["model"] = model_name
    await update.message.reply_text("Modelo cambiado a gemini-1.5-flash ✅")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_model = context.chat_data.get("model", DEFAULT_MODEL)
    lines = [
        "Estado del bot:",
        f"- Modelo actual del chat: {current_model}",
        f"- Modelo por defecto: {DEFAULT_MODEL}",
    ]

    checks = [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]
    for model_name in checks:
        enabled = "✅" if model_name in available_models else "❌"
        lines.append(f"- {model_name}: {enabled}")

    await update.message.reply_text("\n".join(lines))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    model_name = context.chat_data.get("model", DEFAULT_MODEL)
    models_to_try = fallback_models(model_name)
    quota_errors: list[str] = []

    for candidate_model in models_to_try:
        try:
            model = get_model(candidate_model)
            response = await asyncio.to_thread(model.generate_content, user_text)
            reply = getattr(response, "text", None)

            if not reply:
                await update.message.reply_text(
                    "La respuesta de Gemini no contiene texto (puede que el contenido haya sido bloqueado)."
                )
                return

            if candidate_model != model_name:
                context.chat_data["model"] = candidate_model
                logger.info(
                    "Cambio automático de modelo: %s -> %s",
                    model_name,
                    candidate_model,
                )

            await update.message.reply_text(reply)
            return
        except google_exceptions.ResourceExhausted as exc:
            message = str(exc)
            quota_errors.append(message)
            logger.warning("Cuota excedida en %s: %s", candidate_model, message)
            continue
        except google_exceptions.NotFound as exc:
            logger.warning("Modelo no disponible en %s: %s", candidate_model, exc)
            continue
        except Exception as exc:
            logger.exception("Error al llamar a Gemini: %s", exc)
            await update.message.reply_text(
                "Lo siento, ocurrió un error al procesar tu consulta. Por favor, inténtalo de nuevo."
            )
            return

    if quota_errors:
        retry_seconds = parse_retry_seconds(quota_errors[-1])
        if retry_seconds is not None:
            await update.message.reply_text(
                f"Tu clave de Gemini se quedó sin cuota por ahora. Intenta de nuevo en ~{retry_seconds}s o revisa facturación/cuotas en Google AI Studio."
            )
        else:
            await update.message.reply_text(
                "Tu clave de Gemini se quedó sin cuota. Revisa límites/facturación en Google AI Studio e inténtalo más tarde."
            )
        return

    await update.message.reply_text(
        "No hay modelos disponibles para tu API key en este momento."
    )


def main() -> None:
    load_dotenv()

    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not telegram_bot_token:
        raise ValueError("La variable de entorno TELEGRAM_BOT_TOKEN no está definida.")
    if any(char.isspace() for char in telegram_bot_token):
        raise ValueError(
            "TELEGRAM_BOT_TOKEN contiene espacios o saltos de línea; revisa el valor en .env."
        )
    if not gemini_api_key:
        raise ValueError("La variable de entorno GEMINI_API_KEY no está definida.")

    genai.configure(api_key=gemini_api_key)

    global available_models
    available_models = list_supported_models()

    global DEFAULT_MODEL
    DEFAULT_MODEL = choose_default_model(available_models)
    logger.info("Modelo por defecto seleccionado: %s", DEFAULT_MODEL)

    app = ApplicationBuilder().token(telegram_bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pro", set_pro))
    app.add_handler(CommandHandler("flash", set_flash))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stattus", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot iniciado. Esperando mensajes...")
    app.run_polling()


if __name__ == "__main__":
    main()

