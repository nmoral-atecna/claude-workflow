---
issue: <numéro>
titre: <titre de l'issue>
forge:                # github | gitlab — détectée en début d'analyse
branche_defaut:       # idem
etape: analyse        # analyse | prete | dev | test | revue | livraison | terminee
branche:              # renseignée en phase B
worktree:             # idem
base:                 # sha de départ de la branche, idem ; mis à jour à chaque rebase
agent_dev:            # identifiant de l'agent dev en cours (SendMessage) ; vidé à chaque nouvelle session
agent_dev_jalons: 0   # jalons terminés par cet agent ; agent neuf à 3
passes_ko: 0          # passes de recette consécutives sans « validé » ; arrêt à 3
revue: à faire        # à faire | re-vérification | terminée
revue_base:           # sha de HEAD avant les corrections de revue
pr:                   # numéro de PR/MR, renseigné en phase F
dernier_releve:       # date du dernier relevé CI / commentaires
ouverte_le: <AAAA-MM-JJ>
maj_le: <AAAA-MM-JJ>
---

## Objectif

<une ou deux phrases>

## Critères d'acceptation

| Critère | Énoncé vérifiable | Vérification réelle |
|---------|-------------------|---------------------|
| C1 | <critère> | <ex. `curl -X POST …/api/x` → 201 ; `bin/console app:x` → sortie ; tests seuls> |

## Exemples validés

| Exemple | Cas | Contexte et entrée | Attendu |
|---------|-----|--------------------|---------|
| C1.1 | nominal | <contexte, valeurs concrètes> | <résultat observable> |
| C1.2 | <cas limite> | <…> | <…> |

<!-- chaque exemple est couvert par au moins un test, dérivé par l'agent dev ; les choix ⚠ tranchés sont consignés dans les Décisions -->

## Hors périmètre

- <…>

## Jalons

| Jalon | Critères | Statut | Commit |
|-------|----------|--------|--------|
| J1 | C1 | à faire | |

<!-- statut : à faire | en cours | bloqué | partiel | terminé -->

## Environnement

- tests : `<commande>`
- lint : `<commande>`
- analyse statique : `<commande>`
- mutation : `<commande>` | non configuré
- démarrer : `<commande>`
- arrêter : `<commande>`
- intégration : rebase | merge   (de la branche par défaut dans la branche de l'issue)
- merge : squash | merge | rebase   (méthode de merge de la PR)
- nommage des branches : <ex. feat/<numéro>-<slug>> | issue/<numéro>-<slug> par défaut
- points d'accès : <URL, commande console, file, chemin des logs…>
- doc fonctionnelle : <chemin(s)>
- doc technique : <chemin(s), ADR>
- changelog : <chemin> | aucun

## Recette

| Passe | Verdict | Critères KO / non vérifiés | Anomalies |
|-------|---------|-----------------------------|-----------|

## Revue

| Constat | Gravité | Emplacement | Traitement | Statut |
|---------|---------|-------------|------------|--------|

<!-- gravité : bloquant | à corriger | suggestion ; traitement : jalon Jk | piste PR | issue #n | question | rejeté (raison) ; statut : ouvert | corrigé | rejeté -->

## Livraison

- PR/MR : <lien>
- CI : <dernier état>

| Check | Corrections | Relances | Dernier échec |
|-------|-------------|----------|---------------|

| Retour | Source | Traitement | Statut |
|--------|--------|------------|--------|

## Décisions

<!-- spec seulement : analyse, réponses de l'utilisateur, traitement des anomalies et des constats de revue. Les choix mineurs du dev vont dans le Journal, préfixés [dev J<k>]. -->

- <AAAA-MM-JJ> — <décision> (pourquoi)

## Questions ouvertes

- Q1 — <question>

## Journal

- <AAAA-MM-JJ HH:MM> — analyse démarrée
