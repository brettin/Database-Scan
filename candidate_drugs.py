import sys, os, json, re
import requests

# API endpoint for Open Targets Platform
graphql_URL = "https://api.platform.opentargets.org/api/v4/graphql"

# Disease to analyze
disease_name = "Nasal cavity and paranasal sinus carcinoma" # MONDO_0056819

# GraphQL query to convert disease name to Open Targets disease ID
prompt_for_disease_id = """
{
  search(queryString: "DISEASE_NAME") {
    hits {
      id
    }
  }
}
""".strip()

prompt_for_disease_drugs = """
query diseaseAssociatedDrugs {
  disease(efoId: "DISEASE_ID") {
    id
    name
    knownDrugs {
      rows {
        phase
        drug {
          id
          name
        }
      }
    }
  }
}
"""

prompt_for_disease_targets = """
{
  disease(efoId: "DISEASE_ID") {
    associatedTargets {
      rows {
        target {
          id
          approvedSymbol
        }
        score
      }
    }
  }
}
""".strip()

prompt_get_drugs_for_target = """
{
  target(ensemblId: "TARGET_ID") {
    knownDrugs {
      rows {
        drug {
          id
          name
          synonyms
          drugType
          isApproved
          maximumClinicalTrialPhase
        }
      }
    }
  }
}
""".strip()

def main():
    """
    Identifies potential drug candidates for a disease through target-based drug repurposing.
    Uses the Open Targets Platform API to:
    1. Convert disease name to disease ID
    2. Find disease-associated targets
    3. Find drugs that interact with those targets
    4. Compare with known disease-associated drugs to identify new candidates
    """
    
    # Step 1: Find disease ID for named disease
    print("\nStep 1: getting ID for disease:", disease_name)
    prompt = prompt_for_disease_id.replace("DISEASE_NAME",disease_name)
    response = requests.post(graphql_URL, json={'query': prompt} )
    jdata = response.json()
    hits = jdata["data"]["search"]["hits"]
    disease_id = hits[0]['id'] # FIRST disease ID
    print("ID=",disease_id)

    # Step 2: Get disease-associated targets with confidence score >= 0.33
    print("\nStep 2: Getting primary targets for disease_id:", disease_id)
    prompt = prompt_for_disease_targets.replace("DISEASE_ID",disease_id)
    response = requests.post(graphql_URL, json={'query': prompt})
    data = response.json()
    all_targets = []
    if 'data' in data and data['data']['disease']:
        for row in data['data']['disease']['associatedTargets']['rows']:
            target = row['target']
            score = row['score']
            ## print(f"Target: {target['approvedSymbol']}, Score: {score}")
            all_targets.append(
                { 'id': target['id'], 'symbol': target['approvedSymbol'], 'score': score }
            )

    min_score = 0.33
    targets_to_use = [ target for target in all_targets if target["score"] >= min_score ]
    print(f"Disease-Associated Targets With Min Score {min_score}:")
    for target in targets_to_use:
        print(f"    {target['symbol']:8s} score: {target['score']:0.2f}  ID: {target['id']}")

    # Step 3: Find all drugs that interact with the disease-associated targets
    print("\nStep 3: Getting drugs for targets...")
    all_drugs_for_all_targets = []
    for target in targets_to_use:
        target_id = target["id"]
        prompt = prompt_get_drugs_for_target.replace("TARGET_ID",target_id)
        response = requests.post(graphql_URL, json={'query': prompt})
        data = response.json()

        print("  Info about each drug for target",target_id)
        all_drugs_for_target = []
        if 'data' in data and data['data']['target']['knownDrugs']['rows']:
            for row in data['data']['target']['knownDrugs']['rows']:
                drug = row['drug']
                drug_info = { 'id': drug['id'], 'name': drug['name'], 'isApproved': drug['isApproved'],
                              'maximumClinicalTrialPhase': drug['maximumClinicalTrialPhase']
                            }
                all_drugs_for_target.append(drug_info)
                all_drugs_for_all_targets.append(drug_info)
                print("    ",drug_info)

    # Step 4: Get drugs directly associated with the disease
    print("\nStep 4: Getting drugs for disease",disease_id)
    prompt = prompt_for_disease_drugs.replace("DISEASE_ID",disease_id)
    response = requests.post(graphql_URL, json={'query': prompt})
    data = response.json()

    print("  Info about each drug for disease",disease_id)
    all_drugs_for_disease = []
    if 'data' in data and data['data']['disease']['knownDrugs']['rows']:
        for row in data['data']['disease']['knownDrugs']['rows']:
            drug = row['drug']
            drug_info = { 'id': drug['id'], 'name': drug['name'] }
            all_drugs_for_disease.append(drug_info)
            print("    ",drug_info)

    # Create sets for comparison
    D_D = set( [ drug["id"] for drug in all_drugs_for_disease ] )      # Disease-associated drugs
    D_T_D = set( [ drug["id"] for drug in all_drugs_for_all_targets ]) # Target-associated drugs

    # Find drugs that interact with disease targets but aren't yet associated with the disease
    print("\nDisease name:",disease_name)
    print("Disease id:",disease_id)
    print("Drugs associated with targets but not directly with the disease:")
    candidate_drugs = D_T_D - D_D  # Set difference to find new candidates
    for drug_id in candidate_drugs:
        for tempdrug in all_drugs_for_all_targets:
            if tempdrug["id"] == drug_id:
                drug_name = tempdrug["name"]
                break
        print(f"   {drug_id:14s} {drug_name}")

if __name__ == "__main__":
    main()
