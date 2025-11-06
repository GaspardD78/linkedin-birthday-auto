// constants.js - Constantes globales de l'extension

/**
 * Sélecteurs DOM pour LinkedIn
 * Ces sélecteurs sont organisés par priorité (du plus stable au plus fragile)
 */
export const SELECTORS = {
  // Sélecteurs pour les cartes d'anniversaire
  BIRTHDAY_CARDS: 'div[role="listitem"]',

  // Sélecteurs pour les noms (par ordre de préférence)
  NAME_SELECTORS: [
    'a[href*="/in/"] span[aria-hidden="true"]', // Le plus stable
    'p.c2f24abb.e824998c',
    'p.c2f24abb.d4d7f11d.e824998c',
    'h2 span',
    'div[class*="entity-result__title"] span'
  ],

  // Sélecteurs pour les boutons de message
  MESSAGE_BUTTON_SELECTORS: [
    'a[aria-label*="Envoyer un message"]',
    'a[aria-label*="Send message"]',
    'a[href*="/messaging/compose"]',
    'button[aria-label*="message"]'
  ]
};

/**
 * Messages d'erreur standardisés
 */
export const ERROR_MESSAGES = {
  NO_BIRTHDAYS: 'Aucun anniversaire à traiter',
  SCAN_FAILED: 'Erreur lors du scan des anniversaires',
  SEND_FAILED: 'Erreur lors de l\'envoi des messages',
  STORAGE_FAILED: 'Erreur d\'accès au stockage',
  COMMUNICATION_FAILED: 'Erreur de communication avec la page',
  WRONG_PAGE: 'Vous n\'êtes pas sur la page des anniversaires LinkedIn'
};

/**
 * Configuration des délais et timeouts
 */
export const TIMING = {
  PAGE_LOAD_DELAY: 2000,        // Délai d'attente du chargement de la page
  SCROLL_DELAY: 1000,            // Délai entre chaque scroll
  SCROLL_ITERATIONS: 3,          // Nombre de scrolls pour charger le contenu
  CARD_SCROLL_DELAY: 500,        // Délai après scroll vers une carte
  MIN_MESSAGE_DELAY: 3000,       // Délai minimum entre messages
  MAX_MESSAGE_DELAY: 6000,       // Délai maximum entre messages
  AUTO_SCAN_DELAY: 3000,         // Délai avant auto-scan dans popup (increased for module loading)
  SUCCESS_MESSAGE_DURATION: 3000 // Durée d'affichage du message de succès
};

/**
 * Templates de messages par défaut
 */
export const DEFAULT_TEMPLATES = [
  "Joyeux anniversaire {prenom} ! 🎉 Je te souhaite une excellente journée remplie de bonheur !",
  "Bon anniversaire {prenom} ! 🎂 Profite bien de cette journée spéciale !",
  "Happy birthday {prenom} ! 🥳 Je te souhaite le meilleur pour cette nouvelle année !",
  "Joyeux anniversaire {prenom} ! 🎈 Que cette année t'apporte de belles réussites !",
  "Joyeux anniversaire {prenom} ! 🎊 Une belle journée à toi !"
];

/**
 * Validation
 */
export const VALIDATION = {
  MIN_NAME_LENGTH: 2,
  MAX_NAME_LENGTH: 100,
  MIN_MESSAGE_LENGTH: 10,
  MAX_MESSAGE_LENGTH: 500,
  MIN_TEMPLATES: 1,
  MIN_DELAY_SECONDS: 3,
  MAX_DELAY_SECONDS: 30
};

/**
 * URLs LinkedIn
 */
export const LINKEDIN_URLS = {
  BIRTHDAY_PAGE: 'https://www.linkedin.com/mynetwork/catch-up/birthday/',
  BIRTHDAY_PATTERN: 'linkedin.com/mynetwork/catch-up/birthday'
};

/**
 * Clés de stockage
 */
export const STORAGE_KEYS = {
  MESSAGE_TEMPLATES: 'messageTemplates',
  AUTO_SEND: 'autoSend',
  DELAY: 'delay',
  TOTAL_SENT: 'totalSent',
  LAST_SENT_DATE: 'lastSentDate',
  SENT_HISTORY: 'sentHistory'
};

/**
 * Status types pour l'UI
 */
export const STATUS_TYPES = {
  INFO: 'info',
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error'
};
