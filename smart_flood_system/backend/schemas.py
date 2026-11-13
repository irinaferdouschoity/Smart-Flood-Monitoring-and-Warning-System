from datetime import date,datetime
from pydantic import BaseModel,Field
class LocationCreate(BaseModel):
    location_name:str=Field(min_length=1,max_length=150); country:str=Field(min_length=1,max_length=100); latitude:float=Field(ge=-90,le=90); longitude:float=Field(ge=-180,le=180)
class LocationOut(LocationCreate):
    location_id:int; created_at:datetime
    class Config: from_attributes=True
class WeatherOut(BaseModel):
    observation_date:date; precipitation:float|None; temperature_avg:float|None; temperature_max:float|None; temperature_min:float|None; humidity:float|None; dew_point:float|None; wind_speed:float|None; surface_pressure:float|None; data_source:str
    class Config: from_attributes=True
class FloodEventOut(BaseModel):
    event_date:date; flood_occurred:bool; severity:str|None; affected_area:float|None; source:str|None; description:str|None
    class Config: from_attributes=True
class PredictionOut(BaseModel):
    prediction_time:datetime; flood_probability:float; risk_level:str; model_version:str
    class Config: from_attributes=True
class PredictionRequest(BaseModel): location_id:int
