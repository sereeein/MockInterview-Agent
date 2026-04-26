from pydantic import BaseModel, Field


class Education(BaseModel):
    school: str
    degree: str
    major: str
    graduation: str


class Basic(BaseModel):
    name: str
    education: list[Education] = []


class ResumeProject(BaseModel):
    title: str
    period: str
    role: str = ""
    description: str
    outcomes: str = ""


class WorkExperience(BaseModel):
    company: str
    title: str
    period: str
    responsibilities: str
    outcomes: str = ""


class ResumeStructured(BaseModel):
    basic: Basic
    projects: list[ResumeProject] = Field(default_factory=list)
    work_experience: list[WorkExperience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
