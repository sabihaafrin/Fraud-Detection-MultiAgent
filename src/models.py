from pydantic import BaseModel, ConfigDict, Field, ValidationError


class InvalidTransaction(ValueError):
    pass


# Strings are restricted to short, fixed character sets because the
# transaction is included in the LLM prompts.
class Transaction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=False)

    id: str = Field(pattern=r"^T\d{3,10}$")
    customer_id: str = Field(pattern=r"^C\d{3,10}$")
    amount_gbp: float = Field(gt=0, le=1_000_000)
    country: str = Field(pattern=r"^[A-Z]{2}$")
    category: str = Field(pattern=r"^[a-z_]{1,32}$")
    hour: int = Field(ge=0, le=23)
    device_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    txns_last_hour: int = Field(ge=0, le=10_000)
    new_payee: bool
    minutes_since_last_txn: int = Field(ge=0)
    last_txn_country: str = Field(pattern=r"^[A-Z]{2}$")


def validate_transaction(txn: dict) -> dict:
    try:
        return Transaction.model_validate(txn).model_dump()
    except ValidationError as e:
        reasons = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}"
                            for err in e.errors())
        raise InvalidTransaction(f"Invalid transaction: {reasons}") from None
