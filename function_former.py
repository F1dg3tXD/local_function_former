print("Thank you for using Function Former by Making Made Easy! If you would like to support this free project and Making Made Easy, please consider becoming a member of our Patreon at https://patreon.com/MakingMadeEasy ")

import requests
import subprocess
import os
import time
import json
import threading
import traceback
import sys

# OpenAI and LM Studio settings
OPENAI_URL = "https://api.openai.com/v1/completions"
LM_STUDIO_URL = "http://localhost:8080/v1/completions"  # Corrected endpoint for LM Studio

# Initialize initial_request to avoid undefined variable warnings
initial_request = ""

# Function to read chat history and handle user inputs
def handle_user_input(code, mode):
    global chat_history
    while True:
        try:
            user_input = input("Enter additional information (or type 'end chat' to finish): ")

            if user_input.lower() == 'end chat':
                break

            # Build prompt based on chat history
            prompt = "I'm trying to do this: " + initial_request + \
                     "\n\nCHAT HISTORY (oldest to newest):\n\n" + \
                     "\n".join(chat_history) + \
                     "\n\nACTUAL PROMPT: " + user_input + \
                     "\n\nCURRENT CODE:\n\n" + code

            # Decide based on user choice (OpenAI or LM Studio)
            if mode == 'openai':
                payload = {
                    "model": "text-davinci-003",
                    "prompt": prompt,
                    "max_tokens": 500,
                    "temperature": 0.7
                }
                headers = {
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
                }

                try:
                    # Send request to OpenAI
                    response = requests.post(OPENAI_URL, json=payload, headers=headers)
                    response.raise_for_status()  # Ensure we catch HTTP errors
                    result = response.json().get('choices', [{}])[0].get('text', '').strip()
                except Exception as e:
                    print(f"An error occurred while communicating with OpenAI: {e}")
                    break
            elif mode == 'lmstudio':
                # Payload for LM Studio
                payload = {
                    "prompt": prompt,
                    "max_tokens": 500,
                    "temperature": 0.7
                }

                try:
                    # Send request to LM Studio
                    response = requests.post(LM_STUDIO_URL, json=payload)
                    response.raise_for_status()  # Ensure we catch HTTP errors
                    result = response.json().get('text', '').strip()
                except Exception as e:
                    print(f"An error occurred while communicating with LM Studio: {e}")
                    break

            if result:
                print('Response: ' + result)
                print()
                chat_history.append('user input: ' + user_input)
                chat_history.append('AI response to user input: ' + result)
            else:
                print("Received an empty response. Exiting chat.")
                break

        except Exception as e:
            print(f"An error occurred while handling user input: {e}")
            break

# Monitor file changes and display
def display_file_contents():
    last_modified = None
    filename = 'generated_code.py'
    while True:
        try:
            current_modified = os.path.getmtime(filename)
            if last_modified is None or current_modified > last_modified:
                with open(filename, 'r') as file:
                    contents = file.read()
                print("\033[H\033[J", end="")  # Clear console screen
                print(contents)
                last_modified = current_modified
            time.sleep(1)
        except FileNotFoundError:
            print("File not found. Ensure the file exists.")
            time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping file monitoring.")
            break

# Modify print statements to log output
def modify_print_statements(lines):
    modified_lines = []
    for line in lines:
        stripped_line = line.lstrip()
        indent = ' ' * (len(line) - len(stripped_line))

        if "print(" in stripped_line:
            modified_lines.append(indent + stripped_line)
            log_content = str(stripped_line.split("print(", 1)[1].rsplit(")", 1)[0])
            log_line = f'{indent}with open("output.log", "a") as log_file: log_file.write({log_content} + "\\n")\n'
            modified_lines.append(log_line)
        else:
            modified_lines.append(line)
    return modified_lines

# Wrap code with try-except blocks for error logging
def wrap_with_try_except(lines):
    wrapped_lines = ['import traceback\n', 'try:\n']
    for line in lines:
        # Make sure each line inside the try block is indented properly
        if line.strip():  # Only indent non-empty lines
            wrapped_lines.append('    ' + line)
        else:
            wrapped_lines.append(line)
    
    # Add the except block with proper indentation
    wrapped_lines.extend([
        'except Exception:\n',
        '    with open("output.log", "a") as log_file:\n',
        '        traceback.print_exc(file=log_file)\n'
    ])
    return wrapped_lines

