#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import threading
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler
)

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()

# Configuration du bot
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("Le token TELEGRAM_TOKEN est manquant dans les variables d'environnement.")
OWNER_ID = int(os.getenv('OWNER_ID', '144262846'))
PORT = int(os.environ.get('PORT', 8080))

# Dictionnaire pour stocker les messages et leurs expéditeurs
message_registry = {}

# Liste des utilisateurs bloqués (en mémoire)
blocked_users = set()

# Fichier pour stocker les utilisateurs bloqués
BLOCKED_USERS_FILE = 'blocked_users.json'

# Créer une application Flask pour le ping
app = Flask(__name__)

@app.route('/')
def index():
    return 'Bot Telegram en ligne!'

def load_blocked_users():
    """Charge la liste des utilisateurs bloqués depuis le fichier."""
    global blocked_users
    try:
        if os.path.exists(BLOCKED_USERS_FILE):
            with open(BLOCKED_USERS_FILE, 'r') as f:
                blocked_list = json.load(f)
                blocked_users = set(blocked_list)
                logger.info(f"Loaded {len(blocked_users)} blocked users from file")
    except Exception as e:
        logger.error(f"Error loading blocked users: {e}")

def save_blocked_users():
    """Sauvegarde la liste des utilisateurs bloqués dans le fichier."""
    try:
        with open(BLOCKED_USERS_FILE, 'w') as f:
            json.dump(list(blocked_users), f)
            logger.info(f"Saved {len(blocked_users)} blocked users to file")
    except Exception as e:
        logger.error(f"Error saving blocked users: {e}")

def start(update: Update, context: CallbackContext) -> None:
    """Gestionnaire de la commande /start."""
    user = update.effective_user
    
    # Vérifier si l'utilisateur est bloqué
    if user.id in blocked_users and user.id != OWNER_ID:
        update.message.reply_text(
            "Vous avez été bloqué et ne pouvez pas utiliser ce bot."
        )
        return
    
    update.message.reply_text(
        f'Bonjour {user.first_name} ! Je suis un bot de relais de messages. '
        f'Envoyez-moi un message et il sera transmis au propriétaire du bot.'
    )
    
    # Informer le propriétaire qu'un nouvel utilisateur a démarré le bot
    if user.id != OWNER_ID:
        context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"Nouvel utilisateur: {user.first_name} (@{user.username or 'Sans username'}) [ID: {user.id}] a démarré le bot."
        )

def help_command(update: Update, context: CallbackContext) -> None:
    """Gestionnaire de la commande /help."""
    user = update.effective_user
    
    # Vérifier si l'utilisateur est bloqué
    if user.id in blocked_users and user.id != OWNER_ID:
        update.message.reply_text(
            "Vous avez été bloqué et ne pouvez pas utiliser ce bot."
        )
        return
    
    # Message d'aide pour les utilisateurs normaux
    help_text = (
        'Commandes disponibles:\n'
        '/start - Démarrer le bot\n'
        '/help - Afficher ce message d\'aide\n\n'
        'Pour utiliser ce bot, envoyez simplement un message et il sera transmis au propriétaire.'
    )
    
    # Ajouter les commandes de gestion pour le propriétaire
    if user.id == OWNER_ID:
        help_text += (
            '\n\nCommandes de gestion (propriétaire uniquement):\n'
            '/block [user_id] - Bloquer un utilisateur\n'
            '/unblock [user_id] - Débloquer un utilisateur\n'
            '/blocklist - Afficher la liste des utilisateurs bloqués'
        )
    
    update.message.reply_text(help_text)

