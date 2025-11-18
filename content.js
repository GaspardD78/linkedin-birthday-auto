// content.js - Script injecté dans la page LinkedIn

// Écouter les messages de la popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'scanBirthdays') {
    scanBirthdays().then(birthdays => {
      sendResponse({ success: true, birthdays });
    }).catch(error => {
      sendResponse({ success: false, error: error.message });
    });
    return true; // Réponse asynchrone
  }
  
  if (request.action === 'sendMessages') {
    sendMessages(request.birthdayType, request.batchSize).then(result => {
      sendResponse({ success: true, ...result });
    }).catch(error => {
      sendResponse({ success: false, error: error.message });
    });
    return true; // Réponse asynchrone
  }
});

/**
 * Standardizes a first name by:
 * - Removing emojis and special characters (except accents and hyphens)
 * - Capitalizing the first letter of each part in compound names (e.g., Marie-Claude, Jean Marie)
 * - Converting the rest to lowercase
 * - Returning empty string if the name is just an initial (e.g., "C" or "C.")
 *
 * @param {string} name - The first name to standardize
 * @returns {string} The standardized first name, or empty string if invalid
 *
 * @example
 * standardizeFirstName("jean") // "Jean"
 * standardizeFirstName("MARIE") // "Marie"
 * standardizeFirstName("marie-claude") // "Marie-Claude"
 * standardizeFirstName("jean marie") // "Jean Marie"
 * standardizeFirstName("Jean🎉") // "Jean"
 * standardizeFirstName("françois") // "François"
 * standardizeFirstName("C") // ""
 * standardizeFirstName("C.") // ""
 */
function standardizeFirstName(name) {
  if (!name) {
    return "";
  }

  // Remove emojis and special characters (including periods)
  // Keep only: letters (including accented), hyphens, and spaces
  const cleanedChars = [];
  for (const char of name) {
    // Keep alphabetic characters, hyphens, and spaces
    // Use a regex test for alphabetic (including accented characters)
    if (/[a-zA-ZÀ-ÿ]/.test(char) || char === '-' || char === ' ') {
      cleanedChars.push(char);
    }
  }

  let cleanedName = cleanedChars.join('');

  // Normalize spaces: replace multiple spaces with single space
  while (cleanedName.includes('  ')) {
    cleanedName = cleanedName.replace('  ', ' ');
  }

  // Normalize spaces around hyphens: "marie - claude" -> "marie-claude"
  cleanedName = cleanedName.replace(/ - /g, '-');
  cleanedName = cleanedName.replace(/- /g, '-');
  cleanedName = cleanedName.replace(/ -/g, '-');

  cleanedName = cleanedName.trim();

  if (!cleanedName) {
    return "";  // Return empty if nothing left after cleaning
  }

  // Check if it's just an initial (single letter)
  if (cleanedName.length === 1) {
    return "";  // Ignore single letter initials
  }

  // Handle names with multiple parts (spaces or hyphens)
  // Split by spaces first to handle "Jean Marie" type names
  const spaceParts = cleanedName.split(' ');

  // Process each space-separated part
  const processedParts = [];
  for (const spacePart of spaceParts) {
    if (!spacePart) {
      continue;
    }

    // Check if this part has hyphens (e.g., "Marie-Claude")
    if (spacePart.includes('-')) {
      const hyphenParts = spacePart.split('-');
      const capitalizedHyphenParts = hyphenParts
        .filter(part => part.length > 0)
        .map(part => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase());
      processedParts.push(capitalizedHyphenParts.join('-'));
    } else {
      // Simple part, just capitalize
      processedParts.push(spacePart.charAt(0).toUpperCase() + spacePart.slice(1).toLowerCase());
    }
  }

  return processedParts.join(' ');
}

