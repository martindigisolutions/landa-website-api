"""
Store Settings service for managing configuration
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from models import StoreSettings
from schemas.settings import (
    SettingCreate, SettingUpdate, BulkSettingItem,
    SettingResponse
)


# Default settings to seed on first run
DEFAULT_SETTINGS = [
    # Store Address
    {"key": "store_street_number", "value": "", "value_type": "string", "description": "Store street number"},
    {"key": "store_street_name", "value": "", "value_type": "string", "description": "Store street name"},
    {"key": "store_street_suffix", "value": "", "value_type": "string", "description": "Store street suffix (Ave, St, Blvd)"},
    {"key": "store_street_direction", "value": "", "value_type": "string", "description": "Store street direction (NE, NW, SE, SW)"},
    {"key": "store_city", "value": "", "value_type": "string", "description": "Store city"},
    {"key": "store_state", "value": "NM", "value_type": "string", "description": "Store state (2-letter code)"},
    {"key": "store_zipcode", "value": "", "value_type": "string", "description": "Store ZIP code"},
    
    # Tax Settings
    {"key": "tax_enabled", "value": "true", "value_type": "boolean", "description": "Enable tax calculation"},
    {"key": "tax_calculation_method", "value": "grt_api", "value_type": "string", "description": "Tax method: grt_api, fixed_rate, none"},
    {"key": "tax_fixed_rate", "value": "0", "value_type": "number", "description": "Fixed tax rate percentage"},
    {"key": "tax_apply_to_shipping", "value": "false", "value_type": "boolean", "description": "Apply tax to shipping cost"},
    
    # Order Limits
    {"key": "min_order_amount", "value": "50", "value_type": "number", "description": "Minimum order amount in dollars"},
    {"key": "max_order_amount", "value": "2000", "value_type": "number", "description": "Maximum order amount in dollars"},
]


class SettingsService:
    """Service for managing store settings"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_settings(self) -> List[StoreSettings]:
        """Get all settings"""
        return self.db.query(StoreSettings).order_by(StoreSettings.key).all()
    
    def get_setting(self, key: str) -> Optional[StoreSettings]:
        """Get a single setting by key"""
        return self.db.query(StoreSettings).filter(
            StoreSettings.key == key
        ).first()
    
    def get_setting_value(self, key: str, default: str = "") -> str:
        """Get setting value, with default fallback"""
        setting = self.get_setting(key)
        return setting.value if setting and setting.value else default
    
    def get_setting_as_float(self, key: str, default: float = 0.0) -> float:
        """Get setting value as float"""
        try:
            return float(self.get_setting_value(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def get_setting_as_bool(self, key: str, default: bool = False) -> bool:
        """Get setting value as boolean"""
        value = self.get_setting_value(key, str(default).lower())
        return value.lower() in ("true", "1", "yes")
    
    def create_setting(self, data: SettingCreate) -> StoreSettings:
        """Create a new setting"""
        setting = StoreSettings(
            key=data.key,
            value=data.value,
            value_type=data.value_type,
            description=data.description
        )
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting
    
    def update_setting(self, key: str, value: str) -> Optional[StoreSettings]:
        """Update a setting value"""
        setting = self.get_setting(key)
        if not setting:
            return None
        
        setting.value = value
        setting.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(setting)
        return setting
    
    def update_settings_bulk(self, items: List[BulkSettingItem]) -> int:
        """Update multiple settings at once"""
        updated_count = 0
        
        for item in items:
            setting = self.get_setting(item.key)
            if setting:
                setting.value = item.value
                setting.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create if doesn't exist
                new_setting = StoreSettings(
                    key=item.key,
                    value=item.value,
                    value_type="string"
                )
                self.db.add(new_setting)
                updated_count += 1
        
        self.db.commit()
        return updated_count
    
    def delete_setting(self, key: str) -> bool:
        """Delete a setting"""
        setting = self.get_setting(key)
        if not setting:
            return False
        
        self.db.delete(setting)
        self.db.commit()
        return True
    
    def seed_default_settings(self) -> int:
        """
        Seed default settings if they don't exist.
        Returns number of settings created.
        """
        created_count = 0
        
        for default in DEFAULT_SETTINGS:
            existing = self.get_setting(default["key"])
            if not existing:
                setting = StoreSettings(
                    key=default["key"],
                    value=default["value"],
                    value_type=default["value_type"],
                    description=default["description"]
                )
                self.db.add(setting)
                created_count += 1
        
        if created_count > 0:
            self.db.commit()
        
        return created_count
    
    def get_order_limits(self) -> Dict[str, float]:
        """Get min and max order amounts"""
        return {
            "min_order_amount": self.get_setting_as_float("min_order_amount", 50.0),
            "max_order_amount": self.get_setting_as_float("max_order_amount", 2000.0)
        }


def get_settings_service(db: Session) -> SettingsService:
    """Factory function to create SettingsService instance"""
    return SettingsService(db)
