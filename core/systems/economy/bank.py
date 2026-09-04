try:
    from core.systems.orchestrator import bank_names, inform_player as infp, request_player_input, warning
    import core.systems.orchestrator as orchestrator
except ImportError:
    # Fallback for direct execution / different PYTHONPATH
    from orchestrator import bank_names, inform_player as infp, request_player_input, warning
    import orchestrator


def apply_bank_membership(player_id, bank_name):  # Banks should be loaded from a banks.xml!
    # Validate requested bank exists
    if bank_name not in bank_names:
        warning(f"Bank '{bank_name}' does not exist. Available banks: {bank_names}")
        return False

    current = orchestrator.current_bank_member

    if current is None:
        # No current membership - apply directly
        orchestrator.current_bank_member = bank_name
        infp(f"Successfully applied for membership with {bank_name}.")
        return True
    elif current == bank_name:
        infp(f"You're already a member of {bank_name}.")
        return True
    elif current in bank_names:
        # Currently already a member with another bank.
        infp(f"You're currently a member of another bank! ({current})")
        response = request_player_input(
            f"Would you like to cancel your membership with {current} and switch to {bank_name}? (yes/no): ",
            input_type="bool",
        )
        if response:
            orchestrator.current_bank_member = bank_name
            infp(f"Cancelled membership with {current} and switched to {bank_name}.")
            return True
        else:
            infp("Bank membership change aborted.")
            return False
    else:
        warning("Error when attempting to determine bank membership status.")
        return False




current_bank_supports_loans = True



def get_bank_loan():
    if current_bank_supports_loans == True:
        # continue
        request_player_input("This Bank Supports loans! Though i havent implemented the loan system yet... check back later :D")
    elif current_bank_supports_loans == False:
        warning("Your Current Bank does NOT support Loans! Please try with another bank!")
    else:
        warning("Error when determining if current bank supports loan.")



def list_active_cards():
    """
    Lists active bank cards (Credit/Debit) active on the players current bank account.
    Only lists ACTIVE cards. Not frozen/etc cards.
    """
    print("This does nothing yet...")