"""
Tax calculation service with GRT API integration for New Mexico
"""
import httpx
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from decimal import Decimal, ROUND_HALF_UP

from models import StoreSettings, TaxRateCache
from schemas.settings import TaxAddress, TaxCalculationResult, StoreAddress

logger = logging.getLogger("landa-api.tax")

# GRT API Base URL
GRT_API_URL = "https://grt.edacnm.org/api/by_address"

# Cache TTL in days
TAX_CACHE_TTL_DAYS = 7


class TaxService:
    """Service for calculating sales tax"""
    
    def __init__(self, db: Session):
        self.db = db
        self._settings_cache: dict = {}
    
    def _get_setting(self, key: str, default: str = "") -> str:
        """Get a setting value from database"""
        if key in self._settings_cache:
            return self._settings_cache[key]
        
        setting = self.db.query(StoreSettings).filter(
            StoreSettings.key == key
        ).first()
        
        value = setting.value if setting else default
        self._settings_cache[key] = value
        return value
    
    def _get_setting_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean setting"""
        value = self._get_setting(key, str(default).lower())
        return value.lower() in ("true", "1", "yes")
    
    def _get_setting_float(self, key: str, default: float = 0.0) -> float:
        """Get a float setting"""
        try:
            return float(self._get_setting(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def _get_cached_rate(self, street_name: str, city: str, state: str, zipcode: str) -> Optional[float]:
        """Get cached tax rate if available and not expired"""
        # Normalize for comparison
        street_upper = (street_name or "").upper().strip()
        city_upper = city.upper().strip()
        state_upper = state.upper().strip()
        
        cache_entry = self.db.query(TaxRateCache).filter(
            TaxRateCache.street_name == street_upper,
            TaxRateCache.city == city_upper,
            TaxRateCache.state == state_upper,
            TaxRateCache.zipcode == zipcode,
            TaxRateCache.expires_at > datetime.utcnow()
        ).first()
        
        if cache_entry:
            logger.info(f"Tax cache HIT for {street_name}, {city}, {state} {zipcode}: {cache_entry.tax_rate}%")
            return cache_entry.tax_rate
        
        return None
    
    def _save_to_cache(self, street_name: str, city: str, state: str, zipcode: str, tax_rate: float, 
                       county: Optional[str] = None, location_code: Optional[str] = None):
        """Save tax rate to cache"""
        # Normalize for storage
        street_upper = (street_name or "").upper().strip()
        city_upper = city.upper().strip()
        state_upper = state.upper().strip()
        
        # Delete any existing entry for this address
        self.db.query(TaxRateCache).filter(
            TaxRateCache.street_name == street_upper,
            TaxRateCache.city == city_upper,
            TaxRateCache.state == state_upper,
            TaxRateCache.zipcode == zipcode
        ).delete()
        
        # Create new cache entry
        cache_entry = TaxRateCache(
            street_name=street_upper,
            city=city_upper,
            state=state_upper,
            zipcode=zipcode,
            tax_rate=tax_rate,
            county=county,
            location_code=location_code,
            expires_at=datetime.utcnow() + timedelta(days=TAX_CACHE_TTL_DAYS)
        )
        self.db.add(cache_entry)
        self.db.commit()
        logger.info(f"Tax cache SAVED for {street_name}, {city}, {state} {zipcode}: {tax_rate}% (expires in {TAX_CACHE_TTL_DAYS} days)")
    
    def get_store_address(self) -> StoreAddress:
        """Get store address from settings"""
        return StoreAddress(
            street_number=self._get_setting("store_street_number", ""),
            street_name=self._get_setting("store_street_name", ""),
            street_suffix=self._get_setting("store_street_suffix", ""),
            street_direction=self._get_setting("store_street_direction", ""),
            city=self._get_setting("store_city", ""),
            state=self._get_setting("store_state", ""),
            zipcode=self._get_setting("store_zipcode", "")
        )
    
    def is_tax_enabled(self) -> bool:
        """Check if tax calculation is enabled"""
        return self._get_setting_bool("tax_enabled", True)
    
    def get_tax_method(self) -> str:
        """Get tax calculation method"""
        return self._get_setting("tax_calculation_method", "grt_api")
    
    def get_fixed_tax_rate(self) -> float:
        """Get fixed tax rate percentage"""
        return self._get_setting_float("tax_fixed_rate", 0.0)
    
    def should_tax_shipping(self) -> bool:
        """Check if shipping should be taxed"""
        return self._get_setting_bool("tax_apply_to_shipping", False)
    
    async def _call_grt_api(self, address: TaxAddress) -> Tuple[Optional[float], Optional[str]]:
        """
        Call the New Mexico GRT API to get tax rate.
        Returns (tax_rate, error_message)
        """
        params = {
            "street_number": address.street_number or "",
            "street_name": address.street_name or "",
            "city": address.city or "",
            "zipcode": address.zipcode or ""
        }
        
        # Add optional fields if present
        if address.street_suffix:
            params["street_suffix"] = address.street_suffix
        if address.street_direction:
            params["street_post_directional"] = address.street_direction
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(GRT_API_URL, params=params)
                response.raise_for_status()
                
                data = response.json()
                results = data.get("results", [])
                
                if results and results[0].get("success"):
                    tax_rate = results[0].get("tax_rate")
                    if tax_rate is not None:
                        return float(tax_rate), None
                
                return None, "Address not found in GRT database"
                
        except httpx.TimeoutException:
            return None, "GRT API timeout"
        except httpx.HTTPStatusError as e:
            return None, f"GRT API error: {e.response.status_code}"
        except Exception as e:
            return None, f"GRT API error: {str(e)}"
    
    def _call_grt_api_sync(self, address: TaxAddress) -> Tuple[Optional[float], Optional[str]]:
        """
        Synchronous version of GRT API call with caching.
        Returns (tax_rate, error_message)
        """
        street_name = address.street_name or ""
        city = address.city or ""
        state = address.state or ""
        zipcode = address.zipcode or ""
        
        # Check cache first (by full address including street)
        cached_rate = self._get_cached_rate(street_name, city, state, zipcode)
        if cached_rate is not None:
            return cached_rate, None
        
        # Cache miss - call API
        params = {
            "street_number": address.street_number or "",
            "street_name": street_name,
            "city": city,
            "zipcode": zipcode
        }
        
        # Add optional fields if present
        if address.street_suffix:
            params["street_suffix"] = address.street_suffix
        if address.street_direction:
            params["street_post_directional"] = address.street_direction
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(GRT_API_URL, params=params)
                response.raise_for_status()
                
                data = response.json()
                results = data.get("results", [])
                
                if results and results[0].get("success"):
                    tax_rate = results[0].get("tax_rate")
                    if tax_rate is not None:
                        # Save to cache (by full address including street)
                        county = results[0].get("county")
                        location_code = results[0].get("location_code")
                        self._save_to_cache(street_name, city, state, zipcode, float(tax_rate), county, location_code)
                        return float(tax_rate), None
                
                return None, "Address not found in GRT database"
                
        except httpx.TimeoutException:
            return None, "GRT API timeout"
        except httpx.HTTPStatusError as e:
            return None, f"GRT API error: {e.response.status_code}"
        except Exception as e:
            return None, f"GRT API error: {str(e)}"
    
    def calculate_tax(
        self,
        subtotal: float,
        shipping_fee: float,
        address: Optional[TaxAddress] = None,
        is_pickup: bool = False
    ) -> TaxCalculationResult:
        """
        Calculate tax for an order.
        
        Args:
            subtotal: Order subtotal (products only)
            shipping_fee: Shipping cost
            address: Customer shipping address (for delivery orders)
            is_pickup: True if order is for store pickup
        
        Returns:
            TaxCalculationResult with tax amount, rate, and source
        """
        # Check if tax is enabled
        if not self.is_tax_enabled():
            return TaxCalculationResult(
                tax_amount=0.0,
                tax_rate=0.0,
                tax_source="none",
                success=True
            )
        
        # Determine which address to use
        if is_pickup:
            # Use store address for pickup orders
            store_addr = self.get_store_address()
            tax_address = TaxAddress(
                street_number=store_addr.street_number,
                street_name=store_addr.street_name,
                street_suffix=store_addr.street_suffix,
                street_direction=store_addr.street_direction,
                city=store_addr.city,
                state=store_addr.state,
                zipcode=store_addr.zipcode
            )
            tax_source_prefix = "store_rate"
        else:
            tax_address = address
            tax_source_prefix = ""
        
        # If no address, return zero tax
        if not tax_address or not tax_address.is_complete():
            return TaxCalculationResult(
                tax_amount=0.0,
                tax_rate=0.0,
                tax_source="none",
                success=True,
                error_message="No address provided for tax calculation"
            )
        
        # Get tax calculation method
        method = self.get_tax_method()
        
        # Calculate taxable amount
        taxable_amount = subtotal
        if self.should_tax_shipping():
            taxable_amount += shipping_fee
        
        # Method: none
        if method == "none":
            return TaxCalculationResult(
                tax_amount=0.0,
                tax_rate=0.0,
                tax_source="none",
                success=True
            )
        
        # Method: fixed_rate
        if method == "fixed_rate":
            rate = self.get_fixed_tax_rate()
            tax_amount = self._calculate_tax_amount(taxable_amount, rate)
            return TaxCalculationResult(
                tax_amount=tax_amount,
                tax_rate=rate,
                tax_source="fixed_rate",
                success=True
            )
        
        # Method: grt_api (default)
        if method == "grt_api":
            # Only works for New Mexico addresses
            if not tax_address.is_new_mexico():
                # Outside NM - no tax (for now)
                return TaxCalculationResult(
                    tax_amount=0.0,
                    tax_rate=0.0,
                    tax_source="none",
                    success=True,
                    error_message="Tax calculation only available for New Mexico"
                )
            
            # Call GRT API
            rate, error = self._call_grt_api_sync(tax_address)
            
            if rate is not None:
                tax_amount = self._calculate_tax_amount(taxable_amount, rate)
                source = tax_source_prefix if is_pickup else "grt_api"
                return TaxCalculationResult(
                    tax_amount=tax_amount,
                    tax_rate=rate,
                    tax_source=source or "grt_api",
                    success=True
                )
            else:
                # API failed - fallback to fixed rate if configured
                fallback_rate = self.get_fixed_tax_rate()
                if fallback_rate > 0:
                    tax_amount = self._calculate_tax_amount(taxable_amount, fallback_rate)
                    return TaxCalculationResult(
                        tax_amount=tax_amount,
                        tax_rate=fallback_rate,
                        tax_source="fixed_rate",
                        success=True,
                        error_message=f"GRT API failed, using fallback rate: {error}"
                    )
                else:
                    return TaxCalculationResult(
                        tax_amount=0.0,
                        tax_rate=0.0,
                        tax_source="none",
                        success=False,
                        error_message=error
                    )
        
        # Unknown method
        return TaxCalculationResult(
            tax_amount=0.0,
            tax_rate=0.0,
            tax_source="none",
            success=False,
            error_message=f"Unknown tax calculation method: {method}"
        )
    
    def _calculate_tax_amount(self, taxable_amount: float, rate: float) -> float:
        """Calculate tax amount with proper rounding"""
        # Rate is a percentage (e.g., 7.875)
        tax = Decimal(str(taxable_amount)) * Decimal(str(rate)) / Decimal("100")
        # Round to 2 decimal places (cents)
        tax = tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(tax)


def get_tax_service(db: Session) -> TaxService:
    """Factory function to create TaxService instance"""
    return TaxService(db)
