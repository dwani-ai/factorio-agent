"""
Defines the agents for the first part of the lab (parent-subagent example).

This module contains the initial definitions for:
- 'attractions_planner': A sub-agent to list attractions for a country.
- 'travel_brainstormer': A sub-agent to help a user decide on a country.
- 'root_agent' ('steering'): The parent agent that directs the conversation
                            to the correct sub-agent.
"""
import os
import sys
import logging

sys.path.append("..")
from dotenv import load_dotenv

from google.adk import Agent
from google.genai import types
from typing import Optional, List, Dict

from google.adk.tools.tool_context import ToolContext

load_dotenv()


# Tools (add the tool here when instructed)


# Agents

attractions_planner = Agent(
    name="attractions_planner",
    model=os.getenv("MODEL"),
    description="Build a list of attractions to visit in a country.",
    instruction="""
        - Provide the user options for attractions to visit within their selected country.
        """,

    )

travel_brainstormer = Agent(
    name="travel_brainstormer",
    model=os.getenv("MODEL"),
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
    model=os.getenv("MODEL"),
    description="Start a user on a travel adventure.",
    instruction="""
        Ask the user if they know where they'd like to travel
        or if they need some help deciding.
        """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0,
    ),
    # Add the sub_agents parameter when instructed below this line

)