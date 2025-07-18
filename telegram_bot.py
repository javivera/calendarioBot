import os
import logging
import tempfile
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import whisper
import main  # Import your existing main.py functions

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_IDS = os.getenv("ALLOWED_CHAT_IDS", "").split(",") if os.getenv("ALLOWED_CHAT_IDS") else []

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

# Load Whisper model (free, local)
print("Loading Whisper model...")
whisper_model = whisper.load_model("base")  # Options: tiny, base, small, medium, large
print("Whisper model loaded!")

class TelegramBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up command and message handlers"""
        # Simple start command
        self.application.add_handler(CommandHandler("start", self.start_command))
        
        # Handle audio messages (voice messages and audio files)
        self.application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, self.handle_audio))
        
        # Handle text messages (including commands) go to Gemini
        self.application.add_handler(MessageHandler(filters.TEXT, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = (
            "¡Hola! 👋 Soy tu asistente de reservas de cabaña.\n\n"
            "Puedes escribirme cualquier cosa sobre reservas:\n"
            "• Hacer nuevas reservas\n"
            "• Consultar reservas existentes\n"
            "• Modificar o cancelar reservas\n"
            "• Ver el calendario de disponibilidad\n\n"
            "🎤 También puedes enviar mensajes de voz y los transcribiré automáticamente.\n\n"
            "¡Solo escríbeme o háblame lo que necesites en lenguaje natural!"
        )
        await update.message.reply_text(welcome_message)
    
    async def handle_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle audio messages (voice messages and audio files)"""
        try:
            # Check if access is restricted
            if ALLOWED_CHAT_IDS and str(update.effective_user.id) not in ALLOWED_CHAT_IDS:
                await update.message.reply_text(
                    "❌ No tienes autorización para usar este bot. "
                    "Contacta al administrador si necesitas acceso."
                )
                return
            
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name
            
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Get the audio file (voice message or audio file)
            audio_file = None
            if update.message.voice:
                audio_file = update.message.voice
                logger.info(f"Voice message from {username} ({user_id})")
            elif update.message.audio:
                audio_file = update.message.audio
                logger.info(f"Audio file from {username} ({user_id})")
            
            if not audio_file:
                await update.message.reply_text("❌ No se pudo procesar el audio.")
                return
            
            # Download the audio file
            file = await context.bot.get_file(audio_file.file_id)
            
            # Create a temporary file to store the audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
                await file.download_to_drive(temp_file.name)
                temp_file_path = temp_file.name
            
            try:
                # Whisper can handle OGG files directly - no conversion needed!
                result = whisper_model.transcribe(temp_file_path, language="es")
                transcribed_text = result["text"]
                
                logger.info(f"Transcribed text: {transcribed_text}")
                
                # Send the transcription to the user (optional)
                await update.message.reply_text(f"🎤 Esto escucho el bot: \"{transcribed_text}\"")
                
                # Process the transcribed text with Gemini
                response = main.chat.send_message(transcribed_text)
                
                # Split long messages if needed
                if len(response.text) > 4000:
                    chunks = [response.text[i:i+4000] for i in range(0, len(response.text), 4000)]
                    for chunk in chunks:
                        await update.message.reply_text(chunk)
                else:
                    await update.message.reply_text(response.text)
                    
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"Error handling audio message: {e}")
            await update.message.reply_text(
                "❌ Lo siento, ocurrió un error al procesar el audio. "
                "Por favor, intenta de nuevo o envía un mensaje de texto."
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all messages - bridge to Gemini"""
        try:
            # Check if access is restricted
            if ALLOWED_CHAT_IDS and str(update.effective_user.id) not in ALLOWED_CHAT_IDS:
                await update.message.reply_text(
                    "❌ No tienes autorización para usar este bot. "
                    "Contacta al administrador si necesitas acceso."
                )
                return
            
            user_message = update.message.text
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name
            
            logger.info(f"Message from {username} ({user_id}): {user_message}")
            
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Send message to Gemini (your existing chat logic)
            response = main.chat.send_message(user_message)
            
            # Split long messages if needed (Telegram has a 4096 character limit)
            if len(response.text) > 4000:
                chunks = [response.text[i:i+4000] for i in range(0, len(response.text), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(response.text)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text(
                "❌ Lo siento, ocurrió un error al procesar tu mensaje. "
                "Por favor, intenta de nuevo."
            )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Telegram bot...")
        
        # Add error handler
        self.application.add_error_handler(self.error_handler)
        
        # Run the bot
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
