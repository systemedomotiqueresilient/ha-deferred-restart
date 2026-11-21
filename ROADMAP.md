# Roadmap

## Fait
- 0.1.0 : report des redémarrages autour des déclenchements prévisibles.
- 0.2.0 : renommage, mode développement, réparations HACS, compatibilité Spook, CI.
- 0.3.0 : téléphone admin (module commun `admin_phone.py` 1.1.0), tests et couverture.

## Prochaines étapes
- Tester la 0.3.0 sur une installation réelle : préremplissage depuis Partition Map / Entity Inventory, réception sur le téléphone, vrai Spook.
- Traduire les notifications persistantes (aujourd'hui en français uniquement) comme les notifications téléphone.
- Release complète (et non plus pré-release) puis demande d'inclusion dans la liste HACS par défaut.
- Suivre les nouvelles versions du module `admin_phone.py` publiées dans `ha-sdr` (recopie à l'identique, test de SHA-256 à mettre à jour).

## Idées, non planifiées
- Intercepter `update.install` sur la mise à jour du core.
- Utiliser la condition native `homeassistant.restart_required`.
- Évaluer les conditions des automatisations pour réduire les reports inutiles.

## Écarté
- Reboot de l'hôte : bouton caché par défaut dans HA, pas de raison valable de complexifier.
