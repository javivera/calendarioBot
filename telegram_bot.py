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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Disable HTTP request logging from urllib3 and other libraries
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Get bot token from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_IDS = os.getenv("ALLOWED_CHAT_IDS", "").split(",") if os.getenv("ALLOWED_CHAT_IDS") else []

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

# Load Whisper model (free, local)
logger.info("🤖 Loading Whisper model for voice transcription...")
whisper_model = whisper.load_model("base")  # Options: tiny, base, small, medium, large
logger.info("✅ Whisper model loaded successfully!")

class TelegramBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up command and message handlers"""
        # Simple start command
        self.application.add_handler(CommandHandler("start", self.start_command))
        
        # Calendar link command
        self.application.add_handler(CommandHandler("calendar", self.calendar_command))
        
        # Handle audio messages (voice messages and audio files)
        self.application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, self.handle_audio))
        
        # Handle text messages (including commands) go to Gemini
        self.application.add_handler(MessageHandler(filters.TEXT, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        logger.info(f"🚀 New user started bot: {username} ({user_id})")
        
        welcome_message = (
            "¡Hola! 👋 Soy tu asistente de reservas de Cabañas Las Chacras.\n\n"
            "Puedes escribirme cualquier cosa sobre reservas:\n"
            "• Hacer nuevas reservas\n"
            "• Consultar reservas existentes\n"
            "• Modificar o cancelar reservas\n"
            "• Ver el calendario de disponibilidad\n\n"
            "📅 **Comandos disponibles:**\n"
            "• /calendar - Ver el calendario online\n\n"
            "🎤 También puedes enviar mensajes de voz y los transcribiré automáticamente.\n\n"
            "¡Solo escríbeme o háblame lo que necesites en lenguaje natural!"
        )
        await update.message.reply_text(welcome_message)
    
    async def calendar_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /calendar command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        logger.info(f"📅 Calendar requested by: {username} ({user_id})")
        
        calendar_message = (
            "📅 **Calendario de Reservas - Cabañas Las Chacras**\n\n"
            "🌐 https://javivera.github.io/calendario/\n\n"
        )
        await update.message.reply_text(calendar_message, parse_mode='Markdown')
    
    async def handle_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle audio messages (voice messages and audio files)"""
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name
            
            # Check if access is restricted
            if ALLOWED_CHAT_IDS and str(update.effective_user.id) not in ALLOWED_CHAT_IDS:
                logger.warning(f"🚫 Unauthorized audio access attempt from {username} ({user_id})")
                await update.message.reply_text(
                    "❌ No tienes autorización para usar este bot. "
                    "Contacta al administrador si necesitas acceso."
                )
                return
            
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Get the audio file (voice message or audio file)
            audio_file = None
            if update.message.voice:
                audio_file = update.message.voice
                logger.info(f"🎤 Voice message received from {username} ({user_id})")
            elif update.message.audio:
                audio_file = update.message.audio
                logger.info(f"🎵 Audio file received from {username} ({user_id})")
            
            if not audio_file:
                logger.error("❌ No audio file found in message")
                await update.message.reply_text("❌ No se pudo procesar el audio.")
                return
            
            logger.info("🔄 Processing audio file...")
            
            # Download the audio file
            file = await context.bot.get_file(audio_file.file_id)
            
            # Create a temporary file to store the audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
                await file.download_to_drive(temp_file.name)
                temp_file_path = temp_file.name
            
            try:
                # Whisper can handle OGG files directly - no conversion needed!
                logger.info("🤖 Transcribing audio with Whisper...")
                result = whisper_model.transcribe(temp_file_path, language="es")
                transcribed_text = result["text"]
                
                logger.info(f"✅ Audio transcribed: \"{transcribed_text}\"")
                
                # Send the transcription to the user (optional)
                await update.message.reply_text(f"🎤 Esto escucho el bot: \"{transcribed_text}\"")
                
                # Process the transcribed text with Gemini
                logger.info("🧠 Sending transcribed text to Gemini AI...")
                response = main.chat.send_message(transcribed_text)
                
                # Split long messages if needed
                if len(response.text) > 4000:
                    chunks = [response.text[i:i+4000] for i in range(0, len(response.text), 4000)]
                    logger.info(f"📝 Sending response in {len(chunks)} chunks")
                    for chunk in chunks:
                        await update.message.reply_text(chunk)
                else:
                    logger.info("📝 Sending AI response")
                    await update.message.reply_text(response.text)
                    
            finally:
                # Clean up the temporary file
                logger.info("🧹 Cleaning up temporary audio file")
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"❌ Error handling audio message: {e}")
            await update.message.reply_text(
                "❌ Lo siento, ocurrió un error al procesar el audio. "
                "Por favor, intenta de nuevo o envía un mensaje de texto."
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all messages - bridge to Gemini"""
        try:
            user_message = update.message.text
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name
            
            # Check if access is restricted
            if ALLOWED_CHAT_IDS and str(update.effective_user.id) not in ALLOWED_CHAT_IDS:
                logger.warning(f"🚫 Unauthorized message access attempt from {username} ({user_id})")
                await update.message.reply_text(
                    "❌ No tienes autorización para usar este bot. "
                    "Contacta al administrador si necesitas acceso."
                )
                return
            
            logger.info(f"💬 Message from {username} ({user_id}): {user_message}")
            
            # Check if the message is asking for calendar link
            calendar_keywords = ['calendario', 'calendar', 'link', 'enlace', 'ver reservas', 'pagina', 'web']
            if any(keyword in user_message.lower() for keyword in calendar_keywords):
                logger.info("📅 Calendar link requested via keyword detection")
                calendar_message = (
                    "📅 **Calendario de Reservas - Cabañas Las Chacras**\n\n"
                    "🌐 https://javivera.github.io/calendario/\n\n"
                
                  
                )
                await update.message.reply_text(calendar_message, parse_mode='Markdown')
                return
            
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Send message to Gemini (your existing chat logic)
            logger.info("🧠 Sending message to Gemini AI...")
            response = main.chat.send_message(user_message)
            
            # Split long messages if needed (Telegram has a 4096 character limit)
            if len(response.text) > 4000:
                chunks = [response.text[i:i+4000] for i in range(0, len(response.text), 4000)]
                logger.info(f"📝 Sending AI response in {len(chunks)} chunks")
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                logger.info("📝 Sending AI response")
                await update.message.reply_text(response.text)
                
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
            await update.message.reply_text(
                "❌ Lo siento, ocurrió un error al procesar tu mensaje. "
                "Por favor, intenta de nuevo."
            )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"❌ Bot error - Update: {update} | Error: {context.error}")
    
    def run(self):
        """Start the bot"""
        logger.info("🚀 Starting Telegram bot...")
        
        # Add error handler
        self.application.add_error_handler(self.error_handler)
        
        # Run the bot
        logger.info("✅ Bot is running and listening for messages...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        logger.info("🎯 Initializing Telegram Bot for Cabañas Las Chacras...")
        bot = TelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise
