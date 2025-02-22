import requests
import json

def query_opentargets(prompt):
    """
    Send a GraphQL query to the Open Targets Platform API and return the JSON response
    
    Args:
        prompt (str): GraphQL query string
    
    Returns:
        dict: JSON response from the API
    """
    graphql_URL = "https://api.platform.opentargets.org/api/v4/graphql"
    response = requests.post(graphql_URL, json={'query': prompt})
    return response.json()

def pretty_print_json(data):
    """
    Print JSON data in a readable format
    
    Args:
        data (dict): JSON data to print
    """
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    # Example usage
    example_query = """
{
  target(ensemblId: "ENSG00000141510") {
    id
    approvedSymbol
    pathways {
      pathway {
        id
        name
      }
    }
  }
}
""".strip()

    
    result = query_opentargets(example_query)
    pretty_print_json(result) 