from dataclasses import dataclass


@dataclass(frozen=True)
class Currency:
    code: str

    def __post_init__(self):
        if not self.code:
            raise ValueError("Currency code cannot be empty")
        if not self.code.replace("_", "").isalnum():
            raise ValueError(
                f"Currency code must only contain letters, numbers, and underscores: {self.code}"
            )
        if len(self.code) < 1 or len(self.code) > 20:
            raise ValueError(f"Currency code must be 1-20 characters: {self.code}")

        object.__setattr__(self, "code", self.code.upper())

    def __str__(self) -> str:
        return self.code

    def __eq__(self, other: "Currency") -> bool:
        return self.code == other.code

    def __hash__(self) -> int:
        return hash(self.code)
