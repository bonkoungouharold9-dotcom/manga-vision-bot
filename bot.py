import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import database

# Variables lues depuis les paramètres de l'hébergeur
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID", "0").strip())
FORCE_SUB_CHANNEL_ID = int(os.getenv("FORCE_SUB_CHANNEL_ID", "0").strip())
FORCE_SUB_URL = os.getenv("FORCE_SUB_URL", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip().replace("@", "")

async def is_subscribed(bot, user_id):
    """Vérifie si l'utilisateur est abonné au canal officiel"""
    if FORCE_SUB_CHANNEL_ID == 0:
        return True
    try:
        member = await bot.get_chat_member(chat_id=FORCE_SUB_CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Erreur vérification abonnement: {e}")
        return True

# 1. AUTO-INDEXATION : Détection automatique des fichiers dans le canal privé
async def auto_index(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post
    if not msg:
        return

    file_name = None
    file_id = None
    file_type = "document"

    if msg.document:
        file_name = msg.document.file_name or msg.caption
        file_id = msg.document.file_id
        file_type = "document"
    elif msg.video:
        file_name = msg.caption or "Vidéo sans titre"
        file_id = msg.video.file_id
        file_type = "video"

    if file_name and file_id:
        database.save_file(file_id, file_name, file_type, msg.message_id)
        print(f"✅ Nouveau manga indexé : {file_name}")

# 2. RECHERCHE DANS LE GROUPE : Déclenchée quand un membre écrit un mot
async def handle_group_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    query = update.message.text.strip()
    if len(query) < 2 or query.startswith("/"):
        return

    results = database.search_files(query)

    if not results:
        text_not_found = (
            f"🔍 Cible : « *{query}* »\n\n"
            "⚠️ Ce manga n'est pas encore disponible dans la base.\n"
            "💡 Il sera ajouté très prochainement par les administrateurs !"
        )
        await update.message.reply_text(text_not_found, parse_mode="Markdown")
        return

    text_found = (
        "🎬 *RÉSULTATS DE RECHERCHE*\n\n"
        f"🔍 Cible : « *{query}* »\n"
        "👤 Statut : 👤 Standard\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎬 CATÉGORIE : MANGA / VF\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Cliquez sur un lien ci-dessous pour recevoir le contenu en privé :*"
    )

    buttons = []
    for item in results:
        btn_url = f"https://t.me/{BOT_USERNAME}?start=file_{str(item['_id'])}"
        buttons.append([InlineKeyboardButton(f"📥 {item['file_name']}", url=btn_url)])

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(text_found, reply_markup=reply_markup, parse_mode="Markdown")

# 3. DISTRIBUTION EN PRIVÉ (/start)
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    args = context.args

    # Vérification de l'abonnement
    subscribed = await is_subscribed(context.bot, user.id)
    if not subscribed:
        start_param = args[0] if args else ""
        text_sub = (
            "⚠️ *Accès Refusé*\n\n"
            "Pour accéder aux mangas et vidéos gratuitement, vous devez d'abord rejoindre notre canal officiel !"
        )
        buttons = [
            [InlineKeyboardButton("📢 Rejoindre le Canal", url=FORCE_SUB_URL)],
            [InlineKeyboardButton("🔄 Réessayer", url=f"https://t.me/{BOT_USERNAME}?start={start_param}")]
        ]
        await update.message.reply_text(text_sub, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
        return

    # Si l'utilisateur clique sur un manga trouvé
    if args and args[0].startswith("file_"):
        file_ref = args[0].replace("file_", "")
        manga = database.get_file_by_id(file_ref)
        if manga:
            try:
                await context.bot.copy_message(
                    chat_id=user.id,
                    from_chat_id=DB_CHANNEL_ID,
                    message_id=manga["message_id"]
                )
                await update.message.reply_text("✅ Bon visionnage / bonne lecture sur Manga Vision 🍿")
            except Exception as e:
                print(f"Erreur envoi: {e}")
                await update.message.reply_text("❌ Une erreur est survenue lors de l'envoi du fichier.")
        else:
            await update.message.reply_text("❌ Fichier introuvable ou supprimé.")
    else:
        await update.message.reply_text(
            "👋 Bienvenue sur *Manga Vision* !\n"
            "Tapez le nom d'un animé ou scan dans notre groupe pour recevoir votre fichier.",
            parse_mode="Markdown"
        )

def main():
    if not BOT_TOKEN:
        print("❌ ERREUR: BOT_TOKEN manquant !")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Indexation depuis le canal privé
    app.add_handler(MessageHandler(filters.Chat(chat_id=DB_CHANNEL_ID) & (filters.Document.ALL | filters.VIDEO), auto_index))

    # Recherche dans le groupe
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & (~filters.COMMAND), handle_group_search))

    # Commande /start
    app.add_handler(CommandHandler("start", start_handler))

    print("⚡️ Bot Manga Vision en marche !")
    app.run_polling()

if __name__ == "__main__":
    main()