// Fonction pour scanner les anniversaires
async function scanBirthdays() {
  console.log('🔍 Scan des anniversaires...');
  
  // Attendre que la page soit complètement chargée
  await sleep(2000);
  
  // Scroll pour charger tous les éléments
  await scrollPage();
  
  const birthdaysToday = [];
  const birthdaysLate = [];
  
  // Sélecteurs identifiés depuis le HTML
  const cards = document.querySelectorAll('div[role="listitem"]');
  
  console.log(`Trouvé ${cards.length} cartes`);
  
  for (const card of cards) {
    try {
      // Extraire le nom
      let name = null;
      
      // Essayer plusieurs sélecteurs
      const nameSelectors = [
        'p.c2f24abb.e824998c',
        'p.c2f24abb.d4d7f11d.e824998c',
      ];
      
      for (const selector of nameSelectors) {
        const nameEl = card.querySelector(selector);
        if (nameEl && nameEl.textContent.trim()) {
          name = nameEl.textContent.trim();
          break;
        }
      }
      
      // Fallback: chercher tous les paragraphes
      if (!name) {
        const paragraphs = card.querySelectorAll('p');
        for (const p of paragraphs) {
          const text = p.textContent.trim();
          if (text && text.length > 2 && text.length < 100 && 
              !text.includes('Célébrez') && !text.includes('anniversaire') &&
              !text.includes('Aujourd\'hui') && !text.includes('Il y a') &&
              !text.includes('avec un peu de retard') && !text.includes('avec du retard')) {
            name = text;
            break;
          }
        }
      }
      
      if (!name) continue;
      
      // Détecter si c'est aujourd'hui ou en retard
      const cardText = card.textContent.toLowerCase();
      let isToday = false;
      let daysLate = 0;
      
      console.log(`📅 Analyse de la carte pour ${name}:`, cardText.substring(0, 200));
      
      // Patterns pour détecter la date (plus robustes)
      // Aujourd'hui
      if (cardText.includes('aujourd\'hui') || 
          cardText.includes('today') ||
          cardText.includes('est aujourd\'hui')) {
        isToday = true;
        console.log(`✅ ${name} - Anniversaire AUJOURD'HUI`);
      } 
      // Hier
      else if (cardText.includes('hier') || 
               cardText.includes('yesterday') ||
               cardText.includes('était hier')) {
        daysLate = 1;
        console.log(`⏰ ${name} - Anniversaire HIER (1 jour)`);
      } 
      // "avec un peu de retard" - pattern spécifique LinkedIn
      else if (cardText.includes('avec un peu de retard') || 
               cardText.includes('avec du retard') ||
               cardText.includes('en retard')) {
        daysLate = 1; // On considère comme en retard (date exacte non affichée par LinkedIn)
        console.log(`⏰ ${name} - En retard (pattern "avec du retard")`);
      }
      // Il y a X jours
      else if (cardText.includes('il y a') || cardText.includes('days ago')) {
        // Chercher "Il y a X jours" ou "X days ago"
        const daysFrMatch = cardText.match(/il y a\s+(\d+)\s+jours?/i);
        const daysEnMatch = cardText.match(/(\d+)\s+days? ago/i);
        
        if (daysFrMatch) {
          daysLate = parseInt(daysFrMatch[1]);
          console.log(`⏰ ${name} - En retard de ${daysLate} jours (FR)`);
        } else if (daysEnMatch) {
          daysLate = parseInt(daysEnMatch[1]);
          console.log(`⏰ ${name} - En retard de ${daysLate} jours (EN)`);
        }
      }
      // Patterns alternatifs
      else if (cardText.includes('was') && cardText.includes('day')) {
        // Cas "was X days ago"
        const match = cardText.match(/was\s+(\d+)\s+days? ago/i);
        if (match) {
          daysLate = parseInt(match[1]);
          console.log(`⏰ ${name} - En retard de ${daysLate} jours (WAS)`);
        }
      }
      
      // Si aucun pattern trouvé, chercher dans les éléments time ou span
      if (!isToday && daysLate === 0) {
        const timeElements = card.querySelectorAll('time, span.t-12, span.t-black--light');
        for (const el of timeElements) {
          const timeText = el.textContent.toLowerCase();
          if (timeText.includes('aujourd\'hui') || timeText.includes('today')) {
            isToday = true;
            console.log(`✅ ${name} - AUJOURD'HUI (trouvé dans time/span)`);
            break;
          } else if (timeText.includes('hier') || timeText.includes('yesterday')) {
            daysLate = 1;
            console.log(`⏰ ${name} - HIER (trouvé dans time/span)`);
            break;
          } else if (timeText.match(/\d+\s+(jour|day)/i)) {
            const match = timeText.match(/(\d+)\s+(jour|day)/i);
            if (match) {
              daysLate = parseInt(match[1]);
              console.log(`⏰ ${name} - ${daysLate} jours (trouvé dans time/span)`);
              break;
            }
          }
        }
      }
      
      // Par défaut, considérer comme aujourd'hui si toujours pas trouvé
      if (!isToday && daysLate === 0) {
        isToday = true;
        console.log(`⚠️ ${name} - Pas de date détectée, considéré comme AUJOURD'HUI par défaut`);
      }
      
      // Trouver le bouton de message
      const messageLink = card.querySelector('a[aria-label*="Envoyer un message"]') ||
                         card.querySelector('a[href*="/messaging/compose"]');
      
      if (!messageLink) continue;
      
      const birthdayData = {
        name: name,
        messageLink: messageLink.getAttribute('href'),
        card: card,
        daysLate: daysLate
      };
      
      if (isToday) {
        birthdaysToday.push(birthdayData);
      } else {
        birthdaysLate.push(birthdayData);
      }
      
    } catch (error) {
      console.error('Erreur lors du scan d\'une carte:', error);
    }
  }
  
  console.log(`✅ ${birthdaysToday.length} anniversaire(s) aujourd'hui`);
  console.log(`⏰ ${birthdaysLate.length} anniversaire(s) en retard`);
  
  return {
    today: birthdaysToday.map(b => ({ name: b.name })),
    late: birthdaysLate.map(b => ({ name: b.name, daysLate: b.daysLate }))
  };
}

