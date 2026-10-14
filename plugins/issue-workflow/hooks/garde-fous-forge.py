#!/usr/bin/env python3
"""Hook garde-fous-forge du workflow /issue — UserPromptSubmit et PreToolUse (Bash).

Politique :
  - push avec --force-with-lease (ou --force-if-includes) : autorisé, pour les rebases,
    sauf vers une branche protégée ;
  - suppression distante d'une branche : autorisée, sauf pour une branche protégée ;
  - branches protégées : la branche par défaut du dépôt (origin/HEAD), plus la liste
    GARDE_FOUS_PROTEGEES ;
  - toujours refusés : --force/-f sans bail, refspec « +… », --mirror, --prune ;
  - merge de PR/MR (gh pr merge, glab mr merge) :
      * jamais depuis un sous-agent ;
      * jamais avec --admin (contournement des protections de branche) ;
      * autorisé sans confirmation si l'utilisateur l'a demandé dans son
        **dernier message** (jeton posé par UserPromptSubmit) ;
      * sinon, confirmation demandée à l'utilisateur (« ask »), jamais silencieux ;
  - merge via l'API, suppressions côté forge : refusés ;
  - toute commande qui touche au dossier des jetons : refusée.

Configuration par variables d'environnement :
  GARDE_FOUS_PROTEGEES  branches protégées en plus de la branche par défaut, motifs séparés
                        par des virgules (défaut : main,master,develop,development,dev,
                        trunk,staging,preprod,production,prod,release/*,releases/*)
  GARDE_FOUS_ETAT       dossier des jetons (défaut : ~/.claude/state/garde-fous-forge)
  GARDE_FOUS_TTL        durée de vie d'un jeton de merge, en secondes (défaut : 7200)

Entrée illisible : la commande passe (ce hook est un garde-fou ; la vraie garantie
reste la protection de branche côté forge).
"""
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
import time

PREFIXE = "[garde-fous-forge]"

PROTEGEES_DEFAUT = "main,master,develop,development,dev,trunk,staging,preprod,production,prod,release/*,releases/*"
PROTEGEES = [p.strip() for p in os.environ.get("GARDE_FOUS_PROTEGEES", PROTEGEES_DEFAUT).split(",") if p.strip()]
DOSSIER_ETAT = os.path.expanduser(os.environ.get("GARDE_FOUS_ETAT", "~/.claude/state/garde-fous-forge"))
TTL = int(os.environ.get("GARDE_FOUS_TTL", "7200"))

# Une demande de merge dans le message de l'utilisateur : merge, merger, mergé, mergez…
DEMANDE_MERGE = re.compile(r"\bmerg(e|er|es|ez|é|ée|és|ées|ent|eons)?\b", re.IGNORECASE)

GIT_OPTS_AVEC_VALEUR = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
PUSH_OPTS_AVEC_VALEUR = {"--repo", "--receive-pack", "--exec", "-o", "--push-option", "--signed"}
SUPPRESSIONS = {
    "gh": {("repo", "delete"), ("issue", "delete"), ("release", "delete"),
           ("run", "delete"), ("label", "delete"), ("secret", "delete"),
           ("variable", "delete"), ("cache", "delete")},
    "glab": {("repo", "delete"), ("issue", "delete"), ("mr", "delete"),
             ("release", "delete"), ("label", "delete"), ("variable", "delete")},
}
OPERATEURS = {";", "&&", "||", "|", "&", "(", ")", ";;", "|&"}
PREFIXES_CMD = {"sudo", "env", "command", "exec", "time", "nohup", "xargs"}
SHELLS = {"sh", "bash", "zsh", "dash"}

REFUS, DEMANDER = "refus", "demander"


# ---------------------------------------------------------------- découpage shell

