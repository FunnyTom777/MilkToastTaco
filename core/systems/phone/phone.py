try:
    from core.systems.orchestrator import display_phone_ui, warning, thisdoesnothing
except ImportError:
    from orchestrator import display_phone_ui, warning, thisdoesnothing

try:
    from core.command_registry import command as _command
except ImportError:
    def _command(*a, **k):
        def _d(fn):
            return fn
        return _d



contacts_list = {}


# Players Phone System:


@_command("phone.open", "Open the phone UI", category="player")
def open_phone():
    display_phone_ui()
    thisdoesnothing()


def open_app(app_id):
    thisdoesnothing()


def play_sound(sound_id):
    """
    Plays a sound via the phone app.
    """
    thisdoesnothing()
    warning(f"Phone App called to play sound {sound_id}")

def open_phone_keypad():
    """
    Opens the keypad on the user phone UI.
    Returns whatever the user inputs.

    User can only input numbers and '#', and then enter.
    """
    thisdoesnothing()
    user_input = "1"
    return user_input

def exit_app():
    """
    Closes the active app and returns to the home screen.
    """
    thisdoesnothing()


@_command("phone.get_contacts", "Get all phone contacts", category="player")
def get_contacts():
    """
    Returns all registered contacts in the players phone contacts list.
    This contacts list is phone wide and can be used by any apps.
    """
    return contacts_list

@_command("phone.new_contact", "Register a new phone contact", category="player")
def new_contact(contact_name, contact_number):
    """
    Registers a new contact in the players phone contact list.
    """
    thisdoesnothing()

@_command("phone.delete_contact", "Delete a phone contact", category="player")
def delete_contact(contact_name):
    """
    Deletes a existing contact in the players phone contact list.
    """
    thisdoesnothing()