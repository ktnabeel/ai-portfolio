import getpass
import os

try:
    import keyring
except ImportError:  # pragma: no cover - optional dependency fallback
    keyring = None

SERVICE_NAME = "ai-portfolio-vps"


def get_vps_password(ip: str, user: str, env_var: str = "VPS_PASSWORD") -> str:
    """Return the VPS password from the environment, keyring, or an interactive prompt.

    Args:
        ip: The SSH target IP address.
        user: The SSH username.
        env_var: Environment variable name checked before keyring or prompt fallback.

    Returns:
        The SSH password.

    Raises:
        RuntimeError: If no password can be resolved.
    """
    password = os.environ.get(env_var)
    if password:
        return password

    if keyring is not None:
        try:
            stored_password = keyring.get_password(SERVICE_NAME, f"{user}@{ip}")
            if stored_password:
                return stored_password
        except Exception:
            pass

    password = getpass.getpass(f"Enter SSH password for {user}@{ip}: ")
    if not password:
        raise RuntimeError(
            f"Missing password for {user}@{ip}. Set {env_var} or store it in keyring."
        )

    if keyring is not None:
        try:
            keyring.set_password(SERVICE_NAME, f"{user}@{ip}", password)
        except Exception:
            pass

    return password
