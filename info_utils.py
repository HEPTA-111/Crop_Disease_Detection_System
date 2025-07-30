import os
from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY not set in environment")

def get_disease_info(crop: str, disease: str):
    """
    Uses OpenAI to fetch:
      description, causes, prevention, treatment_options (list)
    """
    prompt = (
        f"You are an expert agronomist. For the crop '{crop}' with the disease '{disease}', "
        "provide:\n1. A brief description of the disease.\n"
        "2. Main causes.\n3. Prevention measures.\n"
        "4. A list of 3 practical treatment options, naming specific chemicals or organic treatments."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400
        )
        text = response.choices[0].message.content.strip()
    except Exception as e:
        # bubble up so we can see it in the Flask log
        raise RuntimeError(f"OpenAI API error: {e}")

    # Parse the numbered response
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    desc = causes = prevention = ""
    treatment_options = []
    for line in lines:
        if line.startswith("1"):
            desc = line.split(".", 1)[1].strip()
        elif line.startswith("2"):
            causes = line.split(".", 1)[1].strip()
        elif line.startswith("3"):
            prevention = line.split(".", 1)[1].strip()
        elif line.startswith("4"):
            opts = line.split(".", 1)[1].strip()
            treatment_options = [opt.strip(" .") for opt in opts.split(",")]
    return desc, causes, prevention, treatment_options