def block_user(update: Update, context: CallbackContext) -> None:
    """Gestionnaire de la commande /block pour bloquer un utilisateur."""
    user = update.effective_user
    
    # Vérifier que c'est bien le propriétaire qui utilise cette commande
    if user.id != OWNER_ID:
        update.message.reply_text("Cette commande est réservée au propriétaire du bot.")
        return
    
    # Vérifier qu'un ID utilisateur a été fourni
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text(
            "Veuillez spécifier l'ID de l'utilisateur à bloquer.\n"
            "Exemple: /block 123456789"
        )
        return
    
    # Récupérer l'ID utilisateur et le bloquer
    user_id = int(context.args[0])
    
    # Ne pas permettre de bloquer le propriétaire
    if user_id == OWNER_ID:
        update.message.reply_text("Vous ne pouvez pas vous bloquer vous-même.")
        return
    
    blocked_users.add(user_id)
    save_blocked_users()
    
    update.message.reply_text(f"L'utilisateur avec l'ID {user_id} a été bloqué.")

def unblock_user(update: Update, context: CallbackContext) -> None:
    """Gestionnaire de la commande /unblock pour débloquer un utilisateur."""
    user = update.effective_user
    
    # Vérifier que c'est bien le propriétaire qui utilise cette commande
    if user.id != OWNER_ID:
        update.message.reply_text("Cette commande est réservée au propriétaire du bot.")
        return
    
    # Vérifier qu'un ID utilisateur a été fourni
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text(
            "Veuillez spécifier l'ID de l'utilisateur à débloquer.\n"
            "Exemple: /unblock 123456789"
        )
        return
    
    # Récupérer l'ID utilisateur et le débloquer
    user_id = int(context.args[0])
    
    if user_id in blocked_users:
        blocked_users.remove(user_id)
        save_blocked_users()
        update.message.reply_text(f"L'utilisateur avec l'ID {user_id} a été débloqué.")
    else:
        update.message.reply_text(f"L'utilisateur avec l'ID {user_id} n'est pas bloqué.")

def blocklist(update: Update, context: CallbackContext) -> None:
    """Gestionnaire de la commande /blocklist pour afficher la liste des utilisateurs bloqués."""
    user = update.effective_user
    
    # Vérifier que c'est bien le propriétaire qui utilise cette commande
    if user.id != OWNER_ID:
        update.message.reply_text("Cette commande est réservée au propriétaire du bot.")
        return
    
    if not blocked_users:
        update.message.reply_text("Aucun utilisateur n'est bloqué.")
        return
    
    blocklist_text = "Liste des utilisateurs bloqués:\n"
    for blocked_id in blocked_users:
        blocklist_text += f"- ID: {blocked_id}\n"
    
    update.message.reply_text(blocklist_text)

