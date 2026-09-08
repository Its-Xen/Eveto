from pydantic import BaseModel, ConfigDict, Field


class VenueBase(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=["Madison Square Garden"])
    address: str = Field(
        min_length=1, max_length=650, examples=["4 Pennsylvania Plaza"]
    )
    city: str = Field(min_length=1, max_length=255, examples=["New York"])
    capacity: int = Field(gt=0, examples=[3000])


class VenueCreate(VenueBase):
    pass


class VenueUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1, max_length=650)
    city: str | None = Field(default=None, min_length=1, max_length=255)
    capacity: int | None = Field(default=None, gt=0)


class VenueRead(VenueBase):
    id: int
    created_by_id: int

    model_config = ConfigDict(from_attributes=True)
