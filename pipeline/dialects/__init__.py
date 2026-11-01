"""dialects holds tag corrections that only fit one dialect's speech, each turned on by name with --dialect."""

from dialects import co, pr

available = {"pr": pr, "co": co}


def load(names):
    """load returns the dialect modules for names, in order, without repeats."""
    return [available[n] for n in dict.fromkeys(names)]
