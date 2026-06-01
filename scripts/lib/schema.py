from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SchemaBaseModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")


class PersonalInfo(SchemaBaseModel):
    name: str
    email: str
    phone: str | None = None
    website: str | None = None
    github: str | None = None
    linkedin: str | None = None
    location: str | None = None


class Education(SchemaBaseModel):
    id: str
    institution: str
    degree: str
    area: str
    start: str
    end: str
    location: str
    advisor: str | None = None
    details: str | list[str] | None = None
    formatted: dict[str, dict[str, str]] | None = None
    notes: str | None = None


class Experience(SchemaBaseModel):
    id: str
    organization: str
    role: str
    start: str
    end: str
    location: str
    summary: str | None = None
    bullets: list[str] = Field(default_factory=list)
    formatted: dict[str, dict[str, str]] | None = None
    notes: str | None = None


class Project(SchemaBaseModel):
    id: str
    name: str
    url: str | None = None
    summary: str | None = None
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    formatted: dict[str, dict[str, str]] | None = None
    notes: str | None = None


class Honor(SchemaBaseModel):
    id: str
    title: str
    issuer: str | None = None
    location: str | None = None
    date: str | None = None
    summary: str | None = None
    notes: str | None = None


class Service(SchemaBaseModel):
    id: str
    role: str
    organization: str
    location: str | None = None
    date: str | None = None
    notes: str | None = None


class Skill(SchemaBaseModel):
    id: str
    category: str
    items: list[str]
    formatted: dict[str, dict[str, str]] | None = None
    notes: str | None = None


class Grant(SchemaBaseModel):
    id: str
    title: str
    funder: str
    role: str
    amount: str | None = None
    start: str | None = None
    end: str | None = None
    details: list[str] = Field(default_factory=list)
    notes: str | None = None


class Affiliation(SchemaBaseModel):
    id: str
    organization: str
    role: str | None = None
    date: str | None = None
    notes: str | None = None


class Summary(SchemaBaseModel):
    text: str


class PublicationRef(SchemaBaseModel):
    cite_key: str


class PresentationRef(SchemaBaseModel):
    cite_key: str


class ProfessionalData(SchemaBaseModel):
    schema_version: str
    personal_info: PersonalInfo
    education: list[Education] = Field(default_factory=list)
    research_experience: list[Experience] = Field(default_factory=list)
    work_experience: list[Experience] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    honors: list[Honor] = Field(default_factory=list)
    service_leadership: list[Service] = Field(default_factory=list)
    teaching_experience: list[Experience] = Field(default_factory=list)
    grants: list[Grant] = Field(default_factory=list)
    extracurricular: list[Experience] = Field(default_factory=list)
    affiliations: list[Affiliation] = Field(default_factory=list)
    wetlab_skills: list[Skill] = Field(default_factory=list)
    summary: Summary | None = None
    publications: list[PublicationRef] = Field(default_factory=list)
    presentations: list[PresentationRef] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        if value != "1.0":
            raise ValueError("schema_version must be '1.0'")
        return value
