# issue-workflow

Plugin Claude Code. `/issue-workflow:issue 42` (ou simplement « commençons l'issue 42 ») prend une issue GitHub ou GitLab et la mène de l'analyse au merge :

| Étape | Qui | Quoi |
|-------|-----|------|
| A. Analyse | session pilote, avec vous | écarts et questions, critères vérifiables, exemples (les ⚠ sont les choix à valider), jalons |
| B. Environnement | session pilote | commandes du projet, worktree et Docker isolés |
| C. Développement | agent `dev` | un jalon à la fois : tests, code, garde-fous, commit |
| D. Recette | agent `test` | vérification réelle de chaque critère, sans voir le travail du dev |
| E. Revue | agent `review` | relecture du code : architecture, sécurité, périmètre, contrat des exemples |
| F. Livraison | agent `doc`, puis session pilote | doc, rebase, PR/MR, CI, retours de revue, merge sur demande |

Tout l'état d'une issue vit dans `.claude/issues/<n>/state.md` : on peut fermer la session et reprendre plus tard.

## Contenu

```
plugins/issue-workflow/
├── .claude-plugin/plugin.json
├── skills/issue/            SKILL.md, forges.md, templates/state.md
├── agents/                  dev.md, test.md, review.md, doc.md
└── hooks/                   hooks.json, garde-fous-forge.py
```

Le hook `garde-fous-forge` surveille les commandes Bash :

- push forcé seulement avec `--force-with-lease`, et seulement vers une branche `issue/…` ;
- merge sans confirmation seulement si votre dernier message le demande ; sinon, confirmation ; jamais depuis un sous-agent ni avec `--admin` ;
- suppressions côté forge refusées.

Préfixes de branches configurables : variable `GARDE_FOUS_PREFIXES` (défaut `issue/`).

## Installation

Prérequis : `git`, `python3`, et `gh` ou `glab` authentifié (`gh auth login` / `glab auth login`).

```
/plugin marketplace add nmoral/claude-workflow
/plugin install issue-workflow@nmoral-claude
```

Puis ajoutez à `~/.claude/settings.json` les permissions de `settings.exemple.json` : un plugin ne peut pas les fournir lui-même. Elles évitent une demande de validation à chaque commande courante ; adaptez la liste à votre pile.

Vérification : dans une nouvelle session, `/hooks` liste `garde-fous-forge.py` sous `UserPromptSubmit` et `PreToolUse`, et `/agents` liste `issue-workflow:dev`, `test`, `review` et `doc`.

## Pour toute une équipe

Dans le `.claude/settings.json` d'un projet, versionné :

```json
{
  "extraKnownMarketplaces": {
    "nmoral-claude": { "source": { "source": "github", "repo": "nmoral/claude-workflow" } }
  },
  "enabledPlugins": { "issue-workflow@nmoral-claude": true }
}
```

Chacun se voit proposer le plugin à l'ouverture du projet.

## Conventions par projet

Facultatif, dans le dépôt du projet :

- `CLAUDE.md` : commandes de tests, lint et environnement, convention d'intégration (`rebase` ou `merge`), méthode de merge de la PR ;
- `.claude/checklist-revue.md` : règles que l'agent `review` doit vérifier.

Sans ces fichiers, le workflow pose la question une fois et propose de l'écrire.

## Mise à jour

Le numéro de `version` de `plugins/issue-workflow/.claude-plugin/plugin.json` est augmenté à chaque publication. Côté utilisateur : `/plugin marketplace update nmoral-claude`.
