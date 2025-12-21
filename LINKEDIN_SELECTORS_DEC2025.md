# Sélecteurs LinkedIn Validés (Décembre 2025)
## Page Anniversaires
URL : [https://www.linkedin.com/mynetwork/invite-connect/celebrations/birthdays/](https://www.linkedin.com/mynetwork/invite-connect/celebrations/birthdays/)
La page liste les contacts ayant anniversaire aujourd'hui ou en retard via des cartes interactives. Les sélecteurs doivent prioriser les attributs ARIA stables car LinkedIn modifie fréquemment les classes CSS.
## Structure d'une Carte Contact
```html
<div class="celebrations-entity-list-item" role="listitem">
  <img src="photo.jpg" alt="Photo de [Nom]"/>
  <div>
    <a href="/in/nom-prenom-123/" class="app-aware-link">Nom Contact</a>
    <span>🎉 Anniversaire aujourd'hui</span>
  </div>
  <button aria-label="Envoyer un message à Nom Contact">Message</button>
</div>
```
Structure typique observée dans les automatisations LinkedIn : conteneur listitem avec lien profil et bouton message ARIA-labelé.
## Sélecteurs Robustes à Utiliser
- **Liste des contacts** : `div[role="listitem"]` ou `div.celebrations-entity-list-item
- **Lien profil** : `a.app-aware-link[href*="/in/"]` (relatif à la carte)
- **Nom contact** : `span[dir="ltr"]` ou `.entity-result__title-text` dans la carte
- **Bouton Message** : `button[aria-label*="Message"], button[aria-label*="envoyer un message"]`
## Modal de Message
- **Zone de texte** : `div[role="textbox"][contenteditable="true"]` ou `.msg-form__contenteditable`
- **Bouton Send** : `button[type="submit"][data-tracking-control-name*="send"]` ou `button:has-text("Send"), button:has-text("Envoyer")`
## Détection d'Erreurs
- **Rate limit** : `text="You've reached"`, `text="slow down"`, `text="limite"`
- **Session expirée** : `url*="login"`, `div[data-test-id="login-page"]
- **Modal multiple** : `div[role="textbox"].count() > 1` → utiliser `.last`
## Notes
- Les `data-*` attributes changent souvent → NE PAS UTILISER
- Les `aria-label` et `role` sont plus stables sur LinkedIn
- Toujours vérifier `isVisible()`, `isEnabled()` avant interaction
- Ajouter `page.wait_for_selector(selector, state="visible")` avec timeout 10s
- Pour debug : `page.screenshot()` après chaque échec
