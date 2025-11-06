// popup.js - Interface de l'extension (Version améliorée)

import {
  LINKEDIN_URLS,
  STORAGE_KEYS,
  STATUS_TYPES,
  TIMING
} from './constants.js';

import {
  formatNumber,
  formatDate,
  log
} from './utils.js';

// ============================================================================
// STATE
// ============================================================================

let currentBirthdays = [];
let isSending = false;

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
  try {
    await initializePopup();
  } catch (error) {
    log('error', 'Popup initialization failed', error);
    showStatus(STATUS_TYPES.ERROR, '❌ Erreur d\'initialisation');
  }
});

/**
 * Initialise la popup
 */
async function initializePopup() {
  // Vérifier qu'on est sur la bonne page
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const isBirthdayPage = tab.url && tab.url.includes(LINKEDIN_URLS.BIRTHDAY_PATTERN);

  if (!isBirthdayPage) {
    showWrongPageMessage();
    return;
  }

  // Charger les templates et stats
  await Promise.all([
    loadMessageTemplates(),
    loadStats()
  ]);

  // Configurer les event listeners
  setupEventListeners();

  // Écouter les messages de progression depuis content.js
  setupProgressListener();

  // Auto-scan au chargement (avec un délai plus long pour laisser le content script s'initialiser)
  setTimeout(() => {
    performScan();
  }, TIMING.AUTO_SCAN_DELAY + 500);
}

/**
 * Affiche le message "mauvaise page"
 */
function showWrongPageMessage() {
  document.getElementById('notOnBirthdayPage').style.display = 'block';
  document.getElementById('mainInterface').style.display = 'none';

  document.getElementById('goToBirthdayPage').addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.tabs.update(tabs[0].id, { url: LINKEDIN_URLS.BIRTHDAY_PAGE });
      window.close();
    });
  });
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

/**
 * Configure tous les event listeners
 */
function setupEventListeners() {
  // Bouton Scanner
  document.getElementById('scanButton').addEventListener('click', () => {
    performScan();
  });

  // Bouton Envoyer tous
  document.getElementById('sendAllButton').addEventListener('click', async () => {
    await handleSendAll();
  });

  // Bouton Paramètres
  document.getElementById('settingsButton').addEventListener('click', () => {
    chrome.tabs.create({ url: 'settings.html' });
  });
}

/**
 * Configure l'écoute des messages de progression
 */
function setupProgressListener() {
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'progress') {
      updateProgress(request.current, request.total);
    }
  });
}

// ============================================================================
// SCAN FUNCTIONALITY
// ============================================================================

/**
 * Envoie un message au content script avec retry
 * @param {number} tabId - ID de l'onglet
 * @param {Object} message - Message à envoyer
 * @param {number} retries - Nombre de tentatives restantes
 * @returns {Promise<Object>} - Réponse du content script
 */
async function sendMessageWithRetry(tabId, message, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await chrome.tabs.sendMessage(tabId, message);
      return response;
    } catch (error) {
      log('warn', `Message attempt ${i + 1}/${retries} failed`, error);

      // Si c'est la dernière tentative, lancer l'erreur
      if (i === retries - 1) {
        throw new Error('Le script n\'est pas chargé. Actualisez la page et réessayez.');
      }

      // Attendre un peu avant de réessayer (100ms * tentative)
      await new Promise(resolve => setTimeout(resolve, 100 * (i + 1)));
    }
  }
}

/**
 * Effectue le scan des anniversaires
 */
async function performScan() {
  const scanButton = document.getElementById('scanButton');
  scanButton.disabled = true;

  showStatus(STATUS_TYPES.INFO, '🔍 Scan en cours...');

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    const response = await sendMessageWithRetry(tab.id, {
      action: 'scanBirthdays'
    });

    if (response.success) {
      currentBirthdays = response.birthdays;
      handleScanSuccess(response.birthdays);
    } else {
      handleScanError(response.error);
    }
  } catch (error) {
    log('error', 'Scan communication failed', error);
    showStatus(STATUS_TYPES.ERROR, '❌ Erreur : ' + error.message);
  } finally {
    scanButton.disabled = false;
  }
}

/**
 * Gère le succès du scan
 * @param {Array} birthdays - Liste des anniversaires
 */
