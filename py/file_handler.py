import os
import json
import re
import threading

lock = threading.Lock()

DEFAULT_CONFIG_PATH = "user_data/config.json"

def edit_config(key, action, data):
    if action not in ("add", "remove", "edit"):
        raise ValueError(f"Invalid action: {action}. Supported actions are 'add' and 'remove'.")

    # Get the configuration file path
    config_path = os.path.join(DEFAULT_CONFIG_PATH)

    # Check if the path exists, create it if not
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    # Load existing configuration (empty dict if file doesn't exist)
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            if len(config) < 1:
                config = {}
    except:
        config = {}

    # Edit the configuration based on action
    message = ''
    if action == "add":
        if key not in config:
            config[key] = []
        if data not in config[key]:
            config[key].append(data)
            message = ' added successfully'
        else:
            message = ' already in your list'
    elif action == "edit":
        config[key] = data
    elif action == "remove":
        if key in config and isinstance(config[key], list):
            config[key] = [item for item in config[key] if item != data]
            message = ' removed from your list'
        else:
            raise TypeError(f"The value associated with key '{key}' is not a list.")

    # Save the updated configuration
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    return message

def read_config():
        # Get the configuration file path
    config_path = os.path.join(DEFAULT_CONFIG_PATH)

    # Check if the path exists, create it if not
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    # Load existing configuration (empty dict if file doesn't exist)
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            if len(config) < 1:
                config = {}
    except:
        config = {}

    return config

def read_json(path, file_name):
    file_name = sanitize_file_name(file_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file_path = os.path.join(path, file_name)
    #Check existing data
    try:
        with open(file_path, 'r') as f:
            file_data = json.load(f)
    except:
        file_data = {}
    return file_data


def sanitize_file_name(file_name):
    invalid_chars = r'[\\/:*?"<>|]'
    file_name = re.sub(invalid_chars, '_', file_name)
    file_name = file_name.strip()
    if not file_name:
        raise TypeError('General', 'FILE MANAGER', "File name cannot be empty")
    return file_name