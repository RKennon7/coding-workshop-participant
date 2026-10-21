from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.security import BCRYPT_MAX_BYTES

ACME_EMAIL_DOMAIN = "acme.inc"

# lowercases the email and only accepts addresses on the company domain
def _validate_acme_email(value: str) -> str:
    value = value.strip().lower()
    local, _, domain = value.partition("@")
    if not local or domain != ACME_EMAIL_DOMAIN or " " in value:
        raise ValueError(f"must be a valid @{ACME_EMAIL_DOMAIN} email address")
    return value

AcmeEmail = Annotated[str, AfterValidator(_validate_acme_email)]

# bcrypt can't hash more than 72 bytes (fewer than 72 characters if they're not plain ASCII)
def _validate_password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"must be at most {BCRYPT_MAX_BYTES} bytes long")
    return value

NewPassword = Annotated[str, Field(min_length=8), AfterValidator(_validate_password_bytes)]

# base for every response schema: lets pydantic read straight from ORM objects
class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# minimal user info embedded in other responses (incident reporter, note author, ...)
class UserSummary(ORMModel):
    id: int
    username: str
