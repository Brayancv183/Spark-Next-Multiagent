import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from crew import procesar_mensaje, generar_reporte, METRICAS
from transcription import transcribir_audio

import time
load_dotenv()

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"logs/bot_{time.strftime('%Y%m%d')}.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN no está definido")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY no está definida")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text(
        "¡Hola! Soy el asistente virtual de Spark Next. "
        "Puedes saludarme, consultar datos de tu caso (id_request) o reportar una queja. "
        "También puedes enviarme notas de voz."
    )


def guardar_conversacion(chat_id, mensaje, respuesta, tipo="texto"):
    archivo = f"logs/conversaciones_{time.strftime('%Y%m%d')}.txt"
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] Chat {chat_id} ({tipo})\n")
        f.write(f"  Usuario: {mensaje}\n")
        f.write(f"  Bot: {respuesta}\n\n")


async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("Este comando solo esta disponible para el administrador.")
        return
    reporte_texto = generar_reporte()
    await update.message.reply_text(reporte_texto)


async def manejar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    texto = update.message.text
    logger.info(f"Mensaje de {chat_id}: {texto}")

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        respuesta = await asyncio.to_thread(procesar_mensaje, chat_id, texto)
        await update.message.reply_text(respuesta)
        guardar_conversacion(chat_id, texto, respuesta)
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}", exc_info=True)
        await update.message.reply_text(
            "Lo siento, ocurrió un error interno. Por favor intenta de nuevo."
        )


async def manejar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    logger.info(f"Audio recibido de {chat_id}")

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        archivo = await update.message.voice.get_file()
        bytes_audio = await archivo.download_as_bytearray()

        texto = await asyncio.to_thread(transcribir_audio, bytes(bytes_audio), GROQ_API_KEY)
        logger.info(f"Transcripcion: {texto}")

        respuesta = await asyncio.to_thread(procesar_mensaje, chat_id, texto)
        await update.message.reply_text(respuesta)
        guardar_conversacion(chat_id, texto, respuesta, tipo="voz")
    except Exception as e:
        logger.error(f"Error procesando audio: {e}", exc_info=True)
        await update.message.reply_text(
            "Lo siento, no pude procesar tu nota de voz. Intenta enviar el mensaje por escrito."
        )


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reporte", reporte))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_texto))
    app.add_handler(MessageHandler(filters.VOICE, manejar_audio))

    logger.info("Bot iniciado, esperando mensajes...")
    app.run_polling(poll_interval=1, timeout=30)


if __name__ == "__main__":
    main()
