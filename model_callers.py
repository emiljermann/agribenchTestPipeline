import os
import json
from groq import Groq

from utils import SUPPORTED_MODELS, SCHEMA_BEST_EFFORT_MODELS, SCHEMA_STRICT_MODELS

RESPONSE_TIMEOUT = 60

def get_subject_response(model : str, query : str) -> str:
    """
    Queries subject model with open ended AgriBench test question and returns its response

    Arguments:
        model (str) : Groq model string
        query (sts) : Subject question
    Outputs:
        str : subject response
    """
    if model not in SUPPORTED_MODELS:
        raise ValueError(f"Model {model} not in supported models. Choose from {SUPPORTED_MODELS}")
    
    CLIENT = Groq(
        api_key = os.environ.get("GROQ_API_KEY"),
        timeout = RESPONSE_TIMEOUT
        )
    
    completion = CLIENT.chat.completions.create(
        model = model,
        messages = [ { "role"   : "user", "content" : query } ]
    )

    result = str(completion.choices[0].message.content) # can get token counts from completion.usage.{completion_tokens, prompt_tokens, total_tokens}

    return result

def get_judge_response(model : str, query : str) -> dict:
    """
    Queries judge model with full instruction prompt and returns structured scoring response

    Arguments:
        model (str) : Groq model that accepts json_schema restricted output
        query (sts) : Full judge prompt
    Outputs:
        {
        "accuracy" : int(),
        "relevance" : int(),
        "completeness" : int(),
        "conciseness" : int(),
        "practicality" : int()
        }
    """
    if model not in SCHEMA_BEST_EFFORT_MODELS:
        raise ValueError(f"Model {model} not in supported models. Choose from {SCHEMA_BEST_EFFORT_MODELS}")
    
    CLIENT = Groq(
        api_key = os.environ.get("GROQ_API_KEY"),
        timeout = RESPONSE_TIMEOUT
    )
    strict = model in SCHEMA_STRICT_MODELS
    judge_json_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "grading_results",
                "strict": strict,
                "schema": {
                    "type": "object",
                    "properties": {
                        "accuracy" : { "type" : "integer" },
                        "relevance" : { "type" : "integer" },
                        "completeness" : { "type" : "integer" },
                        "conciseness" : { "type" : "integer" },
                        "practicality" : { "type" : "integer" }
                    },
                    "required": ["accuracy", "relevance", "completeness", "conciseness", "practicality"],
                    "additionalProperties": False
                }
            }
        }
    
    completion = CLIENT.chat.completions.create(
        model = model,
        messages = [ { "role"   : "user", "content" : query } ],
        response_format = judge_json_schema
    )

    result = json.loads(completion.choices[0].message.content or "{}")

    expected_keys = {"accuracy", "relevance", "completeness", "conciseness", "practicality"}

    # Judge returned a response
    if not result:
        raise ValueError(f"Judge returned empty response")
    
    # Judge returned all required grades
    if expected_keys - result.keys():
        raise ValueError(f"Judge is missing expected keys: {expected_keys - result.keys()}")
    
    # Judge returned all numeric grades
    for value in list(result.values()):
        try:
            int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Returned value is incorrect type: {value!r}")

    return dict({key : int(result[key]) for key in expected_keys})