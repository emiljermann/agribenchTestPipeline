from utils import SUBJECT_MODELS
from utils import read_json_array, write_json_array
from utils import get_model_id, get_last_run_filename, log
import time
import argparse
from datetime import datetime
import os

if "GROQ_API_KEY" not in os.environ:
    raise ValueError(f'Export Groq API Key to environment\n  UNIX: echo GROQ_API_KEY="..."\n  WINDOWS:  $env:GROQ_API_KEY="..."')
from model_callers import get_subject_response

API_SLEEP = 0.5
RETRY_SLEEP = 5
MAX_RETRIES = 4

def test_subjects(timestamp : str, questions: list[dict], restart : bool = False):
    """
    Test subjects on questions
    """

    if restart :
        print("Searching for incomplete subject data...")
        for i, subject in enumerate(SUBJECT_MODELS):
            print(f"Searching past subject data for {subject}")
            last_run_filename = get_last_run_filename(get_model_id(subject))
            if not last_run_filename:
                start_subject_idx = i
                start_question_idx = 0
                subject_responses = list()
                print(f"No incomplete subject data found, starting at subject {subject}")
                break
            
            last_run_filepath = os.path.join("data", last_run_filename)
            last_run_results = read_json_array(last_run_filepath)

            if len(last_run_results) != len(questions):
                start_subject_idx = i
                start_question_idx = len(last_run_results)
                subject_responses = last_run_results

                cur_qna_id = questions[start_question_idx]["qna_id"]
                print(f"Found run {last_run_filename}, restarting at {cur_qna_id}")
                break
        else: 
            print("No incomplete data found, returning...")
            return
    else:
        start_subject_idx = 0
        start_question_idx = 0
        subject_responses = list()

    question_total = len(questions)
    for subject in SUBJECT_MODELS[start_subject_idx:]:
        print(f"Testing {subject}")
        subject_filename = f"{timestamp}_s{get_model_id(subject)}.json"
        subject_filepath = os.path.join("data", subject_filename)

        for i,question in enumerate(questions[start_question_idx:]):
            question_number = i + start_question_idx
            cur_qna_id = question["qna_id"]
            subject_response = {
                "qna_id" : cur_qna_id,
                "question" : question["question"],
                "answer" : question["answer"],
                "categories" : question["categories"]
            }
            subject_query = question["question"]
            tries = 0
            qna_id = question["qna_id"]
            print(f"    {qna_id}: {question_number + 1}/{question_total} ")
            while True:
                try:
                    subject_response["response"] = get_subject_response(subject, subject_query)
                    subject_responses.append(subject_response)
                    break
                except Exception as e:
                    log_msg = f"\nError at {timestamp} testing {subject} on {cur_qna_id}:\n {e}"
                    log(log_msg, timestamp)
                    if tries < MAX_RETRIES:
                        print(f"    Encountered error, retrying...")
                        tries += 1
                        time.sleep(RETRY_SLEEP)
                    else:
                        write_json_array(subject_filepath, subject_responses)
                        raise ValueError(f"Testing failed: max retries reached ({MAX_RETRIES})")
                    
            time.sleep(API_SLEEP)
        
        start_question_idx = 0
        write_json_array(subject_filepath, subject_responses)
        subject_responses = list()

def main():
    parser = argparse.ArgumentParser(description="Test subject models defined in utils.py")
    parser.add_argument("--restart", default=False, action = "store_true", help="Restart from previous run")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    questions_filepath = os.path.join("provided_docs", "agribench_task.json")

    questions = read_json_array(questions_filepath)
    test_subjects(timestamp, questions, args.restart)

if __name__ == "__main__":
    main()