def forward_message(update: Update, context: CallbackContext) -> None:
    """Transmet les messages des utilisateurs au propriétaire."""
    user = update.effective_user
    message = update.message
    
    # Ne pas traiter les messages du propriétaire comme des messages à transférer
    if user.id == OWNER_ID:
        return
    
    # Vérifier si l'utilisateur est bloqué
    if user.id in blocked_users:
        update.message.reply_text(
            "Vous avez été bloqué et ne pouvez pas envoyer de messages via ce bot."
        )
        return
    
    # Préparer les informations sur l'expéditeur
    sender_info = (
        f"Message de: {user.first_name} {user.last_name or ''}\n"
        f"Username: @{user.username or 'Sans username'}\n"
        f"ID: {user.id}\n"
        f"----------------------------\n"
    )
    
    # Créer des boutons pour répondre et bloquer
    reply_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Répondre", callback_data=f"reply_{user.id}_{message.message_id}"),
            InlineKeyboardButton("Bloquer", callback_data=f"block_{user.id}")
        ]
    ])
    
    # Transmettre différents types de messages
    if message.text:
        # Message texte
        forwarded = context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"{sender_info}Message: {message.text}",
            reply_markup=reply_keyboard
        )
        # Enregistrer le message pour les réponses futures
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    elif message.photo:
        # Photo
        photo = message.photo[-1]  # Prendre la photo de meilleure qualité
        caption = message.caption or "Sans légende"
        forwarded = context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=photo.file_id,
            caption=f"{sender_info}Légende: {caption}",
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    elif message.document:
        # Document
        forwarded = context.bot.send_document(
            chat_id=OWNER_ID,
            document=message.document.file_id,
            caption=f"{sender_info}Document: {message.document.file_name or 'Sans nom'}",
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    elif message.video:
        # Vidéo
        forwarded = context.bot.send_video(
            chat_id=OWNER_ID,
            video=message.video.file_id,
            caption=f"{sender_info}Vidéo: {message.caption or 'Sans légende'}",
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    elif message.voice:
        # Message vocal
        forwarded = context.bot.send_voice(
            chat_id=OWNER_ID,
            voice=message.voice.file_id,
            caption=f"{sender_info}Message vocal",
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    elif message.audio:
        # Audio
        forwarded = context.bot.send_audio(
            chat_id=OWNER_ID,
            audio=message.audio.file_id,
            caption=f"{sender_info}Audio: {message.audio.title or 'Sans titre'}",
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    elif message.sticker:
        # Sticker
        forwarded = context.bot.send_sticker(
            chat_id=OWNER_ID,
            sticker=message.sticker.file_id
        )
        context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"{sender_info}Sticker envoyé",
            reply_to_message_id=forwarded.message_id,
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    else:
        update.message.reply_text("Ce type de message n'est pas encore pris en charge.")

        context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"{sender_info}Message de type non pris en charge",
            reply_markup=reply_keyboard
        )
    
    # Confirmer la réception à l'utilisateur
    update.message.reply_text("Votre message a été transmis.")

def handle_reply_button(update: Update, context: CallbackContext) -> None:
    """Gère les clics sur les boutons inline."""
    query = update.callback_query
    query.answer()
    
    # Vérifier que c'est bien le propriétaire qui répond
    if query.from_user.id != OWNER_ID:
        query.edit_message_reply_markup(None)
        context.bot.send_message(
            chat_id=query.from_user.id,
            text="Seul le propriétaire du bot peut utiliser ces boutons."
        )
        return
    
    # Extraire les données du callback
    data = query.data.split("_")
    
    # Gérer le bouton de réponse
    if len(data) >= 3 and data[0] == "reply":
        user_id = int(data[1])
        
        # Demander la réponse au propriétaire
        context.user_data["reply_to"] = user_id
        context.user_data["original_message"] = query.message.message_id
        
        query.edit_message_reply_markup(None)
        context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"Répondez à ce message pour envoyer votre réponse à l'utilisateur ID: {user_id}",
            reply_to_message_id=query.message.message_id
        )
    
    # Gérer le bouton de blocage
    elif len(data) >= 2 and data[0] == "block":
        user_id = int(data[1])
        
        # Ne pas permettre de bloquer le propriétaire
        if user_id == OWNER_ID:
            context.bot.send_message(
                chat_id=OWNER_ID,
                text="Vous ne pouvez pas vous bloquer vous-même."
            )
            return
        
        # Bloquer l'utilisateur
        blocked_users.add(user_id)
        save_blocked_users()
        
        query.edit_message_reply_markup(None)
        context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"L'utilisateur avec l'ID {user_id} a été bloqué."
        )

def handle_owner_reply(update: Update, context: CallbackContext) -> None:
    """Gère les réponses du propriétaire aux messages transmis."""
    user = update.effective_user
    message = update.message
    
    # Vérifier que c'est bien le propriétaire qui répond
    if user.id != OWNER_ID:
        return
    
    # Vérifier si le message est une réponse
    if message.reply_to_message:
        replied_msg_id = str(message.reply_to_message.message_id)
        
        # Vérifier si le message original est dans notre registre
        if replied_msg_id in message_registry:
            target_user_id = message_registry[replied_msg_id]["user_id"]
            
            # Vérifier si l'utilisateur cible est bloqué
            if target_user_id in blocked_users:
                context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"Cet utilisateur (ID: {target_user_id}) est bloqué. Débloquezle avec /unblock {target_user_id} pour lui envoyer des messages.",
                    reply_to_message_id=message.message_id
                )
                return
            
            # Envoyer la réponse à l'utilisateur d'origine
            try:
                if message.text:
                    context.bot.send_message(
                        chat_id=target_user_id,
                        text=f"Réponse du propriétaire: {message.text}"
                    )
                elif message.photo:
                    photo = message.photo[-1]
                    caption = message.caption or "Sans légende"
                    context.bot.send_photo(
                        chat_id=target_user_id,
                        photo=photo.file_id,
                        caption=f"Réponse du propriétaire: {caption}"
                    )
                elif message.document:
                    context.bot.send_document(
                        chat_id=target_user_id,
                        document=message.document.file_id,
                        caption=f"Réponse du propriétaire: {message.caption or ''}"
                    )
                elif message.video:
                    context.bot.send_video(
                        chat_id=target_user_id,
                        video=message.video.file_id,
                        caption=f"Réponse du propriétaire: {message.caption or ''}"
                    )
                elif message.voice:
                    context.bot.send_voice(
                        chat_id=target_user_id,
                        voice=message.voice.file_id,
                        caption="Réponse vocale du propriétaire"
                    )
                elif message.audio:
                    context.bot.send_audio(
                        chat_id=target_user_id,
                        audio=message.audio.file_id,
                        caption=f"Réponse audio du propriétaire: {message.caption or ''}"
                    )
                elif message.sticker:
                    context.bot.send_sticker(
                        chat_id=target_user_id,
                        sticker=message.sticker.file_id
                    )
                else:
                    context.bot.send_message(
                        chat_id=target_user_id,
                        text="Le propriétaire a répondu avec un type de message non pris en charge."
                    )
                
                # Confirmer l'envoi au propriétaire
                context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"Votre réponse a été envoyée à l'utilisateur ID: {target_user_id}",
                    reply_to_message_id=message.message_id
                )
            
            except Exception as e:
                context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"Erreur lors de l'envoi de la réponse: {str(e)}",
                    reply_to_message_id=message.message_id
                )

