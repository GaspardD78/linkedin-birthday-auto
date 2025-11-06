// settings.js

let templates = [];

document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  loadStats();

  document.getElementById('addTemplateBtn').addEventListener('click', addTemplate);
  document.getElementById('saveBtn').addEventListener('click', saveSettings);
  document.getElementById('backBtn').addEventListener('click', () => window.close());
  document.getElementById('resetStatsBtn').addEventListener('click', resetStats);
});

function loadSettings() {
  chrome.storage.sync.get(['messageTemplates', 'autoSend', 'delay'], (result) => {
    templates = result.messageTemplates || [
      "Joyeux anniversaire {prenom} ! 🎉 Je te souhaite une excellente journée remplie de bonheur !",
      "Bon anniversaire {prenom} ! 🎂 Profite bien de cette journée spéciale !",
      "Happy birthday {prenom} ! 🥳 Je te souhaite le meilleur pour cette nouvelle année !",
      "Joyeux anniversaire {prenom} ! 🎈 Que cette année t'apporte de belles réussites !"
    ];

    document.getElementById('autoSendCheckbox').checked = result.autoSend || false;
    document.getElementById('delayInput').value = result.delay || 5;

    renderTemplates();
  });
}

function renderTemplates() {
  const listDiv = document.getElementById('templateList');
  listDiv.innerHTML = '';

  templates.forEach((template, index) => {
    const div = document.createElement('div');
    div.className = 'template-item';
    div.innerHTML = `
      <textarea data-index="${index}">${template}</textarea>
      <button onclick="removeTemplate(${index})">🗑️ Supprimer</button>
    `;
    listDiv.appendChild(div);
  });
}

function addTemplate() {
  templates.push("Nouveau message {prenom} 🎉");
  renderTemplates();
}

function removeTemplate(index) {
  if (templates.length <= 1) {
    alert('Vous devez garder au moins un message !');
    return;
  }
  templates.splice(index, 1);
  renderTemplates();
}

function saveSettings() {
  // Récupérer les templates modifiés
  const textareas = document.querySelectorAll('.template-item textarea');
  templates = Array.from(textareas).map(ta => ta.value.trim()).filter(t => t.length > 0);

  if (templates.length === 0) {
    alert('Vous devez avoir au moins un message !');
    return;
  }

  const autoSend = document.getElementById('autoSendCheckbox').checked;
  const delay = parseInt(document.getElementById('delayInput').value);

  chrome.storage.sync.set({
    messageTemplates: templates,
    autoSend: autoSend,
    delay: delay
  }, () => {
    // Afficher le message de succès
    const successMsg = document.getElementById('successMessage');
    successMsg.style.display = 'block';
    
    setTimeout(() => {
      successMsg.style.display = 'none';
    }, 3000);
  });
}

function loadStats() {
  chrome.storage.local.get(['totalSent', 'lastSentDate'], (result) => {
    document.getElementById('totalSent').textContent = result.totalSent || 0;
    
    if (result.lastSentDate) {
      const date = new Date(result.lastSentDate);
      document.getElementById('lastSentDate').textContent = date.toLocaleDateString('fr-FR');
    } else {
      document.getElementById('lastSentDate').textContent = 'Jamais';
    }
  });
}

function resetStats() {
  if (confirm('Voulez-vous vraiment réinitialiser les statistiques ?')) {
    chrome.storage.local.set({
      totalSent: 0,
      lastSentDate: null
    }, () => {
      loadStats();
      alert('Statistiques réinitialisées !');
    });
  }
}
