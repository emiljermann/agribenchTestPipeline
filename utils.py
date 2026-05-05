import json 
import os
import re
from datetime import datetime

#################################
##  Subject and Judge Models   ##
#################################

# RPM := Requests Per Minute
# RPD := Requests Per Day
# TPM := Tokens Per Minute
# TPD := Tokens Per Day

SUBJECT_MODELS = [          # RPM RPD   TPM TPD
    "llama-3.1-8b-instant", # 30  14.4k 6k  500k
    "qwen/qwen3-32b"        # 60  1k    6k  500k
]

JUDGE_MODELS = [          # RPM RPD  TPM TPD
    'openai/gpt-oss-20b', # 30  1k   8k  200k
    'openai/gpt-oss-120b' # 30  1k   8k  200k
]

##############################
##  Supported Groq Models   ##
##############################

SUPPORTED_MODELS = {                             # RPM RPD   TPM TPD
    "llama-3.1-8b-instant",                      # 30  14.4k 6k  500k
    "llama-3.3-70b-versatile",                   # 30  1k    12k 100k
    "meta-llama/llama-4-scout-17b-16e-instruct", # 30  1k    30k 500k
    "openai/gpt-oss-20b",                        # 30  1k    8k  200k
    "openai/gpt-oss-120b",                       # 30  1k    8k  200k
    "qwen/qwen3-32b",                            # 60  1k    6k  500k
}

SCHEMA_BEST_EFFORT_MODELS = {                   # RPM RPD   TPM TPD
    "openai/gpt-oss-20b",                       # 30  1k    8k  200k
    'openai/gpt-oss-120b',                      # 30  1k    8k  200k
    'meta-llama/llama-4-scout-17b-16e-instruct' # 30  1k    30k 500k
}

SCHEMA_STRICT_MODELS = {  # RPM RPD   TPM TPD
    'openai/gpt-oss-20b', # 30  1k    8k  200k
    'openai/gpt-oss-120b' # 30  1k    8k  200k
}

########################
##  Module Utilities  ##
########################

def generate_judge_prompt(grading_instructions: str, question : str, correct_answer: str, subject_answer : str) -> str:
    """
    Takes individual parts of judge prompt and pulls them together into a single string for judge querying
    """
    full_prompt =  "#Grading Instructions:\n"
    full_prompt += "<grading_instructions>\n"
    full_prompt += grading_instructions
    full_prompt += "\n</grading_instructions>\n"
    full_prompt += "\n#Expert Created Test Question:\n"
    full_prompt += "<expert_question>\n"
    full_prompt += question
    full_prompt += "\n</expert_question>\n"
    full_prompt += "\n#Expert Evaluated Correct Answer:\n"
    full_prompt += "<expert_correct_answer>\n"
    full_prompt += correct_answer
    full_prompt += "\n</expert_correct_answer>\n"
    full_prompt += "\n#Subject Answer:\n"
    full_prompt += "<subject_answer>\n"
    full_prompt += subject_answer
    full_prompt += "\n</subject_answer>\n"

    return full_prompt

def read_json_array(filepath: str) -> list[dict]:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json_array(filepath: str, inputs: list[dict]):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(inputs, f, indent=4)

def get_last_run_filename(subject_id : str, judge_id : str = None):
    """
    Returns most recent model run data for both Subject and Judge models
    """
    if judge_id:
        file_id = f"s{subject_id}_j{judge_id}"
    else:
        file_id = f"s{subject_id}"

    all_filenames = os.listdir("data")
    valid_filenames = list()

    for filename in all_filenames:
        if filename.endswith(f"{file_id}.json"):
            valid_filenames.append(filename)

    if not valid_filenames: return None
    valid_filenames.sort(reverse=True)
    
    return valid_filenames[0]
    
def get_model_id(model_name : str) -> str:
    """
    Strips extra characters from model name for filename formatting
    """
    return re.sub(r'[.\-/\\]', '', model_name)

def log(message, timestamp = datetime.now().strftime("%Y%m%d%H%M%S")):
    filepath = os.path.join("logs", timestamp)
    with open(filepath, "a") as f:
        f.write(message + "\n")

def read_txt(filepath):
    with open(filepath, "r") as f:
       text = f.read()
    return text


class ScoreKeeper:
    """
    Tracks scores by all judges and outputs as single grade
    """    
    def __init__(self):
        self.accuracy_sum = 0
        self.relevance_sum = 0
        self.completeness_sum = 0
        self.conciseness_sum = 0
        self.practicality_sum = 0

        self.accuracy_count = 0
        self.relevance_count = 0
        self.completeness_count = 0
        self.conciseness_count = 0
        self.practicality_count = 0

    def log(self, accuracy, relevance, completeness, conciseness, practicality):
        self.accuracy_sum += accuracy
        self.relevance_sum += relevance
        self.completeness_sum += completeness
        self.conciseness_sum += conciseness
        self.practicality_sum += practicality

        self.accuracy_count += 1
        self.relevance_count += 1
        self.completeness_count += 1
        self.conciseness_count += 1
        self.practicality_count += 1
    
    def score(self) -> dict:
        if not all([self.accuracy_count != 0,
                    self.relevance_count != 0,
                    self.completeness_count != 0,
                    self.conciseness_count != 0,
                    self.practicality_count != 0]):
            raise ValueError(f"Attempted to divide by 0 in ScoreKeeper.score()")
        
        accuracy_score = self.accuracy_sum / self.accuracy_count
        relevance_score = self.relevance_sum / self.relevance_count
        completeness_score = self.completeness_sum / self.completeness_count
        conciseness_score = self.conciseness_sum / self.conciseness_count
        practicality_score = self.practicality_sum / self.practicality_count

        return {
            "accuracy" : round(accuracy_score, 4),
            "relevance" : round(relevance_score, 4),
            "completeness" : round(completeness_score, 4),
            "conciseness" : round(conciseness_score, 4),
            "practicality" : round(practicality_score, 4)
        }