import os

def read_prompt_file(filename):
    # This file is chart/prompts.py
    # Planets are in chart/prompts/planets/
    prompts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")
    path = os.path.join(prompts_dir, "planets", filename)
    with open(path, encoding='utf-8') as f:
        return f.read()

# Planet templates
PLANET_TEMPLATES = {
    "Sun": read_prompt_file("Sun v3.1.txt"),
    "Moon": read_prompt_file("Moon v3.0.txt"),
    "Mercury": read_prompt_file("Mercury v3.0.txt"),
    "Venus": read_prompt_file("Venus_v3.2.txt"),
    "Mars": read_prompt_file("Mars v3.1.txt"),
    "Jupiter": read_prompt_file("Jupiter v3.2.txt"),
    "Saturn": read_prompt_file("Saturn v3.1.txt"),
}

# Master and submission prompts
def read_main_prompt(filename):
    prompts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")
    path = os.path.join(prompts_dir, filename)
    with open(path, encoding="utf-8") as f:
        return f.read()

MASTER_CHART_PROMPT = read_main_prompt("Outer_Skies_MasterPrompt_v0_11.txt")
CHART_SUBMISSION_PROMPT = read_main_prompt("Outer_Skies_Chart_Submission_Prompt_v0.11.txt")
