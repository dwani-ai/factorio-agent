import os
import sys
import logging

sys.path.append("..")
from dotenv import load_dotenv

from google.adk import Agent
from google.genai import types
from typing import Optional, List, Dict

from google.adk.tools.tool_context import ToolContext

# NEW: import the Client class (note the package root)
from google import genai

load_dotenv()

# Create a single client; it will read GOOGLE_API_KEY from env by default
# or you can pass it explicitly as: genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
client = genai.Client()

GEMINI_MODEL = "gemini-2.5-flash-lite"  # or "models/gemini-2.5-flash-lite" depending on your setup

# You generally do NOT pass the client into Agent; you pass the model name.
# The google-adk framework will use the configured SDK/client under the hood.


# Tools (add the tool here when instructed)



# Agents

attractions_planner = Agent(
    name="attractions_planner",
    model=GEMINI_MODEL,
    description="Build a list of attractions to visit in a country.",
    instruction="""
        - Provide the user options for attractions to visit within their selected country.
        """,
)

travel_brainstormer = Agent(
    name="travel_brainstormer",
    model=GEMINI_MODEL,
    description="Help a user decide what country to visit.",
    instruction="""
        Provide a few suggestions of popular countries for travelers.

        Help a user identify their primary goals of travel:
        adventure, leisure, learning, shopping, or viewing art

        Identify countries that would make great destinations
        based on their priorities.
        """,
)

root_agent = Agent(
    name="steering",
    model=GEMINI_MODEL,
    description="Start a user on a travel adventure.",
    instruction="""
        Ask the user if they know where they'd like to travel
        or if they need some help deciding.

        - If the user does NOT know where to go and wants ideas,
          delegate to the `travel_brainstormer` sub-agent.

        - If the user ALREADY has a country in mind,
          delegate to the `attractions_planner` sub-agent
          to list attractions in that country.
        """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0,
    ),
    sub_agents=[travel_brainstormer, attractions_planner],
)
