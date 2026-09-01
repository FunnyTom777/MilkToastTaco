try:
    from core.systems.orchestrator import devmode, debug_mode, request_player_input, warning
except ImportError:
    from orchestrator import devmode, debug_mode, request_player_input, warning


def financepurchase(player_id, financed_item, item_value, item_name, repayment_period):
    repayment_period_not_specified = repayment_period is None

    if repayment_period_not_specified:  # Ask user to specify
        repayment_period = request_player_input(
            "How long of a Repayment Period would you like? (1-12 months): ",
            input_type="int",
            min_value=1,
            max_value=12,
        )
    else:  # Repayment period already specified - validate and confirm
        if not isinstance(repayment_period, int) or not 1 <= repayment_period <= 12:
            warning(f"Invalid repayment_period {repayment_period}, must be 1-12. Asking player to specify.")
            repayment_period = request_player_input(
                "How long of a Repayment Period would you like? (1-12 months): ",
                input_type="int",
                min_value=1,
                max_value=12,
            )
        else:
            confirmed = request_player_input(
                f"Are you sure you would like to Finance {item_name}, worth {item_value}, over a period of {repayment_period} months? (yes/no): ",
                input_type="bool",
            )
            if not confirmed:
                # Re-ask for period if not confirmed
                repayment_period = request_player_input(
                    "How long of a Repayment Period would you like? (1-12 months): ",
                    input_type="int",
                    min_value=1,
                    max_value=12,
                )

    if debug_mode:
        print(f"DEBUG: finance requested by player {player_id}, For item {item_name}, with value {item_value}, over repayment period {repayment_period}.")

    return repayment_period
