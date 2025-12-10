"""
A module for querying the restcountries.com REST API.

This module provides a simple interface to fetch country information
from the restcountries.com API with support for field filtering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import httpx


@dataclass
class Country:
    """Represents a country with its information."""
    
    name: dict[str, Any]
    cca2: str | None = None  # 2-letter country code
    cca3: str | None = None  # 3-letter country code
    data: dict[str, Any] | None = None  # Full country data
    
    @property
    def common_name(self) -> str:
        """Get the common name of the country."""
        return self.name.get("common", "")
    
    @property
    def official_name(self) -> str:
        """Get the official name of the country."""
        return self.name.get("official", "")
    
    @property
    def code(self) -> str:
        """Get the country code (CCA2 if available, otherwise CCA3)."""
        return self.cca2 or self.cca3 or ""
    
    def __str__(self) -> str:
        return f"{self.common_name} ({self.code})"
    
    def __repr__(self) -> str:
        return f"Country(name={self.common_name!r}, code={self.code!r})"


class RestCountriesClient:
    """Client for interacting with the restcountries.com API."""
    
    def __init__(self, timeout: float = 10.0, base_url: str | None = None):
        """
        Initialize the REST Countries client.
        
        Args:
            timeout: Timeout for HTTP requests in seconds (default: 10.0)
            base_url: Base URL for the API (default: https://restcountries.com/v3.1)
        """
        self.timeout = timeout
        self._base_url = base_url or "https://restcountries.com/v3.1"
        self._client: httpx.Client | None = None
    
    @property
    def base_url(self) -> str:
        """Get the base URL for the API."""
        return self._base_url
    
    @property
    def client(self) -> httpx.Client:
        """Get or create an HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client
    
    def __enter__(self) -> RestCountriesClient:
        """Context manager entry."""
        self._client = httpx.Client(timeout=self.timeout)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if self._client:
            self._client.close()
            self._client = None
    
    def get_all_countries(self, fields: list[str] | None = None) -> list[Country]:
        """
        Fetch all countries from the API.
        
        Args:
            fields: List of fields to retrieve. If None, all fields are returned.
                   Common fields include: name, cca2, cca3, capital, region, 
                   population, area, languages, flags, etc.
        
        Returns:
            List of Country objects
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        # Build the URL with field filtering if specified
        url = f"{self.base_url}/all"
        if fields:
            # Always include name and country codes for the Country object
            required_fields = {"name", "cca2", "cca3"}
            all_fields = required_fields | set(fields)
            fields_param = ",".join(all_fields)
            url = f"{url}?fields={fields_param}"
        
        response = self.client.get(url)
        response.raise_for_status()
        
        countries_data = response.json()
        
        return [
            Country(
                name=country.get("name", {}),
                cca2=country.get("cca2"),
                cca3=country.get("cca3"),
                data=country
            )
            for country in countries_data
        ]
    
    def get_country_by_name(
        self, 
        name: str, 
        fields: list[str] | None = None,
        full_text: bool = False
    ) -> list[Country]:
        """
        Search for countries by name.
        
        Args:
            name: Country name to search for
            fields: List of fields to retrieve
            full_text: If True, search for exact match only
            
        Returns:
            List of matching Country objects
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        url = f"{self.base_url}/name/{name}"
        params = {}
        
        if full_text:
            params["fullText"] = "true"
        
        if fields:
            required_fields = {"name", "cca2", "cca3"}
            all_fields = required_fields | set(fields)
            params["fields"] = ",".join(all_fields)
        
        response = self.client.get(url, params=params)
        response.raise_for_status()
        
        countries_data = response.json()
        
        return [
            Country(
                name=country.get("name", {}),
                cca2=country.get("cca2"),
                cca3=country.get("cca3"),
                data=country
            )
            for country in countries_data
        ]
    
    def get_country_by_code(
        self, 
        code: str, 
        fields: list[str] | None = None
    ) -> Country:
        """
        Get a country by its ISO code (alpha2, alpha3, or numeric).
        
        Args:
            code: Country code (e.g., 'US', 'USA', '840')
            fields: List of fields to retrieve
            
        Returns:
            Country object
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        url = f"{self.base_url}/alpha/{code}"
        
        if fields:
            required_fields = {"name", "cca2", "cca3"}
            all_fields = required_fields | set(fields)
            fields_param = ",".join(all_fields)
            url = f"{url}?fields={fields_param}"
        
        response = self.client.get(url)
        response.raise_for_status()
        
        country_data = response.json()
        
        return Country(
            name=country_data.get("name", {}),
            cca2=country_data.get("cca2"),
            cca3=country_data.get("cca3"),
            data=country_data
        )
    
    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


# Convenience function for quick queries
def get_all_countries(fields: list[str] | None = None) -> list[Country]:
    """
    Convenience function to get all countries without managing a client.
    
    Args:
        fields: List of fields to retrieve
        
    Returns:
        List of Country objects
    """
    with RestCountriesClient() as client:
        return client.get_all_countries(fields=fields)


def get_country_by_code(code: str, fields: list[str] | None = None) -> Country:
    """
    Convenience function to get a country by code without managing a client.
    
    Args:
        code: Country code (e.g., 'US', 'USA')
        fields: List of fields to retrieve
        
    Returns:
        Country object
    """
    with RestCountriesClient() as client:
        return client.get_country_by_code(code=code, fields=fields)
