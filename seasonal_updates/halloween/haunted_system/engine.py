"""Deterministic authored Haunted story engine."""

import copy
import random

from .discoveries import RARE_DISCOVERIES
from .stories import get_story


def _find_discovery(discovery_id):
    for discoveries in RARE_DISCOVERIES.values():
        for discovery in discoveries:
            if discovery.get("discovery_id") == discovery_id:
                return discovery
    return None


def _matches_reaction(reaction, state):
    required = reaction.get("all", [])
    return all(state.get(flag) for flag in required)


def get_scene(location_id, scene_id):
    story = get_story(location_id)
    if not story:
        raise KeyError(f"Unknown Haunted location: {location_id}")
    scene = story["scenes"].get(scene_id)
    if not scene:
        raise KeyError(f"Unknown Haunted scene {scene_id!r} for {location_id!r}")
    return story, scene


def render_scene(location_id, scene_id, state, sanity, *, active_effects=None):
    story, scene = get_scene(location_id, scene_id)
    state = state or {}
    active_effects = active_effects or {}

    if scene_id == story["opening_scene"]:
        if float(sanity) <= 0:
            text = story["opening"].get("insane") or story["opening"].get("low") or story["opening"].get("normal", "")
        elif float(sanity) <= 25:
            text = story["opening"].get("low") or story["opening"].get("normal", "")
        else:
            text = story["opening"].get("normal", "")
    else:
        if float(sanity) <= 0 and scene.get("insane"):
            text = scene["insane"]
        elif float(sanity) <= 25 and scene.get("low_sanity"):
            text = scene["low_sanity"]
        else:
            text = scene["text"]

    reactions = [r for r in scene.get("reactions", []) if _matches_reaction(r, state)]
    if reactions:
        text += "\n\n" + "\n\n".join(r["text"] for r in reactions[:2])

    if active_effects.get("haunted_run_discovery_bonus") and any(
        isinstance(c, dict) and c.get("discovery_id") for c in scene.get("choices", [])
    ):
        text += "\n\n👁️ **Something catches your attention.** A detail in this place feels easier to notice than it should."

    if active_effects.get("haunted_run_force_universal") and (
        story.get("signal_scene") == scene_id
        or (not story.get("signal_scene") and scene_id == story["opening_scene"])
    ):
        text += (
            "\n\n📻 **A signal cuts through the story.** The device you prepared locks onto a transmission that does not belong here."
        )

    if active_effects.get("haunted_run_watchers_eye") and scene_id == story["opening_scene"]:
        text += "\n\n👁️ **The Watcher's Eye reacts.** You notice a detail in the location that would normally be easy to miss."

    return {
        "story": story,
        "scene": copy.deepcopy(scene),
        "text": text,
        "choices": copy.deepcopy(scene.get("choices", [])),
    }


def resolve_choice(location_id, scene_id, state, choice_index):
    story, scene = get_scene(location_id, scene_id)
    choices = scene.get("choices", [])
    if not isinstance(choice_index, int) or not 0 <= choice_index < len(choices):
        raise IndexError("Invalid Haunted story choice index.")

    choice = copy.deepcopy(choices[choice_index])
    outcomes = [o for o in choice.get("outcomes", []) if isinstance(o, dict)]
    if not outcomes:
        raise ValueError("Haunted story choice has no outcomes.")

    outcome = random.choices(
        outcomes,
        weights=[max(0.0, float(o.get("weight", 0))) for o in outcomes],
        k=1,
    )[0]
    outcome = copy.deepcopy(outcome)

    new_state = dict(state or {})
    effects = outcome.get("effects") or {}
    for key, value in effects.items():
        new_state[key] = value

    discovery_id = outcome.get("discovery_id")
    if discovery_id:
        found = list(new_state.get("discoveries_found") or [])
        if discovery_id not in found:
            found.append(discovery_id)
        new_state["discoveries_found"] = found
        discovery = _find_discovery(discovery_id)
        if discovery:
            discovery_text = (
                f"🔐 **{discovery['title']}**\n{discovery['text']}"
            )
            outcome_text = str(outcome.get("text", "") or "").strip()

            # Some authored discovery choices repeat the discovery description
            # as their outcome text. Avoid rendering that same prose twice while
            # preserving any genuinely additional outcome text.
            def _normalize_narrative(value: str) -> str:
                return " ".join(
                    value.replace("**", "")
                    .replace("*", "")
                    .replace("`", "")
                    .replace("“", '"')
                    .replace("”", '"')
                    .replace("’", "'")
                    .split()
                ).strip().lower()

            if outcome_text and _normalize_narrative(outcome_text) == _normalize_narrative(discovery["text"]):
                outcome["text"] = discovery_text
            elif outcome_text:
                outcome["text"] = f"{discovery_text}\n\n{outcome_text}"
            else:
                outcome["text"] = discovery_text

    if outcome.get("pet_discovery"):
        new_state["pet_opportunity_taken"] = True

    next_scene = outcome.get("next_scene")
    if next_scene is not None and next_scene not in story["scenes"]:
        raise KeyError(f"Haunted story points to missing scene {next_scene!r} in {location_id!r}")

    return choice, outcome, new_state, next_scene
