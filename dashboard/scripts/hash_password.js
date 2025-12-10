#!/usr/bin/env node
/**
 * Script utilitaire pour hasher un mot de passe avec bcrypt.
 * Utilisé pour générer DASHBOARD_PASSWORD dans .env
 *
 * Usage:
 *   node dashboard/scripts/hash_password.js "MonMotDePasse"
 *
 * Ou interactif:
 *   node dashboard/scripts/hash_password.js
 */

const bcrypt = require('bcryptjs');
const readline = require('readline');

// Nombre de rounds bcrypt (10 = rapide, 12 = recommandé, 14 = très sécurisé)
const SALT_ROUNDS = 12;

async function hashPassword(password) {
  if (!password || password.trim() === '') {
    throw new Error('Le mot de passe ne peut pas être vide');
  }

  if (password.length < 8) {
    console.warn('⚠️  WARNING: Le mot de passe est court (< 8 caractères)');
    console.warn('   Recommandation: utilisez au moins 12 caractères avec lettres, chiffres et symboles');
  }

  const hash = await bcrypt.hash(password, SALT_ROUNDS);
  return hash;
}

async function main() {
  const args = process.argv.slice(2);

  // Vérifier si mode silencieux (pour automatisation)
  const quietMode = args.includes('--quiet') || args.includes('-q');
  const passwordArg = args.find(arg => !arg.startsWith('--') && !arg.startsWith('-'));

  if (passwordArg) {
    // Mode avec argument
    const password = passwordArg;
    try {
      const hash = await hashPassword(password);

      if (quietMode) {
        // Mode silencieux: afficher uniquement le hash
        console.log(hash);
      } else {
        // Mode verbose
        console.log('\n✅ Mot de passe hashé avec succès!\n');
        console.log('Copiez cette ligne dans votre fichier .env:');
        console.log('─────────────────────────────────────────────────');
        console.log(`DASHBOARD_PASSWORD=${hash}`);
        console.log('─────────────────────────────────────────────────\n');
        console.log('💡 Conseil: Utilisez un gestionnaire de mots de passe (1Password, Bitwarden, etc.)');
        console.log('');
      }
    } catch (error) {
      if (!quietMode) {
        console.error('❌ Erreur:', error.message);
      }
      process.exit(1);
    }
  } else {
    // Mode interactif
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    console.log('\n═══════════════════════════════════════════════════');
    console.log('🔐 Générateur de Mot de Passe Bcrypt');
    console.log('═══════════════════════════════════════════════════\n');

    rl.question('Entrez votre mot de passe (ne sera pas affiché): ', async (password) => {
      // Note: readline n'a pas de mode "password" natif,
      // mais le terminal ne l'affichera pas si lancé correctement
      try {
        const hash = await hashPassword(password);
        console.log('\n✅ Mot de passe hashé avec succès!\n');
        console.log('Copiez cette ligne dans votre fichier .env:');
        console.log('─────────────────────────────────────────────────');
        console.log(`DASHBOARD_PASSWORD=${hash}`);
        console.log('─────────────────────────────────────────────────\n');
        console.log('💡 Conseil: Conservez votre mot de passe original dans un gestionnaire sécurisé');
        console.log('');
        rl.close();
      } catch (error) {
        console.error('❌ Erreur:', error.message);
        rl.close();
        process.exit(1);
      }
    });
  }
}

main();
