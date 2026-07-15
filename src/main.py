import sys
from pathlib import Path

# Add project root to python path to avoid ModuleNotFoundError when running on Railway
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from src.config import TELEGRAM_BOT_TOKEN, validate_config
from src.database import init_db
from src.handlers import start, handle_text, handle_photo

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Validate that required configurations exist
        validate_config()
    except ValueError as e:
        logger.error(f"Config Error: {e}")
        print(f"\n❌ [ERRO DE CONFIGURAÇÃO] {e}\n")
        return

    # Initialize Database on startup (synchronously before starting loop)
    logger.info("Inicializando banco de dados SQLite local...")
    try:
        init_db()
        logger.info("Banco de dados pronto para uso.")
    except Exception as e:
        logger.critical(f"Falha ao inicializar o banco de dados: {e}", exc_info=True)
        return

    # Initialize the Application
    logger.info("Construindo aplicação do Telegram Bot...")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register Command and Message Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Guru Tips Bot iniciado. Aguardando mensagens por polling...")
    
    # Run the bot until Stopped (Ctrl+C)
    application.run_polling()

if __name__ == '__main__':
    main()
