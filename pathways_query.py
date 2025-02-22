import requests, json

def get_pathways_for_target(target_id):
    graphql_URL = "https://api.platform.opentargets.org/api/v4/graphql"
    
    # Query template
    query = """
{
  target(ensemblId: "TARGET_ID") {
    id
    approvedSymbol
    pathways {
      pathway
      pathwayId
    }
  }
}
""".strip()
    
    # Replace placeholder with actual target ID
    query = query.replace("TARGET_ID", target_id)
    
    # Make the request
    response = requests.post(graphql_URL, json={'query': query})
    data = response.json()

    print(f"data={json.dumps(data, indent=2)}")

    all_pathways = []
    pathway_set = set()

    for pathway in data['data']['target']['pathways']:
        pathway_id = pathway['pathwayId']
        if pathway_id in pathway_set:
            continue
        pathway_set.add(pathway_id)
        all_pathways.append(pathway)    

    return all_pathways, pathway_set

if __name__ == "__main__":
    # Example target ID (TP53 gene)
    target_id = "ENSG00000141510"
    pathways, pathway_set = get_pathways_for_target(target_id) 
    print(f"pathways={pathways}")
    print(f"pathway_set={pathway_set}")