function handleScanSuccess(birthdays) {
  displayBirthdays(birthdays);
  document.getElementById('birthdayCount').textContent = formatNumber(birthdays.length);

  const notSentCount = birthdays.filter(b => !b.alreadySent).length;

  if (birthdays.length > 0) {
    document.getElementById('sendAllButton').disabled = notSentCount === 0;

    if (notSentCount === 0) {
      showStatus(STATUS_TYPES.SUCCESS, `✅ ${birthdays.length} anniversaire(s) détecté(s) - Tous déjà envoyés !`);
    } else {
      showStatus(STATUS_TYPES.SUCCESS, `✅ ${notSentCount} anniversaire(s) à traiter !`);
    }
  } else {
    showStatus(STATUS_TYPES.WARNING, '⚠️ Aucun anniversaire trouvé aujourd\'hui.');
  }
}

/**
 * Gère l'erreur du scan
 * @param {string} error - Message d'erreur
 */
function handleScanError(error) {
  showStatus(STATUS_TYPES.ERROR, '❌ Erreur lors du scan : ' + error);
  document.getElementById('birthdayCount').textContent = '-';
}

// ============================================================================
// SEND FUNCTIONALITY
// ============================================================================

/**
 * Gère l'envoi de tous les messages
 */
async function handleSendAll() {
  if (isSending) {
    return;
  }

  const notSentCount = currentBirthdays.filter(b => !b.alreadySent).length;

  if (!confirm(`Voulez-vous vraiment envoyer des messages aux ${notSentCount} contact(s) ?`)) {
    return;
  }

  isSending = true;
  const sendButton = document.getElementById('sendAllButton');
  sendButton.disabled = true;

  showStatus(STATUS_TYPES.INFO, '📤 Envoi des messages en cours...');
  showProgressBar();

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    const response = await sendMessageWithRetry(tab.id, {
      action: 'sendAllMessages'
    });

    if (response.success) {
      handleSendSuccess(response.sent, response.skipped);
    } else {
      handleSendError(response.error);
    }
  } catch (error) {
    log('error', 'Send communication failed', error);
    showStatus(STATUS_TYPES.ERROR, '❌ Erreur : ' + error.message);
  } finally {
    hideProgressBar();
    isSending = false;
    sendButton.disabled = false;
  }
}

/**
 * Gère le succès de l'envoi
 * @param {number} sent - Nombre de messages envoyés
 * @param {number} skipped - Nombre de messages ignorés
 */
function handleSendSuccess(sent, skipped) {
  document.getElementById('sentCount').textContent = formatNumber(sent);

  let message = `✅ ${sent} message(s) envoyé(s) !`;
  if (skipped > 0) {
    message += ` (${skipped} ignoré(s))`;
  }

  showStatus(STATUS_TYPES.SUCCESS, message);

  // Sauvegarder les stats
  saveStats(sent);

  // Re-scanner pour mettre à jour l'affichage
  setTimeout(() => {
    performScan();
  }, 1000);
}

/**
 * Gère l'erreur de l'envoi
 * @param {string} error - Message d'erreur
 */
function handleSendError(error) {
  showStatus(STATUS_TYPES.ERROR, '❌ Erreur : ' + error);
}

// ============================================================================
// UI UPDATES
// ============================================================================

/**
 * Affiche un message de status
 * @param {string} type - Type de status (info, success, warning, error)
 * @param {string} message - Message à afficher
 */
function showStatus(type, message) {
  const statusDiv = document.getElementById('statusMessage');
  statusDiv.className = `status ${type}`;

  const icons = {
    [STATUS_TYPES.INFO]: '📘',
    [STATUS_TYPES.SUCCESS]: '✅',
    [STATUS_TYPES.WARNING]: '⚠️',
    [STATUS_TYPES.ERROR]: '❌'
  };

  statusDiv.innerHTML = `<span class="emoji">${icons[type]}</span><div>${message}</div>`;
  statusDiv.style.display = 'flex';
}

/**
 * Affiche la liste des anniversaires
 * @param {Array} birthdays - Liste des anniversaires
 */
