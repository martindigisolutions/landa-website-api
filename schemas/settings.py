"""
Store Settings schemas for configuration management
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ---------- Setting Item ----------

class SettingBase(BaseModel):
    """Base schema for a setting"""
    key: str
    value: Optional[str] = None


class SettingCreate(SettingBase):
    """Schema for creating a setting"""
    value_type: str = "string"  # "string", "number", "boolean", "json"
    description: Optional[str] = None


class SettingUpdate(BaseModel):
    """Schema for updating a setting value"""
    value: str


class SettingResponse(BaseModel):
    """Full setting response"""
    id: int
    key: str
    value: Optional[str] = None
    value_type: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingPublic(BaseModel):
    """Public setting (key-value only)"""
    key: str
    value: Optional[str] = None
    value_type: str

    class Config:
        from_attributes = True


# ---------- Bulk Operations ----------

class BulkSettingItem(BaseModel):
    """Item for bulk update"""
    key: str
    value: str


class BulkSettingsUpdate(BaseModel):
    """Schema for bulk updating settings"""
    settings: List[BulkSettingItem]


class BulkSettingsResponse(BaseModel):
    """Response for bulk update"""
    success: bool
    message: str
    updated_count: int


# ---------- Settings List Response ----------

class SettingsListResponse(BaseModel):
    """Response containing list of settings"""
    settings: List[SettingResponse]


# ---------- Tax Calculation Response ----------

class TaxCalculationResult(BaseModel):
    """Result of tax calculation"""
    tax_amount: float
    tax_rate: float
    tax_source: str  # "grt_api", "fixed_rate", "store_rate", "none"
    success: bool
    error_message: Optional[str] = None


# ---------- Store Address ----------

class StoreAddress(BaseModel):
    """Store address for tax calculation"""
    street_number: str
    street_name: str
    street_suffix: Optional[str] = None
    street_direction: Optional[str] = None
    city: str
    state: str
    zipcode: str


# ---------- Shipping Address for Tax ----------

class TaxAddress(BaseModel):
    """Address for tax calculation"""
    street_number: Optional[str] = None
    street_name: Optional[str] = None
    street_suffix: Optional[str] = None
    street_direction: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None
    
    def is_complete(self) -> bool:
        """Check if address has minimum required fields"""
        return bool(self.city and self.state and self.zipcode)
    
    def is_new_mexico(self) -> bool:
        """Check if address is in New Mexico"""
        return self.state and self.state.upper() in ("NM", "NEW MEXICO")
