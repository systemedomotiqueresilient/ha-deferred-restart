# Changelog

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions selon [SemVer](https://semver.org/lang/fr/).

## [0.3.1] - 2026-11-21

### Modifié
- Module `admin_phone.py` passé en **MODULE_VERSION 1.2.0**, copié tel quel depuis `ha-sdr` (commit `77a8992`), SHA-256 `1d720150ff1c709547018236afcb1c555e630c504be0c34b20fe0b79ed80545b`, vérifié par un test. Seul changement : `outdoor_brief` ajouté aux intégrations sœurs, ce qui permet de proposer le téléphone admin choisi dans Outdoor Brief. Aucune fonction ni signature modifiée.

## [0.3.0] - 2026-11-21

### Ajouté
- **Téléphone admin** (convention commune SDR, spec v0.2) :
  - module `admin_phone.py` **MODULE_VERSION 1.1.0**, copié tel quel depuis `ha-sdr` (commit `dfc42ab`), SHA-256 `32b3619e975eaeb0606252b4cdca9f3d2402854193f88619cd4bde383b30e1f9`, vérifié par un test ;
  - capteur diagnostic `sensor.deferred_restart_admin_phone`, unique_id `<entry_id>_admin_notify_target`, état et attribut `notify_service` = cible ou `None` ;
  - champ « Téléphone admin » dans le config flow, prérempli via `suggest_admin_target` (une valeur chez les sœurs = préremplie, plusieurs = liste, aucune = services `notify.mobile_app_*` puis entités notify mobiles) ; saisie libre, refusée si elle n'est pas du type `notify.xxx` (`invalid_target`) ;
  - même champ dans l'options flow ; la valeur est stockée dans `entry.data["admin_notify_target"]` (réécrite par `async_update_entry`), les réglages restent dans `entry.options` ;
  - alertes envoyées au téléphone via `async_notify_admin` : redémarrage différé (une fois par report), forcé au délai maximum (envoyé avant le redémarrage), ou en échec. Un échec d'envoi n'empêche jamais un redémarrage. Messages en français si la langue du serveur est le français, en anglais sinon.
  - icônes : titres avec émoji (⏳ différé, ⚠️ forcé, 🚨 échec) sur le téléphone et dans les notifications persistantes ; pour un service `notify.mobile_app_*`, `data.notification_icon` (icône MDI, Android) et `data.tag` = `deferred_restart_pending`, pour que chaque annonce remplace la précédente sur le téléphone.
- Tests pytest (`tests/`) : 25 tests, couverture 77 %, dont aucune / une / plusieurs valeurs sœurs, plateforme non listée ignorée, suppression d'une sœur, options flow, migration, envoi, cohérence des versions.
- `pyproject.toml` (pytest, couverture, ruff alignés sur `ha-sdr`), `requirements_test.txt` (outils de test uniquement), job « Tests » dans la CI.
- `VERSION`, `ROADMAP.md`, `CLAUDE.md`.

### Modifié
- Entrée de configuration en version **1.2** : migration 1.1 → 1.2 automatique et sans perte (ajout de `admin_notify_target: None` dans `entry.data`, réglages conservés).

## [0.2.0] - 2026-11-16

### Ajouté
- Renommage en **Deferred Restart** (domaine `deferred_restart`), le nom Restart Guard étant déjà pris.
- Interrupteur `switch.deferred_restart_protection` : pause de la protection (mode développement), réactivation automatique, état conservé après redémarrage.
- Reconnaissance des réparations HACS « Redémarrage requis » comme demande humaine.
- Compatibilité avec l'option `force` de Spook, quel que soit l'ordre de chargement.
- README EN + FR, licence MIT, icône, workflows hassfest et HACS, catégorie `computers_network`.

## [0.1.0] - 2026-11-15

### Ajouté
- Première version (sous le nom Restart Guard) : report de `homeassistant.restart` autour des déclenchements `time`, `time_pattern`, `sun` et `calendar`, exécution automatique quand la fenêtre se libère, délai maximum de report.
