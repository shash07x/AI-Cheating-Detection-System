import time
from collections import defaultdict

# ----------------------------
# SESSION STATE
# ----------------------------

SESSION_SEGMENTS = defaultdict(lambda: {
    "active": False,
    "start": None,
    "last_voice": None
})

SILENCE_TIMEOUT = 2.5   # seconds


def update_answer_state(session_id, audio_energy):
    """
    Returns:
        "start" | "end" | None
    """

    now = time.time()
    state = SESSION_SEGMENTS[session_id]

    # speaking
    if audio_energy > 0.02:
        state["last_voice"] = now

        if not state["active"]:
            state["active"] = True
            state["start"] = now
            return "start"

    # silence
    else:
        if state["active"] and state["last_voice"]:
            if now - state["last_voice"] > SILENCE_TIMEOUT:
                state["active"] = False
                return "end"

    return None