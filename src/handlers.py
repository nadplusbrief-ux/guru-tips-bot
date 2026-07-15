import io
import base64
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from openai import AsyncOpenAI

from src.config import OPENAI_API_KEY, DAILY_LIMIT
from src.database import async_check_and_increment_usage
from src.prompt import GURU_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Initialize Async OpenAI Client
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def reply_with_markdown_fallback(message, text: str, edit_message=None):
    """
    Sends or edits a Telegram message.
    Tries to render with Markdown formatting first. If it fails due to formatting issues,
    falls back to raw text. Automatically splits messages longer than 4000 characters.
    """
    # Split text into chunks of 4000 characters to prevent Telegram message length limits
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    
    for idx, chunk in enumerate(chunks):
        try:
            if idx == 0 and edit_message:
                await edit_message.edit_text(chunk, parse_mode="Markdown")
            else:
                await message.reply_text(chunk, parse_mode="Markdown")
        except BadRequest as e:
            logger.warning(f"Failed to send message with Markdown parsing. Retrying as plain text. Error: {e}")
            try:
                if idx == 0 and edit_message:
                    await edit_message.edit_text(chunk)
                else:
                    await message.reply_text(chunk)
            except Exception as e2:
                logger.error(f"Failed to send fallback message: {e2}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler. Greets the user and explains the bot limits and capabilities."""
    user = update.effective_user
    username = user.username or user.first_name
    
    welcome_text = (
        f"Olá, *{username}*! Bem-vindo ao *Guru Tips*! 🧠⚽\n\n"
        "Eu sou seu analista e gestor de risco de apostas esportivas, "
        "movido por inteligência artificial avançada.\n\n"
        "Aqui está o que posso fazer por você:\n"
        "💬 *Enviar Texto:* Escreva os detalhes de um jogo, odds e mercados para receber uma análise tática e de Valor Esperado (EV).\n"
        "📸 *Enviar Imagem:* Mande o print ou foto do seu bilhete de apostas para uma auditoria completa de risco e gestão de banca.\n\n"
        f"📊 *Plano Grátis:* Você possui um limite de até *{DAILY_LIMIT} análises diárias* gratuitas.\n\n"
        "Como posso te ajudar hoje?"
    )
    await reply_with_markdown_fallback(update.message, welcome_text)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles textual analysis queries from users."""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username
    user_text = update.message.text

    # Skip commands
    if user_text.startswith('/'):
        return

    # Check daily rate limit
    is_allowed = await async_check_and_increment_usage(user_id, username)
    if not is_allowed:
        limit_msg = (
            f"Você atingiu seu limite diário de {DAILY_LIMIT} análises. "
            "Assine o plano premium para continuar."
        )
        await update.message.reply_text(limit_msg)
        return

    # Send a placeholder "thinking" message
    thinking_msg = await update.message.reply_text("Guru está analisando... ⏳")

    try:
        # Call OpenAI Chat Completion API
        completion = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": GURU_SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.4
        )
        response_text = completion.choices[0].message.content
        
        # Deliver response
        await reply_with_markdown_fallback(update.message, response_text, edit_message=thinking_msg)
        
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
        error_msg = (
            "Desculpe, ocorreu um erro ao processar sua análise com a inteligência artificial. "
            "Por favor, tente novamente em alguns instantes."
        )
        try:
            await thinking_msg.edit_text(error_msg)
        except Exception:
            await update.message.reply_text(error_msg)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles photo inputs (betting slip screenshots) using GPT-4o vision."""
    if not update.message or not update.message.photo:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username

    # Check daily rate limit
    is_allowed = await async_check_and_increment_usage(user_id, username)
    if not is_allowed:
        limit_msg = (
            f"Você atingiu seu limite diário de {DAILY_LIMIT} análises. "
            "Assine o plano premium para continuar."
        )
        await update.message.reply_text(limit_msg)
        return

    # Send a placeholder "thinking" message
    thinking_msg = await update.message.reply_text("Guru está analisando o bilhete... ⏳")

    try:
        # Get the largest photo size
        largest_photo = update.message.photo[-1]
        photo_file = await largest_photo.get_file()
        
        # Download image directly to memory
        out = io.BytesIO()
        await photo_file.download_to_memory(out)
        image_bytes = out.getvalue()
        
        # Base64 encode
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Prompt text (use caption if present, otherwise default)
        prompt_text = update.message.caption
        if not prompt_text:
            prompt_text = (
                "Audite este bilhete. Calcule o risco, a probabilidade implícita combinada "
                "e diga se há valor esperado (EV) positivo, propondo gestão de banca adequada."
            )

        # Call OpenAI GPT-4o Vision
        completion = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": GURU_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.4
        )
        response_text = completion.choices[0].message.content
        
        # Deliver response
        await reply_with_markdown_fallback(update.message, response_text, edit_message=thinking_msg)

    except Exception as e:
        logger.error(f"Error calling OpenAI API (Vision): {e}", exc_info=True)
        error_msg = (
            "Desculpe, ocorreu um erro ao processar a auditoria do seu bilhete. "
            "Certifique-se de que a imagem está legível e tente novamente."
        )
        try:
            await thinking_msg.edit_text(error_msg)
        except Exception:
            await update.message.reply_text(error_msg)
