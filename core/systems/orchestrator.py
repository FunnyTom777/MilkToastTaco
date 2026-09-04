import datetime
import os

devmode = True  # This should eventually be loaded from a config.xml, but hardcoded for now.
debug_mode = True  # Enables Debug Printing across MTT!
current_bank_member = None  # Placeholder - None means no membership, otherwise bank name string

bank_names = ["bank1"]


def request_player_input(
    text: str,
    input_type: str = "string",
    max_length: int | None = None,
    min_length: int | None = None,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
    allowed_values: list | None = None,
    case_sensitive: bool = False,
    allow_empty: bool = False,
):
    """
    Request and validate player input with caller-defined limits.

    Args:
        text: Prompt displayed to the player.
        input_type: Restrict to "string", "int", "float", "bool".
        max_length: Maximum allowed string length (for string type).
        min_length: Minimum required string length (for string type).
        min_value: Minimum allowed numeric value (for int/float).
        max_value: Maximum allowed numeric value (for int/float).
        allowed_values: Explicit allowlist (e.g. ["yes", "no"] or [1,2,3]).
                        Compared case-insensitively unless case_sensitive=True.
        case_sensitive: Whether allowed_values comparison is case-sensitive.
        allow_empty: If False, empty/whitespace-only input is rejected.

    Returns:
        Validated value coerced to the requested type (str/int/float/bool).
    """
    valid_types = {"string", "str", "int", "integer", "float", "bool", "boolean"}
    normalized_type = input_type.lower().strip()
    if normalized_type not in valid_types:
        warning(f"request_player_input called with unknown input_type '{input_type}', defaulting to 'string'")
        normalized_type = "string"

    # Normalize type aliases
    if normalized_type == "str":
        normalized_type = "string"
    elif normalized_type == "integer":
        normalized_type = "int"
    elif normalized_type == "boolean":
        normalized_type = "bool"

    # Prepare allowed_values lookup
    allowed_normalized = None
    if allowed_values is not None:
        if not case_sensitive and normalized_type in ("string", "bool"):
            allowed_normalized = [str(v).lower() for v in allowed_values]
        else:
            allowed_normalized = list(allowed_values)

    while True:
        raw = input(text)

        # Handle empty
        if not allow_empty and raw.strip() == "":
            inform_player("Input cannot be empty. Please try again.")
            continue

        # --- Bool handling ---
        if normalized_type == "bool":
            lowered = raw.strip().lower()
            bool_map = {
                "true": True, "false": False,
                "yes": True, "no": False,
                "y": True, "n": False,
                "1": True, "0": False,
                "abort": True, "cancel": True,  # for bank membership prompt compatibility
                "cancle": True,  # common typo tolerance
            }
            if lowered in bool_map:
                value = bool_map[lowered]
            else:
                inform_player("Please enter a boolean value (yes/no, true/false, y/n, 1/0).")
                continue

            if allowed_normalized is not None:
                # For bool, allowed_values should contain booleans
                if value not in allowed_values and lowered not in allowed_normalized:
                    inform_player(f"Input must be one of: {allowed_values}")
                    continue
            return value

        # --- Int handling ---
        if normalized_type == "int":
            try:
                value = int(raw.strip())
            except ValueError:
                inform_player("Please enter a valid whole number (int).")
                continue

            if min_value is not None and value < min_value:
                inform_player(f"Value must be >= {min_value}.")
                continue
            if max_value is not None and value > max_value:
                inform_player(f"Value must be <= {max_value}.")
                continue
            if allowed_normalized is not None and value not in allowed_normalized:
                inform_player(f"Input must be one of: {allowed_values}")
                continue
            return value

        # --- Float handling ---
        if normalized_type == "float":
            try:
                value = float(raw.strip())
            except ValueError:
                inform_player("Please enter a valid number.")
                continue

            if min_value is not None and value < min_value:
                inform_player(f"Value must be >= {min_value}.")
                continue
            if max_value is not None and value > max_value:
                inform_player(f"Value must be <= {max_value}.")
                continue
            if allowed_normalized is not None and value not in allowed_normalized:
                inform_player(f"Input must be one of: {allowed_values}")
                continue
            return value

        # --- String handling ---
        value = raw if case_sensitive else raw  # keep original casing for return
        check_val = value if case_sensitive else value.lower()

        # Length checks
        if min_length is not None and len(value) < min_length:
            inform_player(f"Input too short. Minimum length is {min_length}.")
            continue
        if max_length is not None and len(value) > max_length:
            inform_player(f"Input too long. Maximum length is {max_length}.")
            continue

        # Allowed values check
        if allowed_normalized is not None:
            if check_val not in allowed_normalized and value not in allowed_normalized:
                inform_player(f"Input must be one of: {allowed_values}")
                continue

        # Numeric range also applies to string length? No, skip.

        return value


def inform_player(text):
    # Route through universal output bus so dashboards/game see it (also prints fallback)
    try:
        from core.output import print_to_user as _ptu
        _ptu(str(text), level="info", channel="general", source="orchestrator")
        return
    except Exception:
        pass
    print(text)


def warning(warning_note):  # Should also eventually save it to a log.txt, with timestamp :D
    # Route through universal output bus (handles buffer + file + dashboard poll)
    try:
        from core.output import warning as _out_warn
        _out_warn(str(warning_note), channel="general", source="orchestrator")
        return
    except Exception:
        pass
    timestamp = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
    msg = f"[{timestamp}] WARNING: {warning_note}"
    print(msg)
    # Append to log file
    try:
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "log.txt")
        # Fallback: if logs dir doesn't exist, try relative
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception as e:
        # Don't crash on logging failure, but show debug info if enabled
        if debug_mode:
            print(f"DEBUG: Failed to write warning to log.txt: {e}")




def display_phone_ui():
    print("*Displayed Phone UI* This dosent exist yet though....")



def thisdoesnothing():
    warning("This does nothing yet...")