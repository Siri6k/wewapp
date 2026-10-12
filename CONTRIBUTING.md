# Contribuer au projet

Merci de participer. Ces règles tiennent sur une page : elles servent à ce que chacun sache quoi faire, et à ce que le code reste fiable.

## Principes

- **Rien ne va directement sur `main`.** Tout passe par une pull request (PR).
- **Une tâche = une branche = une PR.** Petites PR, relues vite.
- **Chaque PR est relue par le fondateur** avant d'être fusionnée.
- **Les tests doivent passer.** Une PR dont les tests échouent n'est pas fusionnée.
- Chacun a le dernier mot dans son domaine (voir l'accord de collaboration). En cas de doute, on demande avant de coder.

## Démarrer

1. Suivez le [README](README.md) pour installer le projet.
2. Copiez `.env.example` vers `.env` et remplissez vos valeurs. **Ne commitez jamais `.env`.**
3. Vérifiez que `python manage.py test` passe avant de commencer.

## Travailler sur une tâche

1. Prenez une tâche dans les **Issues** GitHub (ou demandez-en une) et dites-le en commentaire pour que personne ne la fasse en double.
2. Créez une branche depuis `main` à jour :
   ```bash
   git checkout main && git pull
   git checkout -b feature/fin-de-course
   ```
   Préfixes : `feature/` (nouveauté), `fix/` (correction), `docs/` (documentation).
3. Codez par petites étapes, avec des commits clairs, à l'impératif :
   `Ajoute l'endpoint de fin de course`, `Corrige le calcul du prix minimum`.
4. Ajoutez des **tests** pour ce que vous écrivez.
5. Ouvrez la PR vers `main`.

## Ce que doit contenir une pull request

- Le lien vers l'issue (`Closes #12`).
- **Ce qui change**, en deux ou trois phrases.
- **Comment le tester** (commande ou requête à lancer).
- Les tests ajoutés.

## Définition de « terminé »

Une tâche est terminée quand :

- [ ] `python manage.py test` passe, et les nouveaux comportements sont testés ;
- [ ] `python manage.py makemigrations --check` ne signale rien (les migrations sont dans la PR) ;
- [ ] aucun secret, mot de passe ou donnée réelle d'utilisateur dans le code, les tests ou les captures ;
- [ ] pas de code mort ni de code commenté laissé derrière soi ;
- [ ] le README est mis à jour si une route ou une commande change ;
- [ ] le fondateur a relu et approuvé.

## Style de code

- Suivez le style existant : une app Django par domaine (`accounts`, `drivers`, `rides`), la logique métier hors des vues quand elle grossit (voir `rides/dispatch.py`).
- Noms de variables et de fonctions en anglais, messages affichés aux utilisateurs en français.
- Les prix et montants utilisent `Decimal`, jamais `float`.

## Sécurité

- Les mots de passe et clés ne s'échangent jamais par message ordinaire ni dans le code.
- Un problème de sécurité se signale **en privé** au fondateur, pas dans une issue publique.
- Les accès aux serveurs sont donnés au cas par cas, au minimum nécessaire.

## Communication

- Point d'équipe hebdomadaire : à definir.
- Canal d'équipe : a definir.
- Le fondateur répond aux PR sous 48 h. Si ce délai est dépassé, relancez-le dans le canal.
