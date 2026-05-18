from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.enums import LoginMethod, MediaType, PostCategory
from app.validation import validate_account_id, validate_bio, validate_password, validate_username


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordStartResponse(BaseModel):
    security_question: str


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    avatar_url: str | None = None
    bio: str | None = None


class PublicAuthorProfile(BaseModel):
    user: UserSummary
    posts_count: int
    total_likes_received: int


class PrivateProfile(BaseModel):
    id: str
    account_id: str
    username: str
    avatar_url: str | None = None
    bio: str | None = None
    posts_count: int
    favorites_count: int
    likes_count: int


class SessionStateResponse(BaseModel):
    authenticated: bool
    user: PrivateProfile | None = None


class AuthResponse(BaseModel):
    message: str
    user: PrivateProfile


class InteractionState(BaseModel):
    active: bool
    count: int


class PostMediaItem(BaseModel):
    id: str
    type: MediaType
    url: str
    thumbnail_url: str | None = None
    mime_type: str
    size_bytes: int
    sort_order: int


class PostSummary(BaseModel):
    id: str
    title: str
    body_excerpt: str | None = None
    category: PostCategory
    cover_url: str | None = None
    cover_source: str
    published_at: datetime
    updated_at: datetime
    author: UserSummary
    like_count: int
    favorite_count: int
    has_video: bool
    image_count: int


class PostDetail(PostSummary):
    body: str | None = None
    media: list[PostMediaItem]
    comment_count: int
    is_liked: bool
    is_favorited: bool
    can_edit: bool


class PaginatedPosts(BaseModel):
    items: list[PostSummary]
    total: int
    page: int
    page_size: int


class CommentNode(BaseModel):
    id: str
    body: str
    is_deleted: bool
    created_at: datetime
    author: UserSummary
    replies: list["CommentNode"] = Field(default_factory=list)


class CommentsResponse(BaseModel):
    items: list[CommentNode]


class RegisterRequest(BaseModel):
    account_id: str
    username: str
    password: str
    confirm_password: str
    security_question: str
    security_answer: str

    @model_validator(mode="after")
    def validate_fields(self) -> "RegisterRequest":
        self.account_id = validate_account_id(self.account_id)
        self.username = validate_username(self.username)
        self.password = validate_password(self.password)
        if self.password != self.confirm_password:
            raise ValueError("Password confirmation does not match.")
        if not self.security_question.strip():
            raise ValueError("Security question is required.")
        if not self.security_answer.strip():
            raise ValueError("Security answer is required.")
        self.security_question = self.security_question.strip()
        self.security_answer = self.security_answer.strip()
        return self


class LoginRequest(BaseModel):
    login_method: LoginMethod
    identifier: str
    password: str

    @model_validator(mode="after")
    def validate_fields(self) -> "LoginRequest":
        self.password = self.password.strip()
        if not self.password:
            raise ValueError("Password is required.")
        self.identifier = self.identifier.strip()
        if not self.identifier:
            raise ValueError("Identifier is required.")
        if self.login_method == LoginMethod.ACCOUNT_ID:
            self.identifier = validate_account_id(self.identifier)
        else:
            self.identifier = self.identifier.strip()
        return self


class ForgotPasswordStartRequest(BaseModel):
    account_id: str

    @model_validator(mode="after")
    def validate_fields(self) -> "ForgotPasswordStartRequest":
        self.account_id = validate_account_id(self.account_id)
        return self


class ForgotPasswordResetRequest(BaseModel):
    account_id: str
    security_answer: str
    new_password: str
    confirm_password: str

    @model_validator(mode="after")
    def validate_fields(self) -> "ForgotPasswordResetRequest":
        self.account_id = validate_account_id(self.account_id)
        self.new_password = validate_password(self.new_password)
        if self.new_password != self.confirm_password:
            raise ValueError("Password confirmation does not match.")
        if not self.security_answer.strip():
            raise ValueError("Security answer is required.")
        self.security_answer = self.security_answer.strip()
        return self


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

    @model_validator(mode="after")
    def validate_fields(self) -> "ChangePasswordRequest":
        if not self.old_password.strip():
            raise ValueError("Old password is required.")
        self.new_password = validate_password(self.new_password)
        if self.new_password != self.confirm_password:
            raise ValueError("Password confirmation does not match.")
        return self


class UpdateProfileRequest(BaseModel):
    username: str
    bio: str | None = None

    @model_validator(mode="after")
    def validate_fields(self) -> "UpdateProfileRequest":
        self.username = validate_username(self.username)
        self.bio = validate_bio(self.bio)
        return self


class CommentCreateRequest(BaseModel):
    body: str

    @model_validator(mode="after")
    def validate_fields(self) -> "CommentCreateRequest":
        self.body = self.body.strip()
        if not self.body:
            raise ValueError("Comment cannot be empty.")
        return self


CommentNode.model_rebuild()

