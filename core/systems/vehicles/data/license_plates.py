import secrets
import string

from orchestrator import warning


registered_license_plates = []


def register_new_licenseplate(licenseplate):
    """Registers a new license plate if it is not already registered."""

    if licenseplate in registered_license_plates:
        warning(
            "Provided License Plate Already registered. "
            "Please provide a NON registered license plate. Action Aborted."
        )
        return False

    registered_license_plates.append(licenseplate)
    return True


def return_all_registered_licenseplates():
    """Returns all currently registered license plates."""
    return registered_license_plates


def generate_new_licenseplate(nodash=False):
    """
    Generates a unique 7-character license plate.

    Format:
        ABC-1234
    Or with nodash=True:
        ABC1234
    """

    if not isinstance(nodash, bool):
        warning("Invalid option for 'nodash'.")
        return None

    characters = string.ascii_uppercase + string.digits

    while True:
        if nodash:
            licenseplate = ''.join(
                secrets.choice(characters) for _ in range(7)
            )
        else:
            licenseplate = (
                ''.join(secrets.choice(characters) for _ in range(3))
                + '-'
                + ''.join(secrets.choice(characters) for _ in range(4))
            )

        if licenseplate not in registered_license_plates:
            return licenseplate

        warning(
            f"Generated License Plate {licenseplate} already registered. "
            "Re-generating..."
        )