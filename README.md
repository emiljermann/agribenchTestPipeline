
## Setup

### Build virtual environment with venv and pip
```console
    python -m venv venv              # Setup virtual env
    .\venv\Scripts\Activate.ps1      # Activate virtual env
    pip install -r requirements.txt  # Install package requirements
```

### Get free Groq API token and set environment variable
```console
    $env:GROQ_API_KEY="..."
```

### Select Subject and Judge models in utils.py

Default Selection (uses Groq rate limits):
```python
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
```

### Run Subject Module
```console
    python .\subject_test.py [--restart]
```

### Run Judge Module
```console
    # For default usage, the timestamp prefix of the subject response files must be included using the --subject-timestamp argument
    python .\judge_module.py [--subject-timestamp "YYYYMMDDhhmmss" ] [--report-only] [--report-timestamp "YYYYMMDDhhmmss"] [--restart]
```

## LLM Selection

**Model Provider: Groq** \
Subject Models: *{llama-3.1-8b-instant, qwen/qwen3-32b}* \
Judge Models: *{openai/gpt-oss-20b, openai/gpt-oss-120b}* 

Groq was used to select models due to its variety of models and high token use in its free tier. Llama-3.1-8b-Instant and Qwen3-32b were chosen because they are from different model developing companies, and have different weight sizes, so they are more likely to produce different results. Openai-GPT-oss-20b and Openai-GPT-oss-120b were chosen because they accept strict json_schema adherence through Groq. In the future, I would research other LLM providers, and switch out Openai-GPT-oss-20b with a different model that accepts json schema output. Using two similar Openai models is not ideal for getting diverse response grades, but in this case the different parameter sizes will likely lead to different biases in the model responses, hopefully leading to some nuance in the current judge output. 

## File Info

### subject_test.py
*Call to run subject tests on subjects defined in utils.SUBJECT_MODELS. Models in utils.SUBJECT_MODELS must be chosen from utils.SUPPORT_MODELS (selected models supported by Groq's API)*
```
python .\subject_test.py [--restart]
```
Global Variables:
- `API_SLEEP = 0.5` Selected to satisfy lowest subject RPM (30) defined in utils.py
- `RETRY_SLEEP = 5` Provides reasonable time for API request blocks to lessen in the case of limits being reached
- `MAX_RETRIES = 4` In testing more than one retry was never reached, but this provides ample opportunities to requery

### judge_module.py
*Call to run judge tests on subject model results using judges defined in utils.JUDGE_MODELS. Models in utils.JUDGE_MODELS must be chosen from utils.SCHEMA_BEST_EFFORT_MODELS (models supported by Groq's API that allow for json_schema)*
```
python .\judge_module.py [--subject-timestamp "YYYYMMDDhhmmss" ] [--report-only] [--report-timestamp "YYYYMMDDhhmmss"] [--restart]
```
Global Variables:
- `API_SLEEP = 0.5` Selected to satisfy lowest judge RPM (30) defined in utils.py
- `RETRY_SLEEP = 5` Provides reasonable time for API request blocks to lessen in the case of limits being reached
- `MAX_RETRIES = 4` In testing more than one retry was never reached, but this provides ample opportunities to requery


### model_callers.py
*Stand alone model calling functions to ensure correct querying of both subject and judge models.*

Global Variables
- `RESPONSE_TIMEOUT = 60` Ensures module doesn't get stuck if API endpoint fails without returning. Provides enough time for longer responses to load.

### utils.py
*Provides extra utilities for more readable code. Primarily for file reading and writing, prompt formatting, data retrieval, and final model scoring helpers.*

### data/ 
*Directory for all stored output data*

### logs/ 
*Directory for failure logs*

### resources/judge_prompt.txt
*The judge instruction prompt uses paragraph style explanations of each metric to build general context. Examples are used to provide applied context to the model. General rubric gradepoint standards are defined to provide the model with a baseline to work off of.*

### example_run_data/
*Stores data from a run I ran locally to show what the expected output looks like*

## Misc Design Choices

### Json Arrays
- I continued to use the json array storage of model data. My current setup allows for safe handling of lists of model responses in memory without appending to jsonl after each response. Json arrays are also more human readable.
- Categories and qna_ids are propogated through each data output in the pipeline to allow for easier and more understandable useage

### Judge Module
- The ScoreKeeper class helps to more cleanly run final scores on model outputs
- Errors are checked for frequently (in subject_test.py too) to ensure quality logging and handling.
- The final judge prompt is combined in `utils.generate_judge_prompt()` which formats its output using XML tags to increase the likelihood of accurate contextualization from the LLM.