# Instrument file to log errors and output
def instrument_file(input_filename, output_filename):
    with open(input_filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    lines = wrap_with_try_except(lines)
    lines = modify_print_statements(lines)

    with open(output_filename, 'w', encoding='utf-8') as file:
        file.writelines(line if line.endswith('\n') else line + '\n' for line in lines)

# Monitor file size and terminate if it exceeds a limit
def monitor_file_size(log_file_path, max_lines, process):
    try:
        while process.poll() is None:
            with open(log_file_path, 'r') as file:
                line_count = sum(1 for line in file)
            if line_count > max_lines:
                print(f"Log file exceeded {max_lines} lines. Terminating process.")
                process.terminate()
                break
            time.sleep(1)
    except FileNotFoundError:
        print("Log file not found.")

# Main loop for code generation and execution
def validate_and_run_code(goal_file, mode):
    global chat_history
    error_count = {}

    initial_request1 = input('Please describe the function or script you want: ')
    new_or_existing = input('Generate new code or edit an existing file (1 for new, 2 for existing): ')

    if new_or_existing == '2':
        filename = input('Provide the existing python file name: ')
        with open(filename, 'r') as file:
            code = file.read()
    else:
        code = ""

    while True:
        try:
            if not initial_request1:
                with open(goal_file, 'r') as file:
                    initial_request = file.read().strip()
            else:
                initial_request = initial_request1
                with open(goal_file, 'w+') as file:
                    file.write(initial_request)

            if new_or_existing == '1':
                # Generate code using the chosen API (OpenAI or LM Studio)
                prompt = "Create a Python script: " + initial_request

                if mode == 'openai':
                    payload = {
                        "model": "text-davinci-003",
                        "prompt": prompt,
                        "max_tokens": 1000,
                        "temperature": 0.5
                    }
                    headers = {
                        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
                    }
                    response = requests.post(OPENAI_URL, json=payload, headers=headers)
                    response.raise_for_status()  # Ensure we catch HTTP errors
                    code = response.json().get('choices', [{}])[0].get('text', '').strip()
                elif mode == 'lmstudio':
                    payload = {
                        "prompt": prompt,
                        "max_tokens": 1000,
                        "temperature": 0.5
                    }
                    response = requests.post(LM_STUDIO_URL, json=payload)
                    response.raise_for_status()  # Ensure we catch HTTP errors
                    code = response.json().get('text', '').strip()

            # Check if the code is empty
            if not code:
                print("No code generated. Exiting.")
                break

            # Create 'generated_code' folder if it doesn't exist
            output_folder = 'generated_code'
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            # Save the generated code to a file in the 'generated_code' folder
            code_file_path = os.path.join(output_folder, 'generated_code.py')
            code_file_path_edited = os.path.join(output_folder, 'edited_code.py')

            with open(code_file_path, 'w+', encoding='utf-8') as file:
                file.write(code)

            # Instrument the code
            instrument_file(code_file_path, code_file_path_edited)

            # Monitor file changes
            monitor_thread = threading.Thread(target=monitor_file_size, args=("output.log", 100, process))
            monitor_thread.start()

            # Execute the code
            process = subprocess.Popen(['python', code_file_path_edited], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            while process.poll() is None:
                time.sleep(1)

            with open('output.log', 'r') as file:
                output = file.read()

            if "error" in output.lower():
                error_count[time.time()] = output
                if len(error_count) > 5:
                    print("More than 5 errors encountered. Exiting.")
                    break
            else:
                print("Code executed successfully.")
                break

            time.sleep(1)

            # Call the user input function
            handle_user_input(code, mode)
            break
        except Exception as e:
            print(f"An error occurred while processing: {str(e)}")
            traceback.print_exc(file=sys.stderr)
            break

if __name__ == "__main__":
    # Prompt for API mode
    mode = input("Choose API mode (openai/lmstudio): ").strip().lower()

    if mode not in ['openai', 'lmstudio']:
        print("Invalid mode selected.")
    else:
        goal_file = 'goal_file.txt'
        chat_history = []

        validate_and_run_code(goal_file, mode)
