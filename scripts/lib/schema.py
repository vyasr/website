from __future__ import annotations

from typing import ClassVar, Literal

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


class DisplayConfig(SchemaBaseModel):
    compact: bool = True
    extended: bool = True
    outdated: bool = False


class CVConfig(SchemaBaseModel):
    citations_mode: Literal["selectedpubs", "all", "none", "combinepubs"]
    selected_publications: list[str] = Field(default_factory=list)


class Education(SchemaBaseModel):
    institution: str
    degree: str
    area: str
    start: str
    end: str
    location: str
    advisor: str | None = None
    details: str | list[str] | None = None
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    compact_override: Education | None = None
    notes: str | None = None


class Experience(SchemaBaseModel):
    organization: str
    role: str
    start: str
    end: str
    location: str
    summary: str | None = None
    bullets: list[str] = Field(default_factory=list)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    notes: str | None = None
    latex_overrides: dict[str, str] | None = None


class Project(SchemaBaseModel):
    name: str
    url: str | None = None
    summary: str | None = None
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    notes: str | None = None
    latex_overrides: dict[str, str] | None = None


class Honor(SchemaBaseModel):
    title: str
    issuer: str | None = None
    location: str | None = None
    date: str | None = None
    summary: str | None = None
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    notes: str | None = None


class Service(SchemaBaseModel):
    role: str
    organization: str
    location: str | None = None
    date: str | None = None
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    notes: str | None = None


class Skill(SchemaBaseModel):
    category: str
    items: list[str]
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    latex_overrides: dict[str, str] | None = None


class Grant(SchemaBaseModel):
    title: str
    funder: str
    role: str
    amount: str | None = None
    start: str | None = None
    end: str | None = None
    details: list[str] = Field(default_factory=list)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    notes: str | None = None


class Affiliation(SchemaBaseModel):
    organization: str
    role: str | None = None
    date: str | None = None
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    notes: str | None = None


class Summary(SchemaBaseModel):
    text: str


class PublicationRef(SchemaBaseModel):
    cite_key: str
    display: DisplayConfig = Field(default_factory=DisplayConfig)


class PresentationRef(SchemaBaseModel):
    cite_key: str
    display: DisplayConfig = Field(default_factory=DisplayConfig)


class ProfessionalData(SchemaBaseModel):
    schema_version: str
    personal_info: PersonalInfo
    cv_config: CVConfig
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


_ = Education.model_rebuild()