def commandes_simples(commande: str):
    """Découpe une ligne shell en commandes simples, en respectant les guillemets."""
    lexer = shlex.shlex(commande.replace("\n", " ; "), posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    try:
        tous = list(lexer)
    except ValueError:
        tous = commande.split()
    courante = []
    for jeton in tous:
        if jeton in OPERATEURS or set(jeton) <= set(";&|()"):
            if courante:
                yield courante
            courante = []
        else:
            courante.append(jeton)
    if courante:
        yield courante


def programme(mot: str) -> str:
    return mot.rsplit("/", 1)[-1]


def nettoyer(mots):
    """Ignore les affectations de variables en tête (VAR=x cmd) et les préfixes usuels."""
    mots = list(mots)
    while mots and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", mots[0]) or programme(mots[0]) in PREFIXES_CMD):
        mots.pop(0)
    return mots


# ---------------------------------------------------------------- git push

def git_lire(dossier, *args):
    try:
        r = subprocess.run(["git", "-C", dossier, *args], capture_output=True, text=True, timeout=3)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def branche_protegee(ref: str, dossier: str) -> bool:
    ref = ref.removeprefix("refs/heads/")
    defaut = git_lire(dossier, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").removeprefix("origin/")
    if defaut and ref == defaut:
        return True
    return any(fnmatch.fnmatchcase(ref, motif) for motif in PROTEGEES)


def verifier_git(mots, contexte):
    i = 1
    dossier = contexte["cwd"]
    while i < len(mots) and mots[i].startswith("-"):
        option = mots[i].split("=", 1)[0]
        if option == "-C" and i + 1 < len(mots):
            chemin = os.path.expanduser(mots[i + 1])
            dossier = chemin if os.path.isabs(chemin) else os.path.join(dossier, chemin)
        i += 2 if (option in GIT_OPTS_AVEC_VALEUR and "=" not in mots[i]) else 1
    if i >= len(mots) or mots[i] != "push":
        return None

    bail = force = suppression = False
    positionnels = []
    args = mots[i + 1:]
    k = 0
    while k < len(args):
        a = args[k]
        nom = a.split("=", 1)[0]
        if nom in ("--mirror", "--prune"):
            return (REFUS, f"push avec {nom}")
        if nom in ("--force-with-lease", "--force-if-includes"):
            bail = True
        elif nom == "--force":
            force = True
        elif nom == "--delete":
            suppression = True
        elif nom in PUSH_OPTS_AVEC_VALEUR and "=" not in a:
            k += 1
        elif a.startswith("-") and not a.startswith("--"):
            lettres = a[1:]
            if "f" in lettres:
                force = True
            if "d" in lettres:
                suppression = True
        elif not a.startswith("-"):
            positionnels.append(a)
        k += 1

    refspecs = positionnels[1:]  # le premier positionnel est le dépôt distant
    for r in refspecs:
        if r.startswith("+"):
            return (REFUS, f"push forcé par la refspec {r} : utilise --force-with-lease")
        if r.startswith(":"):
            suppression = True

    destinations = [r.lstrip(":").split(":")[-1] for r in refspecs]

    if suppression:
        if not destinations:
            return (REFUS, "suppression distante sans branche explicite")
        protegees = [d for d in destinations if branche_protegee(d, dossier)]
        if protegees:
            return (REFUS, f"suppression de la branche protégée {protegees[0]}")
        return None

    if not (bail or force):
        return None
    if force and not bail:
        return (REFUS, "push --force sans bail : utilise --force-with-lease (et --force-if-includes)")

    # Sans refspec, ou avec HEAD : la branche poussée est la branche courante.
    if not destinations or "HEAD" in destinations:
        courante = git_lire(dossier, "rev-parse", "--abbrev-ref", "HEAD")
        if not courante or courante == "HEAD":
            return (REFUS, "push forcé dont la branche cible n'a pas pu être déterminée : nomme la branche")
        destinations = [courante if d == "HEAD" else d for d in destinations] or [courante]
    protegees = [d for d in destinations if branche_protegee(d, dossier)]
    if protegees:
        return (REFUS, f"push forcé vers la branche protégée {protegees[0]}")
    return None


# ---------------------------------------------------------------- gh / glab

def verifier_forge(outil, mots, contexte):
    args = mots[1:]
    positionnels = [a for a in args if not a.startswith("-")]

    est_merge = (outil == "gh" and positionnels[:2] == ["pr", "merge"]) or \
                (outil == "glab" and positionnels[:2] == ["mr", "merge"])
    if est_merge:
        if any(a.split("=", 1)[0] == "--admin" for a in args):
            return (REFUS, "merge avec --admin, qui contourne les protections de branche")
        if contexte["sous_agent"]:
            return (REFUS, "merge depuis un sous-agent : seule la session pilote merge")
        if contexte["merge_autorise"]:
            return None
        return (DEMANDER, "merge sans demande de l'utilisateur dans son dernier message")

    if tuple(positionnels[:2]) in SUPPRESSIONS[outil]:
        return (REFUS, f"suppression côté forge ({outil} {' '.join(positionnels[:2])})")

    if positionnels[:1] == ["api"]:
        for k, a in enumerate(args):
            valeur = None
            if a in {"-X", "--method"} and k + 1 < len(args):
                valeur = args[k + 1]
            elif a.startswith("--method="):
                valeur = a.split("=", 1)[1]
            elif a.startswith("-X") and len(a) > 2:
                valeur = a[2:]
            if valeur and valeur.upper() == "DELETE":
                return (REFUS, f"appel d'API en DELETE ({outil} api)")
        joint = " ".join(args)
        if re.search(r"/merge\b", joint) and re.search(r"\b(PUT|POST)\b", joint, re.I):
            return (REFUS, f"merge via l'API ({outil} api) : utilise la clé pr.merge")
    return None


# ---------------------------------------------------------------- analyse

def analyser(commande: str, contexte, profondeur: int = 0):
    if DOSSIER_ETAT in commande or ".claude/state/garde-fous-forge" in commande:
        return (REFUS, "accès au dossier des jetons de garde-fous-forge")
    pire = None
    for mots in commandes_simples(commande):
        mots = nettoyer(mots)
        if not mots:
            continue
        prog = programme(mots[0])
        verdict = None
        if prog == "git":
            verdict = verifier_git(mots, contexte)
        elif prog in ("gh", "glab"):
            verdict = verifier_forge(prog, mots, contexte)
        elif prog in SHELLS and "-c" in mots and profondeur < 3:
            k = mots.index("-c")
            if k + 1 < len(mots):
                verdict = analyser(mots[k + 1], contexte, profondeur + 1)
        if verdict and verdict[0] == REFUS:
            return verdict
        pire = pire or verdict
    return pire


# ---------------------------------------------------------------- jetons de merge

def chemin_jeton(session_id: str) -> str:
    nom = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "inconnue")
    return os.path.join(DOSSIER_ETAT, f"{nom}.json")


def poser_ou_retirer_jeton(donnees):
    texte = donnees.get("prompt") or donnees.get("user_prompt") or ""
    chemin = chemin_jeton(donnees.get("session_id", ""))
    # Les notifications du harnais (rapports d'agents, tâches) commencent par une balise.
    demande = bool(texte) and not texte.lstrip().startswith("<") and DEMANDE_MERGE.search(texte)
    try:
        if demande:
            os.makedirs(DOSSIER_ETAT, mode=0o700, exist_ok=True)
            with open(chemin, "w", encoding="utf-8") as f:
                json.dump({"expire": time.time() + TTL}, f)
        elif os.path.exists(chemin):
            os.remove(chemin)
    except OSError:
        pass


def merge_autorise(session_id: str) -> bool:
    try:
        with open(chemin_jeton(session_id), encoding="utf-8") as f:
            return json.load(f).get("expire", 0) > time.time()
    except (OSError, ValueError):
        return False


# ---------------------------------------------------------------- entrée

def repondre(decision, raison):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": raison,
    }}, ensure_ascii=False))


def main():
    try:
        donnees = json.load(sys.stdin)
    except Exception:
        return 0

    if donnees.get("hook_event_name") == "UserPromptSubmit":
        poser_ou_retirer_jeton(donnees)
        return 0

    if donnees.get("tool_name") != "Bash":
        return 0
    commande = (donnees.get("tool_input") or {}).get("command") or ""
    contexte = {
        "cwd": donnees.get("cwd") or os.getcwd(),
        "sous_agent": bool(donnees.get("agent_id")),
        "merge_autorise": merge_autorise(donnees.get("session_id", "")),
    }
    verdict = analyser(commande, contexte)
    if not verdict:
        return 0

    nature, motif = verdict
    if nature == DEMANDER:
        repondre("ask", f"{PREFIXE} Confirmation requise : {motif}.")
        return 0

    print(
        f"{PREFIXE} Commande refusée : {motif}. C'est un point d'arrêt du workflow "
        "/issue : ne cherche pas d'autre moyen d'obtenir le même effet (autre syntaxe, "
        "script, appel d'API). Session d'issue : pose la question au format imposé. "
        "Sous-agent : arrête-toi et rends un rapport « bloqué » avec cette cause.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
