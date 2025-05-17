# Bot Telegram de relais de messages

Ce bot permet aux utilisateurs de vous envoyer des messages (texte, photo, audio, etc.) via Telegram, que vous pouvez consulter et auxquels vous pouvez répondre en tant que propriétaire.

## Fonctionnalités principales

- Transfert automatique des messages utilisateurs au propriétaire
- Bouton pour répondre ou bloquer un utilisateur
- Gestion des utilisateurs bloqués (/block, /unblock, /blocklist)

## Installation

1. Clonez ce dépôt :
```bash
git clone https://github.com/votre-utilisateur/nom-du-bot.git
cd nom-du-bot
```

2. Créez un fichier `.env` :
```bash
cp .env.example .env
# Modifiez les valeurs dans .env
```

3. Installez les dépendances :
```bash
pip install -r requirements.txt
```

4. Lancez le bot :
```bash
python bot_corrected.py
```

## Déploiement

Pour déployer sur Heroku, Render ou Railway, exposez le port 8080 et assurez-vous que le fichier `blocked_users.json` est bien accessible.

## Sécurité

Ne partagez jamais votre token Telegram. Utilisez des variables d’environnement pour protéger vos identifiants.

---

Fait avec amour et Python.
