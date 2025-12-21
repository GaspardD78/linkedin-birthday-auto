# Image PI-SECURITY-HASH pour Raspberry Pi ARM64
FROM node:20-bookworm-slim

# Pas de npm init interactif, structure minimale
WORKDIR /app

# Installation explicite de bcryptjs (pas de compilateur nécessaire)
# On utilise --save pour créer package.json/lock.json implicites pour la propreté
RUN npm init -y --silent && \
    npm i bcryptjs@2.4.3 --save --production && \
    npm cache clean --force

# Entry point : hashage synchrone sécurisé
# Prend le mot de passe en argument ou via stdin ou ENV
ENTRYPOINT ["node", "-e", "\
const bcrypt = require('bcryptjs'); \
const password = process.argv[1] || process.env.PASSWORD; \
if (!password) { \
  console.error('Missing password'); \
  process.exit(1); \
} \
try { \
  console.log(bcrypt.hashSync(password, 12)); \
} catch (e) { \
  console.error(e); \
  process.exit(1); \
} \
"]
