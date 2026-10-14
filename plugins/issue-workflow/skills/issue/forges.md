# Opérations de forge — GitHub (`gh`) et GitLab (`glab`)

Le skill désigne chaque opération par une clé (`issue.view`, `pr.create`…). Ce fichier donne la commande à utiliser selon la `forge` du frontmatter de `state.md`. Le vocabulaire « PR » désigne aussi une MR GitLab.

Exécute toujours les commandes **depuis le dossier du dépôt ou du worktree** : `gh` et `glab` y déduisent le projet distant, y compris pour une instance GitLab auto-hébergée. Pour les corps de texte longs, écris d'abord un fichier temporaire dans le scratchpad.

Si une commande est refusée par la version installée (option inconnue), consulte `<outil> <commande> --help` et adapte-la. N'abandonne pas l'opération pour autant, et ne la reporte pas sur l'utilisateur.

## Détection (début de la phase A, une fois par issue)

1. `git remote get-url origin`
   - hôte `github.com`, ou une instance GitHub Enterprise connue de `gh auth status` → `github` ;
   - hôte contenant `gitlab`, ou une instance connue de `glab auth status` → `gitlab` ;
   - sinon : demande (on est en analyse, la question y est permise).
2. Vérifie l'authentification : `gh auth status`, ou `glab auth status --hostname <hôte>`. Si elle manque, c'est la **seule** action que l'humain doit faire lui-même (`gh auth login`, ou `glab auth login --hostname <hôte>`) : dis-le et arrête-toi.
3. Renseigne `forge` et `branche_defaut` dans le frontmatter. La branche par défaut s'obtient avec `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`, ou `glab repo view -F json` (champ `default_branch`).

## Table

| Clé | GitHub | GitLab |
|-----|--------|--------|
| `issue.view` | `gh issue view <n> --comments` | `glab issue view <n> --comments` |
| `issue.edit` | `gh issue edit <n> --body-file <f>` | `glab issue update <n> --description "$(cat <f>)"` |
| `issue.create` | `gh issue create --title "<t>" --body-file <f>` | `glab issue create --title "<t>" --description "$(cat <f>)" --yes` |
| `issue.close` | `gh issue close <n> --comment "<texte>"` | `glab issue note <n> -m "<texte>"` puis `glab issue close <n>` |
| `issue.state` | `gh issue view <n> --json state -q .state` | `glab issue view <n> -F json` (champ `state`) |
| `pr.create` | `gh pr create --base <défaut> --head <branche> --title "<t>" --body-file <f>` (`--draft`) | `glab mr create --source-branch <branche> --target-branch <défaut> --title "<t>" --description "$(cat <f>)" --yes` (`--draft`) |
| `pr.state` | `gh pr view <pr> --json state -q .state` → `MERGED` / `CLOSED` / `OPEN` | `glab mr view <pr> -F json` (champ `state`) → `merged` / `closed` / `opened` |
| `ci.watch` | `gh pr checks <pr> --watch` | `glab ci status --branch <branche> --live` |
| `ci.failed` | `gh run view <run-id> --log-failed` (id via `gh pr checks <pr>`) | jobs en échec : `glab ci get --branch <branche>`, puis `glab ci trace <job-id>` |
| `ci.retry` | `gh run rerun <run-id> --failed` | `glab ci retry <job-id>` |
| `review.comments` | `gh pr view <pr> --comments` | `glab mr view <pr> --comments` |
| `review.inline` | `gh api repos/{owner}/{repo}/pulls/<pr>/comments` | `glab api projects/:id/merge_requests/<pr>/discussions` |
| `review.state` | `gh pr view <pr> --json reviewDecision,reviews` | `glab api projects/:id/merge_requests/<pr>/approvals` |
| `review.reply` (général) | `gh pr comment <pr> --body "<texte>"` | `glab mr note <pr> -m "<texte>"` |
| `review.reply` (fil) | `gh api repos/{owner}/{repo}/pulls/<pr>/comments/<id>/replies -f body="<texte>"` | `glab api --method POST projects/:id/merge_requests/<pr>/discussions/<discussion-id>/notes -f body="<texte>"` |
| `pr.checks_ok` | `gh pr checks <pr>` (code de sortie 0 si tout est vert) | `glab ci status --branch <branche>` (statut `success`) |
| `pr.mergeable` | `gh pr view <pr> --json mergeable,mergeStateStatus,reviewDecision` | `glab mr view <pr> -F json` (champs `detailed_merge_status`, `has_conflicts`) |
| `repo.merge_methods` | `gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed` | `glab api projects/:id` (champs `merge_method`, `squash_option`) |
| `pr.merge` | `gh pr merge <pr> --<squash\|merge\|rebase> --delete-branch` | `glab mr merge <pr> [--squash \| --rebase] --remove-source-branch --yes` |
| `pr.merge_auto` | `gh pr merge <pr> --auto --<squash\|merge\|rebase> --delete-branch` | `glab mr merge <pr> --auto-merge [--squash \| --rebase] --remove-source-branch --yes` (anciennes versions : `--when-pipeline-succeeds`) |

Mot-clé de fermeture dans le corps de la PR : `Closes #<n>`, valable sur les deux forges.

`pr.merge` et `pr.merge_auto` ne s'emploient **jamais** avec `--admin` ni aucune option qui contourne les protections de branche : le hook `garde-fous-forge` les refuse.
