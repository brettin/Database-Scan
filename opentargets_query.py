import requests

# Define the corrected GraphQL query
graphql_query = {
    "query": """
    {
      search(queryString: \"ovarian cancer\", entityNames: [\"disease\"]) {
        hits {
          id
          name
        }
      }
    }
    """
}

# Open Targets GraphQL API endpoint
url = "https://api.platform.opentargets.org/api/v4/graphql"

# Send the request
response = requests.post(url, json=graphql_query)

# Check the response status
if response.status_code == 200:
    data = response.json()
    diseases = data.get("data", {}).get("search", {}).get("hits", [])
    for disease in diseases:
        print(f"ID: {disease.get('id')}, Name: {disease.get('name')}")
else:
    print(f"Error: {response.status_code}, {response.text}")
