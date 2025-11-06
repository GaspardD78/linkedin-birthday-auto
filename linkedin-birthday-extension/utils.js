// utils.js - Fonctions utilitaires partagées

import { TIMING, VALIDATION, STORAGE_KEYS, DEFAULT_TEMPLATES } from './constants.js';

/**
 * Fonction de délai (sleep)
 * @param {number} ms - Durée en millisecondes
 * @returns {Promise<void>}
 */
export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Génère un délai aléatoire entre min et max
 * @param {number} min - Délai minimum en ms
 * @param {number} max - Délai maximum en ms
 * @returns {number}
 */
export function randomDelay(min = TIMING.MIN_MESSAGE_DELAY, max = TIMING.MAX_MESSAGE_DELAY) {
  return min + Math.random() * (max - min);
}

/**
 * Extrait le prénom d'un nom complet
 * @param {string} fullName - Nom complet
 * @returns {string} - Prénom
 */
export function extractFirstName(fullName) {
  if (!fullName || typeof fullName !== 'string') {
    return '';
  }
  return fullName.trim().split(/\s+/)[0];
}

/**
 * Valide un nom
 * @param {string} name - Nom à valider
 * @returns {boolean}
 */
export function isValidName(name) {
  if (!name || typeof name !== 'string') {
    return false;
  }

  const trimmedName = name.trim();
  const length = trimmedName.length;

  return length >= VALIDATION.MIN_NAME_LENGTH &&
         length <= VALIDATION.MAX_NAME_LENGTH &&
         !trimmedName.toLowerCase().includes('célébrez') &&
         !trimmedName.toLowerCase().includes('anniversaire') &&
         !trimmedName.toLowerCase().includes('celebrate') &&
         !trimmedName.toLowerCase().includes('birthday');
}

/**
 * Valide un template de message
 * @param {string} template - Template à valider
 * @returns {object} - {isValid: boolean, error: string}
 */
export function validateTemplate(template) {
  if (!template || typeof template !== 'string') {
    return { isValid: false, error: 'Le message ne peut pas être vide' };
  }

  const trimmed = template.trim();

  if (trimmed.length < VALIDATION.MIN_MESSAGE_LENGTH) {
    return { isValid: false, error: 'Le message est trop court (minimum 10 caractères)' };
  }

  if (trimmed.length > VALIDATION.MAX_MESSAGE_LENGTH) {
    return { isValid: false, error: 'Le message est trop long (maximum 500 caractères)' };
  }

  if (!trimmed.includes('{prenom}')) {
    return { isValid: false, error: 'Le message doit contenir {prenom}' };
  }

  return { isValid: true, error: null };
}

/**
 * Génère un message personnalisé à partir d'un template
 * @param {string} firstName - Prénom
 * @param {string} template - Template de message
 * @returns {string} - Message personnalisé
 */
export function generateMessage(firstName, template) {
  if (!firstName || !template) {
    return '';
  }
  return template.replace(/\{prenom\}/g, firstName);
}

/**
 * Sélectionne un template aléatoire
 * @param {Array<string>} templates - Liste de templates
 * @returns {string} - Template sélectionné
 */
export function selectRandomTemplate(templates) {
  if (!templates || templates.length === 0) {
    return DEFAULT_TEMPLATES[0];
  }
  return templates[Math.floor(Math.random() * templates.length)];
}

/**
 * Modifie l'URL de message pour inclure le texte
 * @param {string} originalUrl - URL originale
 * @param {string} message - Message à inclure
 * @returns {string} - URL modifiée
 */
export function modifyMessageUrl(originalUrl, message) {
  if (!originalUrl || !message) {
    return originalUrl;
  }

  const encodedMessage = encodeURIComponent(message);

  // Si l'URL contient déjà un body, le remplacer
  if (originalUrl.includes('body=')) {
    const parts = originalUrl.split('body=');
    const basePart = parts[0];
    const rest = parts[1].split('&');
    const otherParams = rest.slice(1).join('&');

    let newUrl = basePart + 'body=' + encodedMessage;
    if (otherParams) {
      newUrl += '&' + otherParams;
    }
    return newUrl;
  } else {
    // Ajouter le body
    const separator = originalUrl.includes('?') ? '&' : '?';
    return originalUrl + separator + 'body=' + encodedMessage;
  }
}

