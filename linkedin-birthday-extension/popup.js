// popup.js - Interface de l'extension

document.addEventListener('DOMContentLoaded', async () => {
  // Vérifier qu'on est sur la bonne page
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const isBirthdayPage = tab.url && tab.url.includes('linkedin.com/mynetwork/catch-up/birthday');
  
  if (!isBirthdayPage) {
    document.getElementById('notOnBirthdayPage').style.display = 'block';
    document.getElementById('mainInterface').style.display = 'none';
    
    document.getElementById('goToBirthdayPage').addEventListener('click', () => {
      chrome.tabs.update(tab.id, { url: 'https://www.linkedin.com/mynetwork/catch-up/birthday/' });
      window.close();
    });
    return;
  }

  // Charger les templates de messages
  loadMessageTemplates();
  
  // Charger les stats
  loadStats();

  // Bouton Scanner
  document.getElementById('scanButton').addEventListener('click', async () => {
    showStatus('info', '🔍 Scan en cours...');
    
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      
      const response = await chrome.tabs.sendMessage(tab.id, { 
        action: 'scanBirthdays' 
      });
      
      if (response.success) {
        displayBirthdays(response.birthdays);
        document.getElementById('birthdayCount').textContent = response.birthdays.length;
        
        if (response.birthdays.length > 0) {
          document.getElementById('sendAllButton').disabled = false;
          showStatus('success', `✅ ${response.birthdays.length} anniversaire(s) détecté(s) !`);
        } else {
          showStatus('warning', '⚠️ Aucun anniversaire trouvé aujourd\'hui.');
        }
      } else {
        showStatus('error', '❌ Erreur lors du scan : ' + response.error);
      }
    } catch (error) {
      showStatus('error', '❌ Erreur de communication : ' + error.message);
    }
  });

  // Bouton Envoyer tous
  document.getElementById('sendAllButton').addEventListener('click', async () => {
    if (!confirm('Voulez-vous vraiment envoyer les messages à tous les contacts ?')) {
      return;
    }

    const sendButton = document.getElementById('sendAllButton');
    sendButton.disabled = true;
    
    showStatus('info', '📤 Envoi des messages en cours...');
    document.getElementById('progressContainer').style.display = 'block';

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      
      const response = await chrome.tabs.sendMessage(tab.id, { 
        action: 'sendAllMessages' 
      });
      
      if (response.success) {
        document.getElementById('sentCount').textContent = response.sent;
        showStatus('success', `✅ ${response.sent} message(s) envoyé(s) !`);
        
        // Sauvegarder les stats
        saveStats(response.sent);
      } else {
        showStatus('error', '❌ Erreur : ' + response.error);
      }
    } catch (error) {
      showStatus('error', '❌ Erreur : ' + error.message);
    } finally {
      document.getElementById('progressContainer').style.display = 'none';
      sendButton.disabled = false;
    }
  });

  // Bouton Paramètres
  document.getElementById('settingsButton').addEventListener('click', () => {
    chrome.tabs.create({ url: 'settings.html' });
  });

  // Auto-scan au chargement
  setTimeout(() => {
    document.getElementById('scanButton').click();
  }, 500);
});

function showStatus(type, message) {
  const statusDiv = document.getElementById('statusMessage');
  statusDiv.className = `status ${type}`;
  
  const icons = {
    info: '📘',
    success: '✅',
    warning: '⚠️',
    error: '❌'
  };
  
  statusDiv.innerHTML = `<span class="emoji">${icons[type]}</span><div>${message}</div>`;
}

function displayBirthdays(birthdays) {
  const listDiv = document.getElementById('birthdayList');
  
  if (birthdays.length === 0) {
    listDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">Aucun anniversaire aujourd\'hui</div>';
    return;
  }

  listDiv.innerHTML = birthdays.map((birthday, index) => `
    <div class="birthday-item">
      <span style="font-weight: bold;">${index + 1}.</span>
      ${birthday.name}
    </div>
  `).join('');
}

function loadMessageTemplates() {
  chrome.storage.sync.get(['messageTemplates'], (result) => {
    const templates = result.messageTemplates || [
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
  });
}

function loadStats() {
  chrome.storage.local.get(['totalSent', 'lastSentDate'], (result) => {
    const totalSent = result.totalSent || 0;
    const lastSentDate = result.lastSentDate || 'Jamais';
    
    // Afficher les stats si nécessaire
  });
}

function saveStats(sent) {
  chrome.storage.local.get(['totalSent'], (result) => {
    const totalSent = (result.totalSent || 0) + sent;
    chrome.storage.local.set({
      totalSent: totalSent,
      lastSentDate: new Date().toISOString()
    });
  });
}