// Fonction pour envoyer les messages (par lots)
async function sendMessages(birthdayType = 'today', batchSize = 10) {
  console.log(`📤 Envoi des messages (${birthdayType})...`);
  
  // Charger les templates depuis le storage
  const templates = await getMessageTemplates();
  const settings = await getSettings();
  
  let sent = 0;
  let processed = 0;
  
  // Re-scanner pour avoir les données actualisées
  const cards = document.querySelectorAll('div[role="listitem"]');
  const cardsToProcess = [];
  
  // Filtrer les cartes selon le type demandé
  for (const card of cards) {
    try {
      const cardText = card.textContent.toLowerCase();
      
      // Log pour debug
      const nameEl = card.querySelector('p');
      const debugName = nameEl ? nameEl.textContent.substring(0, 30) : 'inconnu';
      
      let isToday = false;
      let isLate = false;
      
      // Détection robuste
      if (cardText.includes('aujourd\'hui') || cardText.includes('today')) {
        isToday = true;
        console.log(`✅ AUJOURD'HUI: ${debugName}`);
      } else if (cardText.includes('hier') || cardText.includes('yesterday') ||
                 cardText.includes('il y a') || cardText.includes('days ago') ||
                 cardText.includes('day ago') ||
                 cardText.includes('avec un peu de retard') ||
                 cardText.includes('avec du retard') ||
                 cardText.includes('en retard')) {
        isLate = true;
        console.log(`⏰ EN RETARD: ${debugName}`);
      }
      
      // Vérifier aussi dans les éléments time/span
      if (!isToday && !isLate) {
        const timeElements = card.querySelectorAll('time, span.t-12, span.t-black--light');
        for (const el of timeElements) {
          const timeText = el.textContent.toLowerCase();
          if (timeText.includes('aujourd\'hui') || timeText.includes('today')) {
            isToday = true;
            console.log(`✅ AUJOURD'HUI (time): ${debugName}`);
            break;
          } else if (timeText.includes('hier') || timeText.includes('yesterday') ||
                     timeText.includes('avec un peu de retard') ||
                     timeText.includes('avec du retard') ||
                     timeText.includes('en retard') ||
                     timeText.match(/\d+\s+(jour|day)/i)) {
            isLate = true;
            console.log(`⏰ EN RETARD (time): ${debugName}`);
            break;
          }
        }
      }
      
      // Si rien trouvé, considérer comme aujourd'hui par défaut
      if (!isToday && !isLate) {
        isToday = true;
        console.log(`⚠️ PAR DÉFAUT AUJOURD'HUI: ${debugName}`);
      }
      
      // Ajouter à la liste appropriée
      if (birthdayType === 'today' && isToday) {
        cardsToProcess.push(card);
      } else if (birthdayType === 'late' && isLate) {
        cardsToProcess.push(card);
      }
    } catch (error) {
      console.error('Erreur lors du filtrage:', error);
    }
  }
  
  console.log(`${cardsToProcess.length} cartes à traiter`);
  
  // Limiter au batch size
  const cardsToSend = cardsToProcess.slice(0, batchSize);
  
  for (let i = 0; i < cardsToSend.length; i++) {
    const card = cardsToSend[i];
    
    try {
      // Extraire le nom
      let name = null;
      const paragraphs = card.querySelectorAll('p');
      for (const p of paragraphs) {
        const text = p.textContent.trim();
        if (text && text.length > 2 && text.length < 100 && 
            !text.includes('Célébrez') && !text.includes('anniversaire') &&
            !text.includes('Aujourd\'hui') && !text.includes('Il y a') &&
            !text.includes('avec un peu de retard') && !text.includes('avec du retard')) {
          name = text;
          break;
        }
      }
      
      if (!name) {
        processed++;
        continue;
      }

      // Extract and standardize the first name
      const firstName = standardizeFirstName(name.split(' ')[0]);

      // Skip if the first name is just an initial (returns empty string)
      if (!firstName) {
        console.log(`⚠️ Skipping contact '${name}' because first name is just an initial.`);
        processed++;
        continue;
      }

      // Trouver le lien de message
      const messageLink = card.querySelector('a[aria-label*="Envoyer un message"]') ||
                         card.querySelector('a[href*="/messaging/compose"]');

      if (!messageLink) {
        processed++;
        continue;
      }
      
      // Générer un message personnalisé (différent pour les retards)
      let message;
      if (birthdayType === 'late') {
        message = generateLateMessage(firstName, templates);
      } else {
        message = generateMessage(firstName, templates);
      }
      
      // Modifier l'URL pour inclure notre message
      const originalHref = messageLink.getAttribute('href');
      const newHref = modifyMessageUrl(originalHref, message);
      
      // Scroll jusqu'à l'élément
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await sleep(500);
      
      // Ouvrir dans un nouvel onglet
      window.open(newHref, '_blank');
      
      sent++;
      processed++;
      
      // Délai entre chaque envoi
      const delay = (settings.delay || 5) * 1000 + Math.random() * 2000;
      console.log(`Message ${sent}/${cardsToSend.length} préparé pour ${name}. Attente de ${Math.round(delay/1000)}s...`);
      await sleep(delay);
      
    } catch (error) {
      console.error('Erreur lors de l\'envoi:', error);
      processed++;
    }
  }
  
  console.log(`✅ ${sent} message(s) envoyé(s) sur ${processed} traité(s)`);
  
  return {
    sent: sent,
    processed: processed,
    remaining: cardsToProcess.length - processed
  };
}