def error_handler(update: Update, context: CallbackContext) -> None:
    """Gère les erreurs rencontrées par le dispatcher."""
    logger.exception("Une erreur est survenue pendant le traitement de la mise à jour.", exc_info=context.error)
    if update and update.effective_chat:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Une erreur est survenue. Veuillez réessayer plus tard."
        )

def run_flask():
    """Exécute l'application Flask pour le ping."""
    app.run(host='0.0.0.0', port=PORT)

def main() -> None:
    """Fonction principale pour démarrer le bot."""
    # Charger la liste des utilisateurs bloqués
    load_blocked_users()
    
    # Créer l'Updater et passer le token du bot
    updater = Updater(TOKEN)
    
    # Récupérer le dispatcher pour enregistrer les gestionnaires
    dispatcher = updater.dispatcher
    
    # Gestionnaires de commandes
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    # Gestionnaires pour les commandes de blocage
    dispatcher.add_handler(CommandHandler("block", block_user))
    dispatcher.add_handler(CommandHandler("unblock", unblock_user))
    dispatcher.add_handler(CommandHandler("blocklist", blocklist))
    
    # Gestionnaire pour les boutons inline
    dispatcher.add_handler(CallbackQueryHandler(handle_reply_button))
    
    # Gestionnaire pour les réponses du propriétaire
    dispatcher.add_handler(MessageHandler(
        Filters.reply & Filters.user(OWNER_ID),
        handle_owner_reply
    ))
    
    # Gestionnaire pour tous les autres messages
    dispatcher.add_handler(MessageHandler(
        Filters.text | Filters.photo | Filters.document | Filters.video |
        Filters.voice | Filters.audio | Filters.sticker,
        forward_message
    ))
    
    # Gestionnaire d'erreurs
    dispatcher.add_error_handler(error_handler)
    
    # Démarrer le serveur Flask dans un thread séparé pour le ping
    flask_thread = threading.Thread(target=run_flask)
    PORT = int(os.environ.get('PORT', 10000))
    flask_thread.daemon = True
    flask_thread.start()
    
    # Démarrer le bot
    updater.start_polling()
    logger.info("Bot démarré. Appuyez sur Ctrl+C pour arrêter.")
    
    # Maintenir le bot en fonctionnement jusqu'à l'interruption
    updater.idle()

if __name__ == '__main__':
    main()
