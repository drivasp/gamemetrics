from pydantic import BaseModel


class RegisterDTO(BaseModel):
    email: str
    password: str
    display_name: str | None = None


class LoginDTO(BaseModel):
    email: str
    password: str


class UserDTO(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    avatar: str | None = None
    bio: str | None = None


class AuthResponseDTO(BaseModel):
    token: str
    user: UserDTO


class UpdateProfileDTO(BaseModel):
    display_name: str | None = None
    bio: str | None = None
