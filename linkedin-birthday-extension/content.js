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
  
  if (request.action === 'sendAllMessages') {
    sendAllMessages().then(sent => {
      sendResponse({ success: true, sent });
    }).catch(error => {
      sendResponse({ success: false, error: error.message });
    });
    return true; // Réponse asynchrone
  }
});

// Fonction pour scanner les anniversaires
async function scanBirthdays() {
  console.log('🔍 Scan des anniversaires...');
  
  // Attendre que la page soit complètement chargée
  await sleep(2000);
  
  // Scroll pour charger tous les éléments
  await scrollPage();
  
  const birthdays = [];
  
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
              !text.includes('Célébrez') && !text.includes('anniversaire')) {
            name = text;
            break;
          }
        }
      }
      
      if (!name) continue;
      
      // Trouver le bouton de message
      const messageLink = card.querySelector('a[aria-label*="Envoyer un message"]') ||
                         card.querySelector('a[href*="/messaging/compose"]');
      
      if (!messageLink) continue;
      
      birthdays.push({
        name: name,
        messageLink: messageLink,
        card: card
      });
      
    } catch (error) {
      console.error('Erreur lors du scan d\'une carte:', error);
    }
  }
  
  console.log(`✅ ${birthdays.length} anniversaire(s) trouvé(s)`);
  
  return birthdays.map(b => ({ name: b.name }));
}

// Fonction pour envoyer tous les messages
async function sendAllMessages() {
  console.log('📤 Envoi des messages...');
  
  const birthdays = await scanBirthdays();
  
  if (birthdays.length === 0) {
    throw new Error('Aucun anniversaire à traiter');
  }
  
  // Charger les templates depuis le storage
  const templates = await getMessageTemplates();
  
  let sent = 0;
  
  // Re-scanner pour avoir les références aux éléments DOM
  const cards = document.querySelectorAll('div[role="listitem"]');
  
  for (let i = 0; i < cards.length; i++) {
    const card = cards[i];
    
    try {
      // Extraire le nom
      let name = null;
      const paragraphs = card.querySelectorAll('p');
      for (const p of paragraphs) {
        const text = p.textContent.trim();
        if (text && text.length > 2 && text.length < 100 && 
            !text.includes('Célébrez') && !text.includes('anniversaire')) {
          name = text;
          break;
        }
      }
      
      if (!name) continue;
      
      const firstName = name.split(' ')[0];
      
      // Trouver le lien de message
      const messageLink = card.querySelector('a[aria-label*="Envoyer un message"]') ||
                         card.querySelector('a[href*="/messaging/compose"]');
      
      if (!messageLink) continue;
      
      // Générer un message personnalisé
      const message = generateMessage(firstName, templates);
      
      // Modifier l'URL pour inclure notre message
      const originalHref = messageLink.getAttribute('href');
      const newHref = modifyMessageUrl(originalHref, message);
      
      // Scroll jusqu'à l'élément
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await sleep(500);
      
      // Ouvrir dans un nouvel onglet (ou même onglet)
      window.open(newHref, '_blank');
      
      // Attendre que l'utilisateur envoie le message
      // Pour une vraie automatisation, il faudrait contrôler l'onglet ouvert
      
      sent++;
      
      // Délai entre chaque envoi
      const delay = 3000 + Math.random() * 3000; // 3-6 secondes
      console.log(`Message ${sent}/${cards.length} préparé pour ${name}. Attente de ${Math.round(delay/1000)}s...`);
      await sleep(delay);
      
    } catch (error) {
      console.error('Erreur lors de l\'envoi:', error);
    }
  }
  
  console.log(`✅ ${sent} message(s) envoyé(s)`);
  
  return sent;
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

function generateMessage(firstName, templates) {
  const template = templates[Math.floor(Math.random() * templates.length)];
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
console.log('🎉 LinkedIn Birthday Bot chargé et prêt !');
