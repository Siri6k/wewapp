# WewApp : le moto-taxi à prix fixe

> Application de réservation de moto-taxis pour **Likasi** (ville pilote), puis **Lubumbashi**.
> Promesse : **le prix affiché avant la course est le prix payé après.**

**Statut : pré-MVP, en développement actif.** Le backend (comptes, profil motard) avance, l'application mobile n'est pas commencée.

---

## Pourquoi ce projet ?

À Likasi et Lubumbashi, la moto est le moyen de transport du quotidien. Mais chaque course commence par une négociation :

- le motard annonce un prix au-dessus de la normale ;
- le passager discute, parfois sans issue ;
- à l'arrivée, le prix change et le conflit éclate.

Les passagers perdent du temps et de la confiance, les motards perdent des clients. Les applications de type Bolt ou Uber ne ciblent pas ce marché et ne sont pas pensées pour les motos.

## La solution

Une application **exclusivement dédiée aux moto-taxis** :

- le passager pointe sa destination sur la carte et **voit le prix avant de commander** ;
- la demande part vers le **motard disponible le plus proche** ;
- le passager suit son motard **en direct sur la carte** ;
- à la fin de la course, le passager **note le motard** (1 à 5 étoiles) ;
- les meilleurs motards sont **mis en avant** auprès des clients.

## Modèle économique

- **Zéro commission** sur les courses : le motard garde 100 % du prix.
- **Abonnement mensuel du motard** (environ 3 à 5 USD), qui finance l'application.
- **Gratuit pendant la phase pilote**, pour convaincre les premiers motards.
- Paiement **en espèces** au lancement, Mobile Money (Orange Money, M-Pesa…) ensuite.

## Comment ça marche (le MVP)

1. Le motard se connecte et passe **En ligne** (sa position GPS est partagée tant qu'il est en ligne).
2. Le passager choisit sa destination sur la carte : le prix est calculé et **figé** (tarif de base + prix par km).
3. La demande est envoyée au motard le plus proche, qui a **60 secondes** pour accepter ; sinon elle passe au suivant.
4. Le passager suit l'arrivée du motard puis la course sur la carte.
5. Le motard déclare la course terminée ; le passager voit le récapitulatif et note le motard.
6. Les annulations après acceptation sont comptées dans le profil de chacun, pour repérer les abus.

**Hors périmètre du MVP :** paiement mobile, abonnement codé, SMS de vérification, coefficients de quartiers, tableau de bord sur mesure, vérification d'identité des motards.

## Feuille de route

| Étape | Contenu | État |
|-------|---------|------|
| 1 | Comptes, connexion JWT, profil utilisateur | Terminée |
| 2 | Profil motard, En ligne / Hors ligne, position GPS | En cours |
| 3 | Estimation du prix et création d'une course | À venir |
| 4 | Mise en relation (envoi au plus proche, acceptation, expiration) | À venir |
| 5 | Application mobile (écrans passager et motard) | À venir |
| 6 | Suivi sur la carte, fin de course, notes, annulations | À venir |

Ensuite : pilote avec de vrais motards à Likasi, grille de prix co-construite avec eux, puis Lubumbashi.

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Backend | Python, Django, Django REST Framework |
| Authentification | JWT (téléphone + mot de passe) |
| Base de données | PostgreSQL |
| Application mobile | React Native (Expo) |
| Cartes | Leaflet / OpenStreetMap |
| Temps réel | Polling simple (toutes les 5 secondes), pas de WebSockets |

## Installer le backend en local

Prérequis : Python 3.11+, Docker.

```bash
# Base de données
docker compose up -d

# Environnement Python
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt

# Base et tests
python manage.py migrate
python manage.py test

# Lancer le serveur
python manage.py createsuperuser
python manage.py runserver
```

L'administration est disponible sur `http://localhost:8000/admin/`.

### API disponible

| Méthode | Route | Rôle |
|---------|-------|------|
| POST | `api/auth/register/` | Créer un compte (passager ou motard) |
| POST | `api/auth/login/` | Se connecter, reçoit les jetons JWT |
| POST | `api/auth/refresh/` | Renouveler le jeton |
| GET | `api/auth/me/` | Profil de l'utilisateur connecté |
| GET / PATCH | `api/driver/profile/` | Profil du motard (plaque, note, courses) |
| POST | `api/driver/online/` | Passer en ligne (avec la position) |
| POST | `api/driver/offline/` | Passer hors ligne |
| POST | `api/driver/location/` | Mettre à jour la position |

## Comment participer

Le projet cherche des profils variés, pas seulement des développeurs :

- **Développeurs backend (Django)** : mise en relation, calcul de prix, tests.
- **Développeurs mobile (React Native / Expo)** : écrans passager et motard.
- **Design / UX** : interface simple, lisible en plein soleil, utilisable d'une main.
- **Terrain** : motards et passagers testeurs à Likasi et Lubumbashi, retours sur les prix et les trajets.
- **Cartographie locale** : quartiers, repères connus, trajets types pour la grille de prix.

Pour proposer votre aide :

1. Ouvrez une **issue** en décrivant ce que vous voulez apporter.
2. Pour du code, créez une branche, ajoutez des tests, puis ouvrez une **pull request**.
3. Les tests doivent rester verts (`python manage.py test`).

## Contact

Sirisk : niplandjango@gmail.com

## Licence

[À définir]
