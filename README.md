# Vacances Autriche 2026

Ce dépôt génère la page web à partir du planning en markdown.

## Fichiers à modifier

- planning.md : le contenu du voyage
- template.html : le squelette HTML commun de la page
- styles.css : la feuille de style

## Fichier généré

- index.html : la page web générée automatiquement

Ne pas modifier index.html à la main : il sera réécrit par le script.

## Génération locale

Pour régénérer la page, créer un commit Git et pousser sur le dépôt distant :

```bash
python3 update-site.py
```

Le message de commit par défaut est :

```text
Update site
```

Vous pouvez le personnaliser :

```bash
python3 update-site.py --message "Mise a jour du planning"
```

## Génération sans push

Si vous voulez seulement régénérer la page sans commit ni push :

```bash
python3 update-site.py --no-push
```

Le script ajoute uniquement les fichiers du site lors du commit :

- planning.md
- template.html
- styles.css
- update-site.py
- index.html

## GitHub Actions

Quand une modification est poussée sur main sur planning.md, template.html ou update-site.py, le workflow GitHub régénère aussi index.html automatiquement.