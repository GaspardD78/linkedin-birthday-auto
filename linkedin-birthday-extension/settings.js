// settings.js - Gestion des paramètres (Version améliorée)

import {
  STORAGE_KEYS,
  DEFAULT_TEMPLATES,
  VALIDATION,
  TIMING
} from './constants.js';

import {
  validateTemplate,
  formatDate,
  formatNumber,
  log
} from './utils.js';

// ============================================================================
// STATE
// ============================================================================

let templates = [];

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  try {
    initializeSettings();
  } catch (error) {
    log('error', 'Settings initialization failed', error);
    showError('Erreur lors du chargement des paramètres');
  }
});

/**
 * Initialise la page des paramètres
 */
async function initializeSettings() {
  await loadSettings();
  await loadStats();
  setupEventListeners();
}

/**
 * Configure tous les event listeners
 */
function setupEventListeners() {
  document.getElementById('addTemplateBtn').addEventListener('click', addTemplate);
  document.getElementById('saveBtn').addEventListener('click', saveSettings);
  document.getElementById('backBtn').addEventListener('click', () => window.close());
  document.getElementById('resetStatsBtn').addEventListener('click', resetStats);
}

// ============================================================================
// LOAD SETTINGS
// ============================================================================

/**
 * Charge les paramètres depuis le storage
 */
async function loadSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get([
      STORAGE_KEYS.MESSAGE_TEMPLATES,
      STORAGE_KEYS.AUTO_SEND,
      STORAGE_KEYS.DELAY
    ], (result) => {
      if (chrome.runtime.lastError) {
        log('error', 'Failed to load settings', chrome.runtime.lastError);
        showError('Erreur lors du chargement des paramètres');
        return;
      }

      templates = result[STORAGE_KEYS.MESSAGE_TEMPLATES] || DEFAULT_TEMPLATES;

      document.getElementById('autoSendCheckbox').checked = result[STORAGE_KEYS.AUTO_SEND] || false;
      document.getElementById('delayInput').value = result[STORAGE_KEYS.DELAY] || 5;

      renderTemplates();
      resolve();
    });
  });
}

/**
 * Charge les statistiques
 */
async function loadStats() {
  return new Promise((resolve) => {
    chrome.storage.local.get([
      STORAGE_KEYS.TOTAL_SENT,
      STORAGE_KEYS.LAST_SENT_DATE
    ], (result) => {
      const totalSent = result[STORAGE_KEYS.TOTAL_SENT] || 0;
      const lastSentDate = result[STORAGE_KEYS.LAST_SENT_DATE] || null;

      document.getElementById('totalSent').textContent = formatNumber(totalSent);
      document.getElementById('lastSentDate').textContent = formatDate(lastSentDate);

      resolve();
    });
  });
}

// ============================================================================
// RENDER TEMPLATES
// ============================================================================

/**
 * Rend la liste des templates dans le DOM
 */
function renderTemplates() {
  const listDiv = document.getElementById('templateList');
  listDiv.innerHTML = '';

  templates.forEach((template, index) => {
    const div = document.createElement('div');
    div.className = 'template-item';

    // Créer le textarea
    const textarea = document.createElement('textarea');
    textarea.value = template;
    textarea.dataset.index = index;
    textarea.placeholder = 'Message avec {prenom}...';

    // Validation en temps réel
    textarea.addEventListener('input', (e) => {
      validateTemplateInput(e.target);
    });

    // Créer le bouton de suppression
    const deleteBtn = document.createElement('button');
    deleteBtn.textContent = '🗑️ Supprimer';
    deleteBtn.type = 'button';
    deleteBtn.addEventListener('click', () => removeTemplate(index));

    // Créer le message de validation
    const validationMsg = document.createElement('div');
    validationMsg.className = 'validation-message';
    validationMsg.style.display = 'none';

    div.appendChild(textarea);
    div.appendChild(deleteBtn);
    div.appendChild(validationMsg);

    listDiv.appendChild(div);
  });
}

/**
 * Valide un input de template en temps réel
 * @param {HTMLTextAreaElement} textarea - L'élément textarea à valider
 */
function validateTemplateInput(textarea) {
  const validation = validateTemplate(textarea.value);
  const validationMsg = textarea.parentElement.querySelector('.validation-message');

  if (!validation.isValid) {
    validationMsg.textContent = '⚠️ ' + validation.error;
    validationMsg.style.display = 'block';
    validationMsg.style.color = '#F44336';
    textarea.style.borderColor = '#F44336';
  } else {
    validationMsg.style.display = 'none';
    textarea.style.borderColor = '#4CAF50';
  }
}

// ============================================================================
// TEMPLATE MANAGEMENT
// ============================================================================

/**
 * Ajoute un nouveau template
 */
