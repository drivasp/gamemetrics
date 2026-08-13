from pydantic import BaseModel, Field


class RegisterDTO(BaseModel):
    email: str
    password: str
    display_name: str | None = None
    country_code: str = Field(min_length=2, max_length=2)


class LoginDTO(BaseModel):
    email: str
    password: str


class UserDTO(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    avatar: str | None = None
    bio: str | None = None
    country_code: str | None = None
    role: str = "player"


class AuthResponseDTO(BaseModel):
    token: str
    user: UserDTO


class UpdateProfileDTO(BaseModel):
    display_name: str | None = None
    bio: str | None = None


class BootstrapAdminDTO(BaseModel):
    email: str
    password: str
    display_name: str | None = None
    secret: str
    country_code: str = Field(default="US", min_length=2, max_length=2)


class SetRoleDTO(BaseModel):
    role: str = Field(min_length=4, max_length=20)