// Fonctions utilitaires

async function scrollPage() {
  console.log('📜 Scroll de la page...');
  for (let i = 0; i < 3; i++) {
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(1000);
  }
  window.scrollTo(0, 0);
  await sleep(500);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function getMessageTemplates() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(['messageTemplates'], (result) => {
      const templates = result.messageTemplates || [
        "Joyeux anniversaire {prenom} ! 🎉 Je te souhaite une excellente journée !",
        "Bon anniversaire {prenom} ! 🎂 Profite bien de cette journée spéciale !",
        "Happy birthday {prenom} ! 🥳 Que cette année t'apporte le meilleur !",
        "Joyeux anniversaire {prenom} ! 🎈 Plein de bonheur pour cette nouvelle année !"
      ];
      resolve(templates);
    });
  });
}

function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(['delay', 'autoSend'], (result) => {
      resolve({
        delay: result.delay || 5,
        autoSend: result.autoSend || false
      });
    });
  });
}

function generateMessage(firstName, templates) {
  const template = templates[Math.floor(Math.random() * templates.length)];
  return template.replace('{prenom}', firstName);
}

function generateLateMessage(firstName, templates) {
  // Messages spécifiques pour les anniversaires en retard
  const lateTemplates = [
    "Bon anniversaire avec un peu de retard {prenom} ! 🎉 J'espère que tu as passé une excellente journée !",
    "Joyeux anniversaire en retard {prenom} ! 🎂 Désolé du retard, je te souhaite le meilleur !",
    "Happy belated birthday {prenom} ! 🥳 Mieux vaut tard que jamais !",
    "{prenom}, je suis un peu en retard mais joyeux anniversaire ! 🎈 J'espère que tu as été gâté(e) !"
  ];
  
  const template = lateTemplates[Math.floor(Math.random() * lateTemplates.length)];
  return template.replace('{prenom}', firstName);
}

function modifyMessageUrl(originalUrl, message) {
  // Encoder le message pour l'URL
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
    return originalUrl + '&body=' + encodedMessage;
  }
}

// Notification que le content script est chargé
console.log('🎉 LinkedIn Birthday Bot v2.0 chargé et prêt !');
console.log('🔧 Mode DEBUG activé - Les logs de détection s\'afficheront dans la console');
console.log('💡 Pour analyser la structure de la page, utilisez le script DEBUG_SCRIPT.js');
