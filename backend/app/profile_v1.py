# Generated from packages/schema/profile.v1.schema.json. Do not edit:
# run `uv run datamodel-codegen` instead.

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from app.profile_base import Base


class Phone(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    countryCode: Annotated[str, Field(pattern="^\\+\\d{1,4}$")]
    number: Annotated[str, Field(pattern="^\\d{4,15}$")]


class Address(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    street: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    city: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    region: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    postcode: Annotated[str | None, Field(max_length=20, pattern="\\S")] = None
    country: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None


class Personal(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    firstName: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    lastName: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    preferredName: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    headline: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    email: Annotated[
        str | None,
        Field(
            max_length=300,
            pattern="^(?:[A-Za-z0-9_'+\\-]+\\.)*[A-Za-z0-9_'+\\-]*[A-Za-z0-9_+-]@(?:[A-Za-z0-9][A-Za-z0-9\\-]*\\.)+[A-Za-z]{2,}$",
        ),
    ] = None
    phone: Phone | None = None
    address: Address | None = None


class Link(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    kind: Literal[
        "linkedin", "github", "portfolio", "website", "scholar", "orcid", "other"
    ]
    label: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    url: Annotated[str, Field(max_length=2048, pattern="^[Hh][Tt][Tt][Pp][Ss]?:\\/\\/")]


class Start(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    year: Annotated[int, Field(ge=1900, le=2100)]
    month: Annotated[int | None, Field(ge=1, le=12)] = None


class End(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    year: Annotated[int, Field(ge=1900, le=2100)]
    month: Annotated[int | None, Field(ge=1, le=12)] = None


type Bullet = Annotated[str, Field(max_length=1000, pattern="\\S")]


type ShortItem = Annotated[str, Field(max_length=1000, pattern="\\S")]


type LongItem = Annotated[str, Field(max_length=1000, pattern="\\S")]


class Variants(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    short: Annotated[list[ShortItem] | None, Field(max_length=50)] = None
    long: Annotated[list[LongItem] | None, Field(max_length=50)] = None


type Alias = Annotated[str, Field(max_length=300, pattern="\\S")]


class WorkItem(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    company: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    title: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    employmentType: (
        Literal["full-time", "part-time", "contract", "internship", "freelance"] | None
    ) = None
    location: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    workplace: Literal["remote", "hybrid", "on-site"] | None = None
    start: Start | None = None
    end: End | None = None
    current: bool | None = None
    bullets: Annotated[list[Bullet] | None, Field(max_length=50)] = None
    variants: Variants | None = None
    aliases: Annotated[list[Alias] | None, Field(max_length=50)] = None


type Technology = Annotated[str, Field(max_length=300, pattern="\\S")]


class Variants1(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    short: Annotated[list[ShortItem] | None, Field(max_length=50)] = None
    long: Annotated[list[LongItem] | None, Field(max_length=50)] = None


class Project(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    name: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    role: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    organisation: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    start: Start | None = None
    end: End | None = None
    current: bool | None = None
    url: Annotated[
        str | None, Field(max_length=2048, pattern="^[Hh][Tt][Tt][Pp][Ss]?:\\/\\/")
    ] = None
    repositoryUrl: Annotated[
        str | None, Field(max_length=2048, pattern="^[Hh][Tt][Tt][Pp][Ss]?:\\/\\/")
    ] = None
    technologies: Annotated[list[Technology] | None, Field(max_length=50)] = None
    bullets: Annotated[list[Bullet] | None, Field(max_length=50)] = None
    variants: Variants1 | None = None


type Module = Annotated[str, Field(max_length=300, pattern="\\S")]


class Variants2(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    short: Annotated[list[ShortItem] | None, Field(max_length=50)] = None
    long: Annotated[list[LongItem] | None, Field(max_length=50)] = None


class EducationItem(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    school: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    degree: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    fieldOfStudy: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    minor: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    start: Start | None = None
    end: End | None = None
    current: bool | None = None
    grade: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    thesisTitle: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    modules: Annotated[list[Module] | None, Field(max_length=50)] = None
    bullets: Annotated[list[Bullet] | None, Field(max_length=50)] = None
    variants: Variants2 | None = None
    aliases: Annotated[list[Alias] | None, Field(max_length=50)] = None


type Author = Annotated[str, Field(max_length=300, pattern="\\S")]


class Date(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    year: Annotated[int, Field(ge=1900, le=2100)]
    month: Annotated[int | None, Field(ge=1, le=12)] = None


class Publication(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    title: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    authors: Annotated[list[Author] | None, Field(max_length=50)] = None
    venue: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    date: Date | None = None
    doi: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    url: Annotated[
        str | None, Field(max_length=2048, pattern="^[Hh][Tt][Tt][Pp][Ss]?:\\/\\/")
    ] = None
    status: Literal["published", "accepted", "under-review", "preprint"] | None = None


class IssueDate(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    year: Annotated[int, Field(ge=1900, le=2100)]
    month: Annotated[int | None, Field(ge=1, le=12)] = None


class ExpiryDate(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    year: Annotated[int, Field(ge=1900, le=2100)]
    month: Annotated[int | None, Field(ge=1, le=12)] = None


class Certification(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    name: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    issuer: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    issueDate: IssueDate | None = None
    expiryDate: ExpiryDate | None = None
    credentialId: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    url: Annotated[
        str | None, Field(max_length=2048, pattern="^[Hh][Tt][Tt][Pp][Ss]?:\\/\\/")
    ] = None


class Skill(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    name: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    category: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    level: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    years: Annotated[float | None, Field(ge=0.0, le=60.0)] = None


class Language(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    language: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    proficiency: (
        Literal["native", "fluent", "professional", "conversational", "basic"] | None
    ) = None


class Variants3(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    short: Annotated[list[ShortItem] | None, Field(max_length=50)] = None
    long: Annotated[list[LongItem] | None, Field(max_length=50)] = None


class Award(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    title: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    issuer: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    date: Date | None = None
    bullets: Annotated[list[Bullet] | None, Field(max_length=50)] = None
    variants: Variants3 | None = None


class Variants4(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    short: Annotated[list[ShortItem] | None, Field(max_length=50)] = None
    long: Annotated[list[LongItem] | None, Field(max_length=50)] = None


class VolunteeringItem(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    organisation: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    role: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    start: Start | None = None
    end: End | None = None
    current: bool | None = None
    bullets: Annotated[list[Bullet] | None, Field(max_length=50)] = None
    variants: Variants4 | None = None
    aliases: Annotated[list[Alias] | None, Field(max_length=50)] = None


class CompletionDate(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    year: Annotated[int, Field(ge=1900, le=2100)]
    month: Annotated[int | None, Field(ge=1, le=12)] = None


class Course(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    name: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    provider: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    completionDate: CompletionDate | None = None


class Membership(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    organisation: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    level: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    start: Start | None = None


class Talk(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    title: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    event: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    date: Date | None = None
    url: Annotated[
        str | None, Field(max_length=2048, pattern="^[Hh][Tt][Tt][Pp][Ss]?:\\/\\/")
    ] = None


class Patent(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    title: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    number: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    status: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    date: Date | None = None


class Reference(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            pattern="^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        ),
    ]
    name: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    title: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    organisation: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None
    email: Annotated[
        str | None,
        Field(
            max_length=300,
            pattern="^(?:[A-Za-z0-9_'+\\-]+\\.)*[A-Za-z0-9_'+\\-]*[A-Za-z0-9_+-]@(?:[A-Za-z0-9][A-Za-z0-9\\-]*\\.)+[A-Za-z]{2,}$",
        ),
    ] = None
    phone: Annotated[str | None, Field(max_length=30, pattern="\\S")] = None
    relationship: Annotated[str | None, Field(max_length=300, pattern="\\S")] = None


class ProfileV1(Base):
    model_config = ConfigDict(
        extra="forbid",
    )
    schemaVersion: Literal[1]
    personal: Personal | None = None
    summary: Annotated[str | None, Field(max_length=5000, pattern="\\S")] = None
    links: Annotated[
        list[Link] | None, Field(max_length=100, validate_default=True)
    ] = []
    work: Annotated[
        list[WorkItem] | None, Field(max_length=100, validate_default=True)
    ] = []
    projects: Annotated[
        list[Project] | None, Field(max_length=100, validate_default=True)
    ] = []
    education: Annotated[
        list[EducationItem] | None, Field(max_length=100, validate_default=True)
    ] = []
    publications: Annotated[
        list[Publication] | None, Field(max_length=100, validate_default=True)
    ] = []
    certifications: Annotated[
        list[Certification] | None, Field(max_length=100, validate_default=True)
    ] = []
    skills: Annotated[
        list[Skill] | None, Field(max_length=100, validate_default=True)
    ] = []
    languages: Annotated[
        list[Language] | None, Field(max_length=100, validate_default=True)
    ] = []
    awards: Annotated[
        list[Award] | None, Field(max_length=100, validate_default=True)
    ] = []
    volunteering: Annotated[
        list[VolunteeringItem] | None, Field(max_length=100, validate_default=True)
    ] = []
    courses: Annotated[
        list[Course] | None, Field(max_length=100, validate_default=True)
    ] = []
    memberships: Annotated[
        list[Membership] | None, Field(max_length=100, validate_default=True)
    ] = []
    talks: Annotated[
        list[Talk] | None, Field(max_length=100, validate_default=True)
    ] = []
    patents: Annotated[
        list[Patent] | None, Field(max_length=100, validate_default=True)
    ] = []
    references: Annotated[
        list[Reference] | None, Field(max_length=100, validate_default=True)
    ] = []
