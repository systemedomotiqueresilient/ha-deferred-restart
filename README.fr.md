# Deferred Restart

<img src="https://raw.githubusercontent.com/systemedomotiqueresilient/ha-deferred-restart/main/custom_components/deferred_restart/brand/icon.png" alt="Deferred Restart" width="128">

[![Validate](https://github.com/systemedomotiqueresilient/ha-deferred-restart/actions/workflows/validate.yml/badge.svg)](https://github.com/systemedomotiqueresilient/ha-deferred-restart/actions/workflows/validate.yml)

🇬🇧 [English](README.md) · 🇫🇷 Français

**Version 0.3.0** · [Journal des modifications](CHANGELOG.md) · [Feuille de route](ROADMAP.md)

Intégration Home Assistant qui **diffère** un redémarrage volontaire lorsqu'il risquerait
d'empêcher un déclenchement programmé ou prévisible. Le redémarrage n'est pas refusé :
il est mis en attente et s'exécute automatiquement dès que la fenêtre se libère.

## Installation

### HACS (dépôt personnalisé)

1. HACS → menu ⋮ → **Dépôts personnalisés**
2. Ajouter `https://github.com/systemedomotiqueresilient/ha-deferred-restart`, catégorie **Intégration**
3. Installer **Deferred Restart**, puis redémarrer Home Assistant
4. **Paramètres → Appareils et services → Ajouter une intégration → Deferred Restart**

### Manuelle

Copier `custom_components/deferred_restart/` dans le dossier `config/custom_components/`,
redémarrer, puis ajouter l'intégration comme ci-dessus.

## Principe

Pour chaque déclenchement prévu à l'heure `T`, la plage `[T − 15 min, T + 5 min]` est protégée
(durées réglables). Si l'automatisation est encore en cours à `T + 5`, la protection est prolongée
jusqu'à la fin de son exécution.

Triggers pris en compte (automatisations activées uniquement) :

| Trigger | Détail |
|---|---|
| `time` | heure fixe, `input_datetime` (date/heure/les deux), `sensor` timestamp, `offset` |
| `time_pattern` | ignoré s'il se déclenche plus souvent que l'intervalle minimum (60 min par défaut) |
| `sun` | sunrise / sunset avec offset |
| `calendar` | début / fin d'événement avec offset (lecture mise en cache 5 min) |

Les triggers d'état, de mouvement, de présence, MQTT, événement, template… sont imprévisibles,
donc volontairement ignorés.

## Comportement

- `homeassistant.restart` est intercepté (UI, automatisation, script).
- Fenêtre libre : redémarrage immédiat.
- Fenêtre protégée : la demande est mise en attente et une notification persistante est créée.
  Depuis l'UI ou une réparation HACS « Redémarrage requis », un message d'erreur explique la raison.
  Depuis une automatisation ou un script, rien n'échoue (report silencieux).
- La fenêtre est réévaluée toutes les 30 s. Dès qu'elle est libre, le redémarrage s'exécute.
- Un délai maximum de report (60 min par défaut, 0 = illimité) force le redémarrage au besoin.

## Entités

- `binary_sensor.deferred_restart_safe_now` : `on` si un redémarrage maintenant ne gêne rien (attribut `reasons`)
- `binary_sensor.deferred_restart_pending` : redémarrage en attente (`pending_since`, `deadline`)
- `sensor.deferred_restart_next_scheduled_trigger` : prochain déclenchement prévu sur 24 h
- `sensor.deferred_restart_admin_phone` : téléphone admin (cible des notifications), diagnostic
- `switch.deferred_restart_protection` : coupé = protection en pause (mode développement).
  Elle se réactive automatiquement après la durée de pause (120 min par défaut, attribut `resume_at`).
  La pause survit aux redémarrages : on peut enchaîner les cycles modification → redémarrage → test
  sans la réactiver. Couper l'interrupteur libère aussi un redémarrage déjà en attente.

## Téléphone admin

Deferred Restart peut envoyer ses alertes sur le téléphone de l'administrateur : redémarrage
différé, forcé au délai maximum, ou en échec.

- **À l'installation**, le champ est prérempli si une autre intégration SDR (Sentinel Report,
  Entity Inventory, Partition Map, Package Keeper) connaît déjà le téléphone admin. Si elles ne
  sont pas d'accord, une liste de choix est proposée ; s'il n'y en a aucune, ce sont les services
  `notify.mobile_app_*` et les entités notify de l'application mobile. Laisser vide = pas d'alerte
  sur le téléphone.
- **La valeur est copiée** dans cette intégration : supprimer l'autre intégration ne change rien.
- **Pour la modifier** : Paramètres → Appareils et services → Deferred Restart → Configurer.
- **`sensor.deferred_restart_admin_phone`** (diagnostic) affiche la cible, pour que les autres
  intégrations SDR puissent la proposer à leur tour. Rien n'est jamais écrit dans une autre intégration.
- Un échec d'envoi n'empêche jamais un redémarrage.

Le code commun est dans `admin_phone.py`, copié sans modification depuis le module de
référence SDR (version 1.1.0), commun à toutes les intégrations SDR.

## Actions

- `deferred_restart.force_restart` : exécute le redémarrage en attente, ou redémarre sans contrôle
- `deferred_restart.cancel_pending` : abandonne le redémarrage différé

## Cas d'usage principal : intégrations HACS / Marketplace

Après l'installation ou la mise à jour d'une intégration, HACS propose une réparation
« Redémarrage requis » qui appelle `homeassistant.restart` : elle est interceptée comme le menu
Système → Redémarrer. HACS ne transmet pas l'utilisateur à l'origine de l'appel : Deferred Restart
reconnaît ce cas grâce à la réparation `restart_required` encore ouverte, et affiche le message.

## Compatibilité Spook

Spook remplace aussi `homeassistant.restart` pour ajouter l'option `force`. Les deux coexistent,
quel que soit l'ordre de chargement : `force: true` n'est jamais différé, et un rechargement de
Deferred Restart (changement d'options) n'écrase pas le service de Spook.

## Différence avec Restart Guard (igraph100)

[Restart Guard](https://github.com/igraph100/ha-restart-guard) **avertit** dans la boîte de dialogue
de redémarrage et demande une confirmation ; l'utilisateur décide. Deferred Restart **diffère** le
redémarrage et l'exécute automatiquement dès que la fenêtre est libre. Les domaines sont distincts.

## Limites connues

- Les redémarrages initiés par le Supervisor (`ha core restart`, mise à jour HAOS/Supervisor,
  watchdog) ne passent pas par le core : ils ne peuvent pas être bloqués.
- `update.install` sur la mise à jour du core n'est pas intercepté.
- L'intégration remplace le handler du service `homeassistant.restart`, ce qui touche à une API
  interne. Le handler d'origine (avec la vérification admin) est restauré au déchargement.
- Un script lancé par `script.turn_on` depuis une automatisation programmée n'est vu qu'avec
  l'option « bloquer pour toute automatisation/script en cours ».
- Les conditions des automatisations ne sont pas évaluées : la protection est volontairement conservatrice.

## Licence

[MIT](LICENSE)
