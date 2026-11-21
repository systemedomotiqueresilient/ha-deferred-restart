# Instructions pour les agents (Deferred Restart)

Intégration Home Assistant personnalisée, domaine `deferred_restart`. Elle diffère un
`homeassistant.restart` volontaire autour des déclenchements prévisibles, puis redémarre
automatiquement. Fait partie des intégrations SDR (Système Domotique Résilient).

## Règles
- **`custom_components/deferred_restart/admin_phone.py` ne se modifie JAMAIS ici.** C'est une copie
  exacte du module de référence du dépôt privé `systemedomotiqueresilient/ha-sdr`. Pour le mettre à
  jour : recopier le fichier, mettre à jour `EXPECTED_VERSION` et `EXPECTED_SHA256` dans
  `tests/test_admin_phone_copy.py`, noter la version dans `CHANGELOG.md`.
- Ne jamais modifier le code de Sentinel ni de Spook. Lecture seule vis-à-vis des autres intégrations.
- Aucune dépendance Python dans `manifest.json` (`requirements: []`). Les outils de test vont dans
  `requirements_test.txt`.
- Ne jamais envoyer l'adresse e-mail du compte, des jetons ou des données personnelles à un service
  externe, ni les écrire dans le dépôt.
- Textes utilisateur en FR et EN : `strings.json`, `translations/en.json`, `translations/fr.json`.
- README en deux langues : `README.md` (EN) et `README.fr.md` (FR), à garder synchronisés.

## Téléphone admin (spec commune v0.2)
- Cible dans `entry.data["admin_notify_target"]` (réécrite par l'options flow via
  `async_update_entry`) ; les autres réglages dans `entry.options`.
- Cible non définie = `None`. Capteur diagnostic, unique_id `<entry_id>_admin_notify_target`.
- Envoi uniquement via `async_notify_admin` (ne lève jamais d'exception).

## Versions
Le numéro doit être identique dans `manifest.json`, `const.py` (`VERSION`), `VERSION`,
`pyproject.toml`, `README.md`, `README.fr.md` et le titre de la dernière entrée de `CHANGELOG.md`.
`tests/test_versions.py` le vérifie. Toute migration d'entrée monte `MINOR_VERSION` du config flow
et ajoute une étape dans `async_migrate_entry` (`__init__.py`).

## Vérifications avant commit
```bash
pip install -r requirements_test.txt
ruff check custom_components/ tests/
pytest --cov          # couverture minimale 50 %
```
hassfest et l'action HACS tournent dans la CI (`.github/workflows/validate.yml`).

## Coordination entre agents
Les agents des intégrations SDR se synchronisent dans le carnet Evernote dédié (notes 00, 01, 02) :
relire la spec (01) et le journal (02) avant de coder, ajouter une entrée à la fin du journal après.
Aucun secret ni donnée personnelle dans ces notes.