function addTemplate() {
  templates.push("Nouveau message {prenom} 🎉");
  renderTemplates();

  // Scroll vers le nouveau template
  setTimeout(() => {
    const listDiv = document.getElementById('templateList');
    listDiv.scrollTop = listDiv.scrollHeight;
  }, 100);

  log('info', 'New template added');
}

/**
 * Supprime un template
 * @param {number} index - Index du template à supprimer
 */
function removeTemplate(index) {
  if (templates.length <= VALIDATION.MIN_TEMPLATES) {
    showError('Vous devez garder au moins un message !');
    return;
  }

  if (confirm('Voulez-vous vraiment supprimer ce message ?')) {
    templates.splice(index, 1);
    renderTemplates();
    log('info', `Template ${index} removed`);
  }
}

// ============================================================================
// SAVE SETTINGS
// ============================================================================

/**
 * Sauvegarde tous les paramètres
 */
async function saveSettings() {
  try {
    // Récupérer les templates modifiés
    const textareas = document.querySelectorAll('.template-item textarea');
    const newTemplates = [];
    const errors = [];

    // Valider tous les templates
    textareas.forEach((textarea, index) => {
      const value = textarea.value.trim();

      if (value.length === 0) {
        errors.push(`Message ${index + 1} : Le message ne peut pas être vide`);
        return;
      }

      const validation = validateTemplate(value);
      if (!validation.isValid) {
        errors.push(`Message ${index + 1} : ${validation.error}`);
      } else {
        newTemplates.push(value);
      }
    });

    // Afficher les erreurs si nécessaire
    if (errors.length > 0) {
      showError('Erreurs de validation :\n' + errors.join('\n'));
      return;
    }

    if (newTemplates.length === 0) {
      showError('Vous devez avoir au moins un message valide !');
      return;
    }

    // Récupérer les autres paramètres
    const autoSend = document.getElementById('autoSendCheckbox').checked;
    let delay = parseInt(document.getElementById('delayInput').value);

    // Valider le délai
    if (isNaN(delay) || delay < VALIDATION.MIN_DELAY_SECONDS || delay > VALIDATION.MAX_DELAY_SECONDS) {
      showError(`Le délai doit être entre ${VALIDATION.MIN_DELAY_SECONDS} et ${VALIDATION.MAX_DELAY_SECONDS} secondes`);
      return;
    }

    // Sauvegarder dans le storage
    await saveToStorage(newTemplates, autoSend, delay);

    // Mise à jour locale
    templates = newTemplates;

    showSuccess();
    log('info', 'Settings saved successfully');

  } catch (error) {
    log('error', 'Failed to save settings', error);
    showError('Erreur lors de la sauvegarde : ' + error.message);
  }
}

/**
 * Sauvegarde dans le storage Chrome
 * @param {Array<string>} templates - Templates à sauvegarder
 * @param {boolean} autoSend - Option d'envoi automatique
 * @param {number} delay - Délai entre les messages
 */
function saveToStorage(templates, autoSend, delay) {
  return new Promise((resolve, reject) => {
    chrome.storage.sync.set({
      [STORAGE_KEYS.MESSAGE_TEMPLATES]: templates,
      [STORAGE_KEYS.AUTO_SEND]: autoSend,
      [STORAGE_KEYS.DELAY]: delay
    }, () => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve();
      }
    });
  });
}

// ============================================================================
// STATS MANAGEMENT
// ============================================================================

/**
 * Réinitialise les statistiques
 */
function resetStats() {
  if (!confirm('Voulez-vous vraiment réinitialiser les statistiques ?')) {
    return;
  }

  chrome.storage.local.set({
    [STORAGE_KEYS.TOTAL_SENT]: 0,
    [STORAGE_KEYS.LAST_SENT_DATE]: null,
    [STORAGE_KEYS.SENT_HISTORY]: {}
  }, () => {
    if (chrome.runtime.lastError) {
      showError('Erreur lors de la réinitialisation');
      return;
    }

    loadStats();
    showSuccess('Statistiques réinitialisées !');
    log('info', 'Stats reset');
  });
}

// ============================================================================
// UI FEEDBACK
// ============================================================================

/**
 * Affiche un message de succès
 * @param {string} message - Message à afficher (optionnel)
 */
function showSuccess(message = '✅ Paramètres sauvegardés avec succès !') {
  const successMsg = document.getElementById('successMessage');
  successMsg.textContent = message;
  successMsg.style.display = 'block';

  setTimeout(() => {
    successMsg.style.display = 'none';
  }, TIMING.SUCCESS_MESSAGE_DURATION);
}

/**
 * Affiche un message d'erreur
 * @param {string} message - Message d'erreur
 */
function showError(message) {
  alert('❌ ' + message);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

log('info', 'Settings script loaded');
