import os

PROMPT_DIR = os.path.dirname(__file__)

def read_prompt(filename):
    """Read a UTF-8 text file from the prompts folder."""
    path = os.path.join(PROMPT_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return f.read()

# === Load prompts ===
SUN_PROMPT = read_prompt('sun.txt')
MOON_PROMPT = read_prompt('moon.txt')
MERCURY_PROMPT = read_prompt('mercury.txt')
VENUS_PROMPT = read_prompt('venus.txt')
MARS_PROMPT = read_prompt('mars.txt')
JUPITER_PROMPT = read_prompt('jupiter.txt')
SATURN_PROMPT = read_prompt('saturn.txt')
# Add Uranus, Neptune, Pluto etc. if needed:
# URANUS_PROMPT = read_prompt('uranus.txt')
# NEPTUNE_PROMPT = read_prompt('neptune.txt')
# PLUTO_PROMPT = read_prompt('pluto.txt')

MASTER_CHART_PROMPT = read_prompt('master_chart_prompt.txt')
CHART_SUBMISSION_PROMPT = read_prompt('chart_submission_prompt.txt')

PLANETARY_PROMPTS = {
    "Sun": SUN_PROMPT,
    "Moon": MOON_PROMPT,
    "Mercury": MERCURY_PROMPT,
    "Venus": VENUS_PROMPT,
    "Mars": MARS_PROMPT,
    "Jupiter": JUPITER_PROMPT,
    "Saturn": SATURN_PROMPT,
    # "Uranus": URANUS_PROMPT,
    # "Neptune": NEPTUNE_PROMPT,
    # "Pluto": PLUTO_PROMPT,
}

# Optional: print loaded prompt names and lengths for debug
if __name__ == "__main__":
    print("Loaded prompts:")
    for name, text in PLANETARY_PROMPTS.items():
        print(f"{name}: {len(text)} characters")
    print(f"Master Chart Prompt: {len(MASTER_CHART_PROMPT)} chars")
    print(f"Chart Submission Prompt: {len(CHART_SUBMISSION_PROMPT)} chars")
