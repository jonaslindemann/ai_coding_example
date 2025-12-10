"""
Example usage of the countries module.
"""

from countries import RestCountriesClient


def main():
    with RestCountriesClient() as client:
        print("=" * 60)
        print("Example 1: Get all countries with specific fields")
        print("=" * 60)
        
        # Get all countries with only specific fields
        countries = client.get_all_countries(fields=["capital", "region", "population"])
        
        print(f"\nFound {len(countries)} countries\n")
        
        # Display first 5 countries
        for country in countries[:5]:
            print(f"Country: {country}")
            print(f"  Code: {country.code}")
            print(f"  Capital: {country.data.get('capital', ['N/A'])[0]}")
            print(f"  Region: {country.data.get('region', 'N/A')}")
            print(f"  Population: {country.data.get('population', 'N/A'):,}")
            print()
        
        print("=" * 60)
        print("Example 2: Get specific country by code")
        print("=" * 60)
        
        # Get Sweden by code
        sweden = client.get_country_by_code("SE", fields=["capital", "population", "area", "languages"])
        
        print(f"\n{sweden}")
        print(f"  Official name: {sweden.official_name}")
        print(f"  Capital: {sweden.data.get('capital', ['N/A'])[0]}")
        print(f"  Population: {sweden.data.get('population', 0):,}")
        print(f"  Area: {sweden.data.get('area', 0):,} km²")
        print(f"  Languages: {', '.join(sweden.data.get('languages', {}).values())}")
        print()
        
        print("=" * 60)
        print("Example 3: Search countries by name")
        print("=" * 60)
        
        # Search by name
        nordic = client.get_country_by_name("norway", fields=["capital", "region"])
        
        print(f"\nSearch results for 'norway': {len(nordic)} country found")
        for country in nordic:
            print(f"  {country} - Capital: {country.data.get('capital', ['N/A'])[0]}")
        
        # Get by code
        usa = client.get_country_by_code("USA", fields=["capital", "population"])
        print(f"\n{usa}")
        print(f"  Population: {usa.data.get('population', 0):,}")


if __name__ == "__main__":
    main()
