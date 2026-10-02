"""Small helpers used by authored Haunted story definitions."""


def _outcome(text, sanity=0, *, effects=None, next_scene=None, discovery_id=None,
             pet_discovery=False, end=False, ending_title=None):
    return {
        "weight": 100,
        "sanity": int(sanity),
        "text": text,
        "effects": dict(effects or {}),
        "next_scene": next_scene,
        "discovery_id": discovery_id,
        "pet_discovery": bool(pet_discovery),
        "end": bool(end),
        "ending_title": ending_title,
    }


def choice(label, key, risk, text, sanity=0, *, next_scene=None, effects=None,
           discovery_id=None, pet_discovery=False, end=False, ending_title=None):
    """Create a deterministic authored choice.

    The legacy Haunted system had weighted micro-outcomes. Story choices are
    intentionally deterministic so the authored narrative stays coherent while
    reward drops remain random elsewhere in the run.
    """
    risk = risk if risk in {"low", "medium", "high", "extreme"} else "medium"
    return {
        "label": label,
        "key": key,
        "risk": risk,
        "risk_label": risk.title(),
        "outcomes": [
            _outcome(
                text,
                sanity,
                effects=effects,
                next_scene=next_scene,
                discovery_id=discovery_id,
                pet_discovery=pet_discovery,
                end=end,
                ending_title=ending_title,
            )
        ],
    }


def discovery_choice(label, key, risk, discovery_id, text, sanity, next_scene, *, effects=None):
    return choice(
        label,
        key,
        risk,
        text,
        sanity,
        next_scene=next_scene,
        effects=effects,
        discovery_id=discovery_id,
    )


def pet_choice(label, key, risk, text, sanity, next_scene, *, effects=None):
    return choice(
        label,
        key,
        risk,
        text,
        sanity,
        next_scene=next_scene,
        effects=effects,
        pet_discovery=True,
    )


def scene(scene_id, text, choices, *, low_sanity=None, insane=None, reactions=None):
    return {
        "id": scene_id,
        "text": text,
        "low_sanity": low_sanity,
        "insane": insane,
        "choices": choices,
        "reactions": list(reactions or []),
    }


def story(location_id, title, opening, scenes, *, shortcut_scene=None, signal_scene=None,
          description=None):
    scene_order = list(scenes)
    return {
        "location_id": location_id,
        "title": title,
        "description": description or "",
        "opening_scene": scene_order[0],
        "scene_order": scene_order,
        "scene_count": len(scene_order),
        "opening": opening,
        "scenes": scenes,
        "shortcut_scene": shortcut_scene,
        "signal_scene": signal_scene,
    }
