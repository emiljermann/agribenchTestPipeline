from utils import SUPPORTED_MODELS, JUDGE_MODELS, SUBJECT_MODELS
from utils import read_json_array, write_json_array, read_txt
from utils import generate_judge_prompt, get_model_id, get_last_run_filename, log, ScoreKeeper

import time
import argparse
import os
import re
from collections import defaultdict
from datetime import datetime

if "GROQ_API_KEY" not in os.environ:
    raise ValueError(f'Export Groq API Key to environment\n  UNIX: echo GROQ_API_KEY="..."\n  WINDOWS:  $env:GROQ_API_KEY="..."')
from model_callers import get_judge_response

API_SLEEP = 0.5
RETRY_SLEEP = 5
MAX_RETRIES = 4

def grade_subject(timestamp : str, subject : str, responses : list[dict], restart : bool = False):
    if subject not in SUPPORTED_MODELS:
        raise ValueError(f"Subject model invalid: {subject}") # Naive sanity check
    
    grading_instructions = read_txt(os.path.join("resources", "judge_prompt.txt"))

    if restart :
        print("Searching for incomplete judge data...")
        for i,judge in enumerate(JUDGE_MODELS):
                print(f"Searching past judge data for {judge}")
                last_run_filename = get_last_run_filename(get_model_id(subject), get_model_id(judge))
                if not last_run_filename:
                    start_judge_idx = i
                    start_response_idx = 0
                    judge_responses = list()
                    print(f"No incomplete judge data found, starting at judge {judge}")
                    break
                
                last_run_results = read_json_array(last_run_filename)

                if len(last_run_results) != len(responses):
                    start_judge_idx = i
                    start_response_idx = len(last_run_results)
                    judge_responses = last_run_results

                    cur_qna_id = responses[start_response_idx]["qna_id"]
                    print(f"Found run {last_run_filename}, restarting at {cur_qna_id}")
                    break

        else: 
            print("No incomplete judge data found, returning")
            return
    else:
        start_judge_idx = 0
        start_response_idx = 0
        judge_responses = list()

    response_total = len(responses)
    for judge in JUDGE_MODELS[start_judge_idx:]:
        print(f"Starting Judge {judge}")
        judge_filename = f"{timestamp}_s{get_model_id(subject)}_j{get_model_id(judge)}.json"
        judge_filepath = os.path.join("data", judge_filename)

        for i,response in enumerate(responses[start_response_idx:]):
            response_number = i + start_response_idx
            cur_qna_id = response["qna_id"]
            judge_response = {
                "qna_id" : cur_qna_id,
                "categories" : response["categories"]
            }
            judge_query = generate_judge_prompt(grading_instructions,
                                                response["question"],
                                                response["answer"],
                                                response["response"])
            tries = 0
            print(f"    {cur_qna_id}: {response_number + 1}/{response_total} ")
            while True:
                try:
                    grades = get_judge_response(judge, judge_query)
                    judge_response["accuracy"] = grades["accuracy"]
                    judge_response["relevance"] = grades["relevance"]
                    judge_response["completeness"] = grades["completeness"]
                    judge_response["conciseness"] = grades["conciseness"]
                    judge_response["practicality"] = grades["practicality"]
                    judge_responses.append(judge_response)
                    break
                except Exception as e:
                    log_msg = f"\nError at {timestamp} grading {subject} with {judge} on {cur_qna_id}:\n {e}"
                    log(log_msg, timestamp)
                    if tries < MAX_RETRIES:
                        print(f"        Encountered error, retrying...")
                        tries += 1
                        time.sleep(RETRY_SLEEP)
                    else:
                        write_json_array(judge_filepath, judge_responses)
                        raise ValueError(f"Testing failed: max retries reached ({MAX_RETRIES})")
                    
        start_response_idx = 0
        write_json_array(judge_filepath, judge_responses)
        judge_responses = list()

def generate_reportcard(timestamp : str, subject : str):
    all_filenames = os.listdir("data")
    valid_filenames = list()

    subject_id = get_model_id(subject)

    pattern = rf"{timestamp}_s{subject_id}_j.*\.json"
    for filename in all_filenames:
        if re.fullmatch(pattern, filename):
            valid_filenames.append(filename)
    
    if len(valid_filenames) != len(JUDGE_MODELS):
        raise ValueError(f"Expected {len(JUDGE_MODELS)} judge files, got {len(valid_filenames)}:\n{valid_filenames}")
    
    grades = defaultdict(ScoreKeeper)
    
    for filename in valid_filenames:
        filepath = os.path.join("data", filename)
        judge_responses = read_json_array(filepath)
        for response in judge_responses:
            grades["total"].log(response["accuracy"], 
                                response["relevance"],
                                response["completeness"],
                                response["conciseness"],
                                response["practicality"])
            for category in response["categories"]:
                grades[category].log(response["accuracy"], 
                                    response["relevance"],
                                    response["completeness"],
                                    response["conciseness"],
                                    response["practicality"])
    reportcard = dict()
    reportcard["model"] = subject_id
    reportcard["scores"] = dict()

    for category in grades.keys():
        reportcard["scores"][category] = grades[category].score()
    
    
    reportcard_filename = f"{timestamp}_s{subject_id}_reportcard.json"
    reportcard_filepath = os.path.join("data", reportcard_filename)
    write_json_array(reportcard_filepath, reportcard)

    print(f"Report Card saved at {reportcard_filename}")

    return reportcard

def visualize_reportcard(reportcard : dict):
    model = reportcard["model"]
    print(f"Report Card for Model {model}")
    for category in reportcard["scores"].keys():
        print(category)
        for grade_type in reportcard["scores"][category].keys():
            category_grades = reportcard["scores"][category]
            print(f"    {grade_type} : {category_grades[grade_type]}")

def main():
    parser = argparse.ArgumentParser(description="Run Emil's AgriBench Interview Response Judge Module")
    parser.add_argument("--subject-timestamp", default=False, help="Timestamp for subject data. Format: YYYYMMDDhhmmss")
    parser.add_argument("--report-only", default=False, action = "store_true", help="Only report scores. This will overwrite reportcard data for the provided timestamp")
    parser.add_argument("--report-timestamp", default=None, help="Timestamp to report for if running report only. Format: YYYYMMDDhhmmss")
    parser.add_argument("--restart", default=False, action = "store_true", help="Restart from previous run")
    args = parser.parse_args()

    if args.report_only and not args.report_timestamp:
        raise ValueError('Must enter report timestamp if reporting only: --report-timestamp "YYYYMMDDhhmmss"')
    if not args.report_only and not args.subject_timestamp:
        raise ValueError('Must enter subject timestamp if judging subject: --subject-timestamp "YYYYMMDDhhmmss"')

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    for subject in SUBJECT_MODELS:
        if args.report_only: 
            subject_reportcard = generate_reportcard(args.report_timestamp, subject)
        else:
            subject_id = get_model_id(subject)
            subject_responses_filename = f"{args.subject_timestamp}_s{subject_id}.json"
            subject_responses_filepath = os.path.join("data", subject_responses_filename)
            subject_responses = read_json_array(subject_responses_filepath)
            grade_subject(timestamp, subject, subject_responses, args.restart)
            subject_reportcard = generate_reportcard(timestamp, subject)

        visualize_reportcard(subject_reportcard)

if __name__ == "__main__":
    main()