/**
 * Récupère les templates depuis le storage
 * @returns {Promise<Array<string>>}
 */
export function getMessageTemplates() {
  return new Promise((resolve, reject) => {
    try {
      chrome.storage.sync.get([STORAGE_KEYS.MESSAGE_TEMPLATES], (result) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        const templates = result[STORAGE_KEYS.MESSAGE_TEMPLATES] || DEFAULT_TEMPLATES;
        resolve(templates);
      });
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * Sauvegarde les templates dans le storage
 * @param {Array<string>} templates - Templates à sauvegarder
 * @returns {Promise<void>}
 */
export function saveMessageTemplates(templates) {
  return new Promise((resolve, reject) => {
    try {
      chrome.storage.sync.set({
        [STORAGE_KEYS.MESSAGE_TEMPLATES]: templates
      }, () => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve();
      });
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * Vérifie si un message a déjà été envoyé aujourd'hui
 * @param {string} contactName - Nom du contact
 * @returns {Promise<boolean>}
 */
export async function isAlreadySentToday(contactName) {
  return new Promise((resolve) => {
    chrome.storage.local.get([STORAGE_KEYS.SENT_HISTORY], (result) => {
      const history = result[STORAGE_KEYS.SENT_HISTORY] || {};
      const today = new Date().toISOString().split('T')[0];
      const todaysSent = history[today] || [];
      resolve(todaysSent.includes(contactName));
    });
  });
}

/**
 * Marque un contact comme ayant reçu un message aujourd'hui
 * @param {string} contactName - Nom du contact
 * @returns {Promise<void>}
 */
export async function markAsSentToday(contactName) {
  return new Promise((resolve) => {
    chrome.storage.local.get([STORAGE_KEYS.SENT_HISTORY], (result) => {
      const history = result[STORAGE_KEYS.SENT_HISTORY] || {};
      const today = new Date().toISOString().split('T')[0];

      if (!history[today]) {
        history[today] = [];
      }

      if (!history[today].includes(contactName)) {
        history[today].push(contactName);
      }

      // Nettoyer l'historique (garder seulement les 7 derniers jours)
      const dates = Object.keys(history);
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - 7);
      const cutoffStr = cutoffDate.toISOString().split('T')[0];

      dates.forEach(date => {
        if (date < cutoffStr) {
          delete history[date];
        }
      });

      chrome.storage.local.set({ [STORAGE_KEYS.SENT_HISTORY]: history }, resolve);
    });
  });
}

/**
 * Formatte un nombre pour l'affichage
 * @param {number} num - Nombre à formatter
 * @returns {string}
 */
export function formatNumber(num) {
  return new Intl.NumberFormat('fr-FR').format(num);
}

/**
 * Formatte une date pour l'affichage
 * @param {string|Date} date - Date à formatter
 * @returns {string}
 */
export function formatDate(date) {
  if (!date) return 'Jamais';

  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
}

/**
 * Logger avec timestamp
 * @param {string} level - Niveau de log (info, warn, error)
 * @param {string} message - Message à logger
 * @param {any} data - Données additionnelles
 */
export function log(level, message, data = null) {
  const timestamp = new Date().toISOString();
  const prefix = `[LinkedIn Birthday Bot ${timestamp}]`;

  switch (level) {
    case 'info':
      console.log(`${prefix} ℹ️ ${message}`, data || '');
      break;
    case 'warn':
      console.warn(`${prefix} ⚠️ ${message}`, data || '');
      break;
    case 'error':
      console.error(`${prefix} ❌ ${message}`, data || '');
      break;
    default:
      console.log(`${prefix} ${message}`, data || '');
  }
}
