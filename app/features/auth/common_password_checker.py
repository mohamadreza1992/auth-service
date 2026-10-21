from pathlib import Path


class CommonPasswordChecker:
    def __init__(self, passwords_file: Path | None = None) -> None:
        if passwords_file is None:
            passwords_file = Path(__file__).parent / "data" / "common_passwords.txt"

        try:
            with passwords_file.open(encoding="utf-8") as file:
                self._passwords = {
                    line.strip().casefold() for line in file if line.strip()
                }
        except OSError as exc:
            raise RuntimeError(
                f"Could not load common passwords from {passwords_file}"
            ) from exc

    def is_common(self, password: str) -> bool:
        return password.casefold() in self._passwords
