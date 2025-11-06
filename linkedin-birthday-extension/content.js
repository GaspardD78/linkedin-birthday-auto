// content.js - Script injecté dans la page LinkedIn (Version sans modules)

// ============================================================================
// CONSTANTS (inline)
// ============================================================================

const SELECTORS = {
  BIRTHDAY_CARDS: 'div[role="listitem"]',
  NAME_SELECTORS: [
    'a[href*="/in/"] span[aria-hidden="true"]',
    'p.c2f24abb.e824998c',
    'p.c2f24abb.d4d7f11d.e824998c',
    'h2 span',
    'div[class*="entity-result__title"] span'
  ],
  MESSAGE_BUTTON_SELECTORS: [
    'a[aria-label*="Envoyer un message"]',
    'a[aria-label*="Send message"]',
    'a[href*="/messaging/compose"]',
    'button[aria-label*="message"]'
  ]
};

const TIMING = {
  PAGE_LOAD_DELAY: 2000,
  SCROLL_DELAY: 1000,
  SCROLL_ITERATIONS: 3,
  CARD_SCROLL_DELAY: 500,
  MIN_MESSAGE_DELAY: 3000,
  MAX_MESSAGE_DELAY: 6000
};

const VALIDATION = {
  MIN_NAME_LENGTH: 2,
  MAX_NAME_LENGTH: 100
};

const STORAGE_KEYS = {
  MESSAGE_TEMPLATES: 'messageTemplates',
  SENT_HISTORY: 'sentHistory'
};

const DEFAULT_TEMPLATES = [
  "Joyeux anniversaire {prenom} ! 🎉 Je te souhaite une excellente journée remplie de bonheur !",
  "Bon anniversaire {prenom} ! 🎂 Profite bien de cette journée spéciale !",
  "Happy birthday {prenom} ! 🥳 Je te souhaite le meilleur pour cette nouvelle année !",
  "Joyeux anniversaire {prenom} ! 🎈 Que cette année t'apporte de belles réussites !"
];

// ============================================================================
// UTILITY FUNCTIONS (inline)
// ============================================================================

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function randomDelay(min = TIMING.MIN_MESSAGE_DELAY, max = TIMING.MAX_MESSAGE_DELAY) {
  return min + Math.random() * (max - min);
}

function extractFirstName(fullName) {
  if (!fullName || typeof fullName !== 'string') {
    return '';
  }
  return fullName.trim().split(/\s+/)[0];
}

function isValidName(name) {
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

function generateMessage(firstName, template) {
  if (!firstName || !template) {
    return '';
  }
  return template.replace(/\{prenom\}/g, firstName);
}

function selectRandomTemplate(templates) {
  if (!templates || templates.length === 0) {
    return DEFAULT_TEMPLATES[0];
  }
  return templates[Math.floor(Math.random() * templates.length)];
}

function modifyMessageUrl(originalUrl, message) {
  if (!originalUrl || !message) {
    return originalUrl;
  }

  const encodedMessage = encodeURIComponent(message);

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
    const separator = originalUrl.includes('?') ? '&' : '?';
    return originalUrl + separator + 'body=' + encodedMessage;
  }
}

function getMessageTemplates() {
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

async function isAlreadySentToday(contactName) {
  return new Promise((resolve) => {
    chrome.storage.local.get([STORAGE_KEYS.SENT_HISTORY], (result) => {
      const history = result[STORAGE_KEYS.SENT_HISTORY] || {};
      const today = new Date().toISOString().split('T')[0];
      const todaysSent = history[today] || [];
      resolve(todaysSent.includes(contactName));
    });
  });
}

async function markAsSentToday(contactName) {
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

function log(level, message, data = null) {
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

// ============================================================================
// MESSAGE HANDLERS
// ============================================================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'scanBirthdays') {
    handleScanBirthdays(sendResponse);
    return true;
  }

  if (request.action === 'sendAllMessages') {
    handleSendAllMessages(sendResponse);
    return true;
  }
});

async function handleScanBirthdays(sendResponse) {
  try {
    const birthdays = await scanBirthdays();
    sendResponse({ success: true, birthdays });
  } catch (error) {
    log('error', 'Scan failed', error);
    sendResponse({ success: false, error: error.message });
  }
}

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

function extractNameFromCard(card) {
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

async function scrollPage() {
  log('info', 'Scrolling page to load all content');

  for (let i = 0; i < TIMING.SCROLL_ITERATIONS; i++) {
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(TIMING.SCROLL_DELAY);
  }

  window.scrollTo(0, 0);
  await sleep(TIMING.SCROLL_DELAY / 2);

  log('info', 'Page scrolling completed');
}

async function scrollToElement(element) {
  element.scrollIntoView({ behavior: 'smooth', block: 'center' });
  await sleep(TIMING.CARD_SCROLL_DELAY);
}

// ============================================================================
// MAIN FUNCTIONS
// ============================================================================

async function scanBirthdays() {
  log('info', 'Starting birthday scan');

  await sleep(TIMING.PAGE_LOAD_DELAY);
  await scrollPage();

  const birthdays = [];
  const cards = document.querySelectorAll(SELECTORS.BIRTHDAY_CARDS);

  log('info', `Found ${cards.length} cards`);

  for (const card of cards) {
    const birthdayInfo = extractBirthdayInfo(card);

    if (birthdayInfo) {
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

async function sendAllMessages() {
  log('info', 'Starting to send messages');

  await sleep(TIMING.PAGE_LOAD_DELAY);

  const templates = await getMessageTemplates();
  log('info', `Loaded ${templates.length} message templates`);

  if (templates.length === 0) {
    throw new Error('Aucun template de message disponible');
  }

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

      if (await isAlreadySentToday(name)) {
        log('info', `Skipping ${name}: already sent today`);
        skipped++;
        continue;
      }

      const firstName = extractFirstName(name);
      const template = selectRandomTemplate(templates);
      const message = generateMessage(firstName, template);

      const originalHref = messageLink.getAttribute('href');
      const newHref = modifyMessageUrl(originalHref, message);

      await scrollToElement(card);

      window.open(newHref, '_blank');

      await markAsSentToday(name);

      sent++;

      const delay = randomDelay();
      log('info', `Message ${sent} prepared for ${name}. Waiting ${Math.round(delay / 1000)}s...`);

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

function notifyProgress(current, total) {
  try {
    chrome.runtime.sendMessage({
      action: 'progress',
      current,
      total
    });
  } catch (error) {
    log('warn', 'Could not send progress update', error);
  }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

log('info', 'LinkedIn Birthday Bot content script loaded');
