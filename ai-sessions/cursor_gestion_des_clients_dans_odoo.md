# Gestion des clients dans Odoo
_Exported on 5/12/2026 at 09:44:30 GMT from Cursor (3.3.27)_

---

**User**

Normalement pour ajouter un client je passe par le module contact dans Odoo. Mais est ce nccessaire ? Le projet sur lequel je travaille n'a mentionner que sale_management et account a installer. Donc je suppose que je n'ai pas besoin du mondule contact pour voir la liste des client sur Odoo. Quels sont les autres moyens possible pour cela ?

---

**Cursor**

Vérifiant comment le projet configure Odoo pour aligner la réponse sur votre contexte.



Voici une réponse structurée pour Odoo (votre projet parle d’**Odoo 18** avec `sale_management` et `account`).

## Est-ce que le module **Contacts** est obligatoire ?

**Pour les données : non.** Les « clients » dans Odoo sont des enregistrements **`res.partner`**, modèle fourni par le module **`base`** (toujours présent). Ce n’est pas Contacts qui « crée » le concept de client.

**Pour l’interface « Contacts » :** le module **`contacts`** ajoute surtout l’**application Contacts** (menus, vues dédiées, expérience « carnet d’adresses »). En pratique, quand vous installez **Ventes** (`sale_management`), Odoo installe souvent **`contacts` en dépendance** même si vous ne l’avez pas listé explicitement dans `ODOO_INIT_MODULES`. Donc vous pouvez très bien avoir l’app Contacts disponible sans l’avoir demandée à la main.

## Voir la liste des clients sans passer par Contacts

Avec seulement **Ventes** et **Comptabilité** (comme dans votre README), vous avez déjà d’autres chemins habituels :

1. **Ventes** — menu du type **Clients / Customers** (partenaires marqués comme clients pour les ventes), souvent sous l’app Sales.
2. **Comptabilité / Facturation** — **Clients** (partenaires avec créances / comptabilité client selon la config).
3. **Depuis une commande / devis** — le champ client sur le devis ouvre la relation vers le même `res.partner` ; selon la version et les droits, vous pouvez aussi **créer** un client depuis là.
4. **Intégration externe** — votre stack FastAPI / `odoo_service` peut créer ou lister les partenaires via l’**API** (XML-RPC / JSON-RPC), sans ouvrir l’UI Contacts.

En résumé : **vous n’êtes pas obligé d’utiliser l’app Contacts** pour gérer ou voir des clients ; **Ventes** et **Comptabilité** s’appuient sur les mêmes partenaires. Le module **contacts** reste utile pour une vue centralisée et des fonctionnalités liées aux fiches contact, mais ce n’est pas le seul moyen d’accéder à la liste des clients tant que **Ventes** et/ou **Comptabilité** sont installés (et souvent **contacts** est déjà là en dépendance de **sale**).

---

**User**

Effectivement. Le module contact sert juste a afficher explicitement ce menu dans le tabs et fonctionne quand je l'ai retirer. Donc customers est inclus dans sale_management et account a l'installation de ces modules si je comprends bien

---

**Cursor**

Oui, vous avez l’essentiel.

**Ce qui est inclus avec `sale_management` et `account`**

- **Ventes** apporte les menus et écrans liés aux clients pour la vente (souvent « Customers / Clients » dans l’app Sales) : ce sont des vues sur le même modèle **`res.partner`**, avec les filtres / champs attendus pour vendre (devis, commandes, etc.).
- **Comptabilité / Facturation** apporte les menus clients côté compta (créances, factures client, etc.), toujours sur **`res.partner`**, avec la logique comptable.

Donc oui : **les entrées de menu « clients / customers » utiles pour la vente et la compta viennent de l’installation de ces modules**, pas besoin d’ouvrir l’app **Contacts** pour ça.

**Rôle de `contacts`**

- Il ajoute surtout l’**application / onglet Contacts** et une présentation « carnet d’adresses » plus générale des partenaires.
- Les données restent **`res.partner`** (déjà dans `base`) ; Ventes et Compta **réutilisent** ces fiches.

**Petite nuance** : si par « retiré » vous voulez dire **désinstallé** le module `contacts` dans Odoo, selon la version et les dépendances, ce n’est pas toujours possible ou recommandé (d’autres modules peuvent en dépendre). Si vous voulez dire **non listé dans `ODOO_INIT_MODULES`** mais que la base a quand même `contacts` après coup, c’est souvent parce que **`sale` l’installe en dépendance** — dans ce cas le menu Contacts apparaît même sans l’avoir mis dans votre liste d’init.

En résumé : **Customers côté Sales et côté Accounting, c’est bien porté par `sale_management` / `account` ; Contacts, c’est surtout l’UI dédiée « Contacts » en plus.**

