import requests

# Define the GraphQL query to retrieve targets for a specific drug
graphql_query = {
    "query": """
    {
      drug(chemblId: \"CHEMBL690\") {
        id
        name
        mechanismsOfAction {
          rows {
            targets {
              id
              approvedSymbol
            }
            mechanismOfAction
          }
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
    drug_info = data.get("data", {}).get("drug", {})
    if drug_info:
        print(f"Drug ID: {drug_info.get('id')}, Name: {drug_info.get('name')}")
        print("Mechanisms of Action:")
        for row in drug_info.get("mechanismsOfAction", {}).get("rows", []):
            targets = row.get("targets", [])
            for target in targets:
                print(f"- Target ID: {target.get('id')}, Symbol: {target.get('approvedSymbol')}, Mechanism: {row.get('mechanismOfAction')}")
    else:
        print("No data found for the specified drug.")
else:
    print(f"Error: {response.status_code}, {response.text}")