function displayBirthdays(birthdays) {
  const listDiv = document.getElementById('birthdayList');

  if (birthdays.length === 0) {
    listDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">Aucun anniversaire aujourd\'hui</div>';
    return;
  }

  listDiv.innerHTML = birthdays.map((birthday, index) => {
    const statusIcon = birthday.alreadySent ? '✅' : '📤';
    const statusText = birthday.alreadySent ? ' (déjà envoyé)' : '';
    const opacity = birthday.alreadySent ? 'opacity: 0.5;' : '';

    return `
      <div class="birthday-item" style="${opacity}">
        <span style="font-weight: bold;">${index + 1}.</span>
        ${statusIcon} ${birthday.name}${statusText}
      </div>
    `;
  }).join('');
}

/**
 * Affiche la barre de progression
 */
function showProgressBar() {
  const container = document.getElementById('progressContainer');
  container.style.display = 'block';
  updateProgress(0, 100); // Initialiser à 0%
}

/**
 * Cache la barre de progression
 */
function hideProgressBar() {
  const container = document.getElementById('progressContainer');
  container.style.display = 'none';
}

/**
 * Met à jour la barre de progression
 * @param {number} current - Valeur actuelle
 * @param {number} total - Valeur totale
 */
function updateProgress(current, total) {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0;

  const progressFill = document.getElementById('progressFill');
  if (progressFill) {
    progressFill.style.width = `${percentage}%`;
  }

  const progressText = document.getElementById('progressText');
  if (progressText) {
    progressText.textContent = `${current} / ${total} (${percentage}%)`;
  }
}

// ============================================================================
// TEMPLATES AND STATS
// ============================================================================

/**
 * Charge les templates de messages
 */
async function loadMessageTemplates() {
  return new Promise((resolve) => {
    chrome.storage.sync.get([STORAGE_KEYS.MESSAGE_TEMPLATES], (result) => {
      const templates = result[STORAGE_KEYS.MESSAGE_TEMPLATES] || [
        "Joyeux anniversaire {prenom} ! 🎉 Je te souhaite une excellente journée !",
        "Bon anniversaire {prenom} ! 🎂 Profite bien de cette journée spéciale !",
        "Happy birthday {prenom} ! 🥳 Que cette année t'apporte le meilleur !",
        "Joyeux anniversaire {prenom} ! 🎈 Plein de bonheur pour cette nouvelle année !"
      ];

      const templatesDiv = document.getElementById('messageTemplates');
      templatesDiv.innerHTML = templates.slice(0, 3).map((template, index) => `
        <div class="template-item">
          ${index + 1}. ${template.replace('{prenom}', '<strong>[Prénom]</strong>')}
        </div>
      `).join('');

      if (templates.length > 3) {
        templatesDiv.innerHTML += `<div class="template-item">... et ${templates.length - 3} autre(s)</div>`;
      }

      resolve();
    });
  });
}

/**
 * Charge les statistiques
 */
async function loadStats() {
  return new Promise((resolve) => {
    chrome.storage.local.get([STORAGE_KEYS.TOTAL_SENT, STORAGE_KEYS.LAST_SENT_DATE], (result) => {
      const totalSent = result[STORAGE_KEYS.TOTAL_SENT] || 0;
      const lastSentDate = result[STORAGE_KEYS.LAST_SENT_DATE] || null;

      // Les stats sont déjà affichées dans l'UI si besoin
      log('info', `Stats loaded: ${totalSent} total sent, last: ${lastSentDate}`);

      resolve();
    });
  });
}

/**
 * Sauvegarde les statistiques
 * @param {number} sent - Nombre de messages envoyés
 */
function saveStats(sent) {
  chrome.storage.local.get([STORAGE_KEYS.TOTAL_SENT], (result) => {
    const totalSent = (result[STORAGE_KEYS.TOTAL_SENT] || 0) + sent;
    chrome.storage.local.set({
      [STORAGE_KEYS.TOTAL_SENT]: totalSent,
      [STORAGE_KEYS.LAST_SENT_DATE]: new Date().toISOString()
    });

    log('info', `Stats saved: ${sent} sent, total: ${totalSent}`);
  });
}

// ============================================================================
// INITIALIZATION
// ============================================================================

log('info', 'Popup script loaded');
