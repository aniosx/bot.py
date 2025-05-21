#!/usr/bin/env python

-- coding: utf-8 --

import os import json import time import random import string import logging import threading from flask import Flask from dotenv import load_dotenv from telegram import Update from telegram.ext import ( Updater, CommandHandler, MessageHandler, Filters, CallbackContext )

Configuration du logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO) logger = logging.getLogger(name)

Charger les variables d'environnement

load_dotenv() TOKEN = os.getenv("TELEGRAM_TOKEN") OWNER_ID = int(os.getenv("OWNER_ID", "123456")) PORT = int(os.environ.get('PORT', 8080))

Fichiers de données

USERS_FILE = "users.json" BLOCKED_FILE = "blocked_users.json" CONFIG_FILE = "config.json"

Charger données persistantes

def load_json(filename, default): try: if os.path.exists(filename): with open(filename, 'r') as f: return json.load(f) except: pass return default

def save_json(filename, data): try: with open(filename, 'w') as f: json.dump(data, f) except Exception as e: logger.error(f"Erreur en sauvegardant {filename}: {e}")

users = load_json(USERS_FILE, {}) blocked = set(load_json(BLOCKED_FILE, [])) config = load_json(CONFIG_FILE, {"require_password": False, "password": ""}) message_log = {}  # Pour anti-spam

Flask app pour Render

app = Flask(name) @app.route('/') def index(): return 'Bot actif'

def generate_alias(): return "USER" + ''.join(random.choices(string.digits, k=4))

def get_alias(user_id): if str(user_id) not in users: alias = generate_alias() while alias in users.values(): alias = generate_alias() users[str(user_id)] = alias save_json(USERS_FILE, users) return users[str(user_id)]

def is_allowed(user_id): return str(user_id) not in blocked

def is_spamming(user_id): now = time.time() if user_id not in message_log: message_log[user_id] = [] message_log[user_id] = [t for t in message_log[user_id] if now - t < 60] if len(message_log[user_id]) >= 6: return True message_log[user_id].append(now) return False

def start(update: Update, context: CallbackContext): user = update.effective_user if not is_allowed(user.id): return update.message.reply_text("Vous êtes bloqué.")

if config.get("require_password") and str(user.id) not in users:
    context.user_data['awaiting_password'] = True
    return update.message.reply_text("Veuillez entrer le mot de passe pour accéder au salon.")

alias = get_alias(user.id)
update.message.reply_text(f"Bienvenue {alias}. Vous êtes dans le salon anonyme.")

def handle_message(update: Update, context: CallbackContext): user = update.effective_user text = update.message.text

if not is_allowed(user.id):
    return update.message.reply_text("Vous êtes bloqué.")

if context.user_data.get('awaiting_password'):
    if text == config.get("password"):
        context.user_data['awaiting_password'] = False
        alias = get_alias(user.id)
        update.message.reply_text(f"Mot de passe accepté. Bienvenue {alias}.")
    else:
        update.message.reply_text("Mot de passe incorrect.")
    return

if str(user.id) not in users:
    update.message.reply_text("Vous devez d'abord envoyer /start.")
    return

if is_spamming(user.id):
    return update.message.reply_text("Trop de messages. Veuillez ralentir.")

alias = get_alias(user.id)
for uid in users:
    if uid != str(user.id) and uid not in blocked:
        try:
            context.bot.send_message(chat_id=int(uid), text=f"{alias} : {text}")
        except:
            pass

Commandes admin

def help_command(update: Update, context: CallbackContext): if update.effective_user.id != OWNER_ID: return update.message.reply_text( "/help - Affiche cette aide\n" "/users - Liste des utilisateurs\n" "/block <alias> - Bloque un utilisateur\n" "/unblock <alias> - Débloque un utilisateur\n" "/stats - Stats\n" "/setpassword <mot> - Active le mot de passe\n" "/disablepassword - Désactive le mot de passe" )

def users_command(update: Update, context: CallbackContext): if update.effective_user.id != OWNER_ID: return msg = "Utilisateurs:\n" for uid, alias in users.items(): status = "(bloqué)" if uid in blocked else "(actif)" msg += f"{alias} {status}\n" update.message.reply_text(msg)

def block_command(update: Update, context: CallbackContext): if update.effective_user.id != OWNER_ID: return if not context.args: return update.message.reply_text("Usage: /block USER1234") alias = context.args[0] for uid, a in users.items(): if a == alias: blocked.add(uid) save_json(BLOCKED_FILE, list(blocked)) return update.message.reply_text(f"{alias} bloqué.") update.message.reply_text("Alias introuvable.")

def unblock_command(update: Update, context: CallbackContext): if update.effective_user.id != OWNER_ID: return if not context.args: return update.message.reply_text("Usage: /unblock USER1234") alias = context.args[0] for uid, a in users.items(): if a == alias: blocked.discard(uid) save_json(BLOCKED_FILE, list(blocked)) return update.message.reply_text(f"{alias} débloqué.") update.message.reply_text("Alias introuvable.")

def stats_command(update: Update, context: CallbackContext): if update.effective_user.id != OWNER_ID: return update.message.reply_text( f"Total utilisateurs: {len(users)}\nBloqués: {len(blocked)}" )

def set_password(update: Update, context: CallbackContext): if update.effective_user.id != OWNER_ID: return if not context.args: return update.message.reply_text("Usage: /setpassword mot") config["require_password"] = True config["password"] = context.args[0] save_json(CONFIG_FILE, config) update.message.reply_text("Mot de passe activé.")

def disable_password(update: Update, context: CallbackContext): if update.effective_user.id != OWNER_ID: return config["require_password"] = False config["password"] = "" save_json(CONFIG_FILE, config) update.message.reply_text("Mot de passe désactivé.")

def main(): updater = Updater(TOKEN) dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("help", help_command))
dp.add_handler(CommandHandler("users", users_command))
dp.add_handler(CommandHandler("block", block_command))
dp.add_handler(CommandHandler("unblock", unblock_command))
dp.add_handler(CommandHandler("stats", stats_command))
dp.add_handler(CommandHandler("setpassword", set_password))
dp.add_handler(CommandHandler("disablepassword", disable_password))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

flask_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': PORT})
flask_thread.daemon = True
flask_thread.start()

updater.start_polling()
updater.idle()

if name == 'main': main()
