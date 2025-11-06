// content.js - Script injecté dans la page LinkedIn (Version améliorée)

import {
  SELECTORS,
  ERROR_MESSAGES,
  TIMING
} from './constants.js';

import {
  sleep,
  randomDelay,
  extractFirstName,
  isValidName,
  generateMessage,
  selectRandomTemplate,
  modifyMessageUrl,
  getMessageTemplates,
  isAlreadySentToday,
  markAsSentToday,
  log
} from './utils.js';

// ============================================================================
// MESSAGE HANDLERS
// ============================================================================

/**
 * Écouter les messages de la popup
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'scanBirthdays') {
    handleScanBirthdays(sendResponse);
    return true; // Réponse asynchrone
  }

  if (request.action === 'sendAllMessages') {
    handleSendAllMessages(sendResponse);
    return true; // Réponse asynchrone
  }
});

/**
 * Handler pour le scan des anniversaires
 * @param {Function} sendResponse - Fonction de callback
 */
async function handleScanBirthdays(sendResponse) {
  try {
    const birthdays = await scanBirthdays();
    sendResponse({ success: true, birthdays });
  } catch (error) {
    log('error', 'Scan failed', error);
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Handler pour l'envoi de tous les messages
 * @param {Function} sendResponse - Fonction de callback
 */
async function handleSendAllMessages(sendResponse) {
  try {
    const result = await sendAllMessages();
    sendResponse({ success: true, sent: result.sent, skipped: result.skipped });
  } catch (error) {
    log('error', 'Send all failed', error);
    sendResponse({ success: false, error: error.message });
  }
}

// ============================================================================
// DOM EXTRACTION UTILITIES
// ============================================================================

/**
 * Extrait le nom d'une carte d'anniversaire
 * @param {HTMLElement} card - Élément DOM de la carte
 * @returns {string|null} - Nom extrait ou null
 */
function extractNameFromCard(card) {
  // Essayer chaque sélecteur dans l'ordre de priorité
  for (const selector of SELECTORS.NAME_SELECTORS) {
    try {
      const elements = card.querySelectorAll(selector);
      for (const element of elements) {
        const text = element.textContent.trim();
        if (isValidName(text)) {
          log('info', `Name found with selector: ${selector}`, text);
          return text;
        }
      }
    } catch (error) {
      log('warn', `Selector failed: ${selector}`, error);
    }
  }

  // Fallback: chercher tous les paragraphes
  const paragraphs = card.querySelectorAll('p, span, div[class*="name"]');
  for (const element of paragraphs) {
    const text = element.textContent.trim();
    if (isValidName(text)) {
      log('info', 'Name found with fallback selector', text);
      return text;
    }
  }

  return null;
}

/**
 * Trouve le lien de message dans une carte
 * @param {HTMLElement} card - Élément DOM de la carte
 * @returns {HTMLElement|null} - Élément de lien ou null
 */
function findMessageLink(card) {
  for (const selector of SELECTORS.MESSAGE_BUTTON_SELECTORS) {
    try {
      const link = card.querySelector(selector);
      if (link && link.getAttribute('href')) {
        log('info', `Message link found with selector: ${selector}`);
        return link;
      }
    } catch (error) {
      log('warn', `Message link selector failed: ${selector}`, error);
    }
  }

  return null;
}

/**
 * Extrait les informations d'une carte d'anniversaire
 * @param {HTMLElement} card - Élément DOM de la carte
 * @returns {Object|null} - Objet contenant name, messageLink, card ou null
 */
function extractBirthdayInfo(card) {
  try {
    const name = extractNameFromCard(card);
    if (!name) {
      log('warn', 'No valid name found in card');
      return null;
    }

    const messageLink = findMessageLink(card);
    if (!messageLink) {
      log('warn', `No message link found for ${name}`);
      return null;
    }

    return {
      name,
      messageLink,
      card
    };
  } catch (error) {
    log('error', 'Error extracting birthday info', error);
    return null;
  }
}

// ============================================================================
// PAGE INTERACTION
// ============================================================================

/**
 * Scrolle la page pour charger tous les éléments
 * @returns {Promise<void>}
 */
async function scrollPage() {
  log('info', 'Scrolling page to load all content');

  for (let i = 0; i < TIMING.SCROLL_ITERATIONS; i++) {
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(TIMING.SCROLL_DELAY);
  }

  // Retour en haut
  window.scrollTo(0, 0);
  await sleep(TIMING.SCROLL_DELAY / 2);

  log('info', 'Page scrolling completed');
}

/**
 * Scrolle vers un élément de manière fluide
 * @param {HTMLElement} element - Élément vers lequel scroller
 * @returns {Promise<void>}
 */
async function scrollToElement(element) {
  element.scrollIntoView({ behavior: 'smooth', block: 'center' });
  await sleep(TIMING.CARD_SCROLL_DELAY);
}

// ============================================================================
// MAIN FUNCTIONS
// ============================================================================

/**
 * Scanne la page pour détecter les anniversaires
 * @returns {Promise<Array>} - Liste des anniversaires détectés
 */
async function scanBirthdays() {
  log('info', 'Starting birthday scan');

  // Attendre que la page soit complètement chargée
  await sleep(TIMING.PAGE_LOAD_DELAY);

  // Scroll pour charger tous les éléments
  await scrollPage();

  const birthdays = [];
  const cards = document.querySelectorAll(SELECTORS.BIRTHDAY_CARDS);

  log('info', `Found ${cards.length} cards`);

  for (const card of cards) {
    const birthdayInfo = extractBirthdayInfo(card);

    if (birthdayInfo) {
      // Vérifier si déjà envoyé aujourd'hui
      const alreadySent = await isAlreadySentToday(birthdayInfo.name);

      birthdays.push({
        name: birthdayInfo.name,
        alreadySent
      });

      log('info', `Birthday detected: ${birthdayInfo.name}${alreadySent ? ' (already sent)' : ''}`);
    }
  }

  log('info', `Scan completed: ${birthdays.length} birthdays found`);

  return birthdays;
}

/**
 * Envoie les messages à tous les contacts
 * @returns {Promise<Object>} - Résultat avec nombre de messages envoyés et ignorés
 */
async function sendAllMessages() {
  log('info', 'Starting to send messages');

  // Attendre que la page soit chargée
  await sleep(TIMING.PAGE_LOAD_DELAY);

  // Charger les templates
  const templates = await getMessageTemplates();
  log('info', `Loaded ${templates.length} message templates`);

  if (templates.length === 0) {
    throw new Error('Aucun template de message disponible');
  }

  // Scroll pour charger tout le contenu
  await scrollPage();

  let sent = 0;
  let skipped = 0;

  const cards = document.querySelectorAll(SELECTORS.BIRTHDAY_CARDS);
  log('info', `Processing ${cards.length} cards`);

  for (let i = 0; i < cards.length; i++) {
    const card = cards[i];

    try {
      const birthdayInfo = extractBirthdayInfo(card);

      if (!birthdayInfo) {
        log('warn', `Card ${i + 1} skipped: no valid info`);
        skipped++;
        continue;
      }

      const { name, messageLink } = birthdayInfo;

      // Vérifier si déjà envoyé aujourd'hui
      if (await isAlreadySentToday(name)) {
        log('info', `Skipping ${name}: already sent today`);
        skipped++;
        continue;
      }

      const firstName = extractFirstName(name);
      const template = selectRandomTemplate(templates);
      const message = generateMessage(firstName, template);

      // Modifier l'URL pour inclure le message
      const originalHref = messageLink.getAttribute('href');
      const newHref = modifyMessageUrl(originalHref, message);

      // Scroll jusqu'à l'élément
      await scrollToElement(card);

      // Ouvrir dans un nouvel onglet
      window.open(newHref, '_blank');

      // Marquer comme envoyé
      await markAsSentToday(name);

      sent++;

      // Délai aléatoire entre chaque envoi
      const delay = randomDelay();
      log('info', `Message ${sent} prepared for ${name}. Waiting ${Math.round(delay / 1000)}s...`);

      // Notifier la popup de la progression
      notifyProgress(sent, cards.length);

      await sleep(delay);

    } catch (error) {
      log('error', `Error processing card ${i + 1}`, error);
      skipped++;
    }
  }

  log('info', `Send completed: ${sent} sent, ${skipped} skipped`);

  return { sent, skipped };
}

/**
 * Notifie la popup de la progression
 * @param {number} current - Nombre actuel
 * @param {number} total - Total
 */
function notifyProgress(current, total) {
  try {
    chrome.runtime.sendMessage({
      action: 'progress',
      current,
      total
    });
  } catch (error) {
    // Silently fail if popup is closed
    log('warn', 'Could not send progress update', error);
  }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

log('info', 'LinkedIn Birthday Bot content script loaded');
