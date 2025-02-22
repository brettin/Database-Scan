
# 1. Take the genes (G1s) found for disease (D1)
# 2. Look for other diseases (D2s) that are also connected to these same genes
# 3. Find what drugs (S2s) are being used to treat those other diseases

import sys, os, json, re, requests

graphql_URL = "https://api.platform.opentargets.org/api/v4/graphql"

main_disease_name = "Nasal cavity and paranasal sinus carcinoma" # MONDO_0056819
main_disease_id = "ovarian carcinoma" # MONDO:0005140
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

# ENSG00000080815 example target_id
prompt_get_diseases_for_target = """
query GetAssociatedDiseases {
  target(ensemblId: "TARGET_ID" ) {
    associatedDiseases {
      rows {
        disease {
          id
          name
        }
        score
      }
    }
  }
}
""".strip()

prompt_get_targets_for_drug = """
query DrugTargets {
  drug(chemblId: "DRUG_ID" ) {
    id
    name
    linkedTargets {
      count
      rows {
        id
        approvedSymbol
        approvedName
      }
    }
  }
}
""".strip()

def main():
    # Step 1: Find disease ID for named disease
    print("\nStep 1: getting ID for disease:", main_disease_name)
    prompt = prompt_for_disease_id.replace("DISEASE_NAME",main_disease_name)
    response = requests.post(graphql_URL, json={'query': prompt} )
    jdata = response.json()
    hits = jdata["data"]["search"]["hits"]
    main_disease_id = hits[0]['id'] # FIRST disease ID
    print("ID=",main_disease_id)

    print("\nStep 2: Getting drugs for main_disease",main_disease_id)
    prompt = prompt_for_disease_drugs.replace("DISEASE_ID",main_disease_id)
    response = requests.post(graphql_URL, json={'query': prompt})
    data = response.json()

    print("  Info about each drug for main_disease",main_disease_id)
    all_drugs_for_main_disease = []
    main_drug_set = set()
    if 'data' in data and data['data']['disease']['knownDrugs']['rows']:
        for row in data['data']['disease']['knownDrugs']['rows']:
            drug = row['drug']
            drug_id = drug["id"]
            if drug_id in main_drug_set:
                continue
            main_drug_set.add(drug_id)
            drug_info = { 'id': drug_id, 'name': drug['name'] }
            all_drugs_for_main_disease.append(drug_info)
            print("    ",drug_info)
    print("NUM DRUGS RELATED TO MAIN DISEASE:", len(main_drug_set))

    print("\nStep 3: Getting primary targets for main disease_id:", main_disease_id)
    prompt = prompt_for_disease_targets.replace("DISEASE_ID",main_disease_id)
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
    print("NUM TARGETS TO USE:", len(targets_to_use))

    print(f"Disease-Associated Targets With Min Score {min_score}:")
    for target in targets_to_use:
        print(f"    {target['symbol']:8s} score: {target['score']:0.2f}  ID: {target['id']}")

    # Step 3: Find diseases related to all targets

    print("\nStep 4: Getting diseases related to targets...")
    all_diseases_for_all_targets = []
    disease_set = set()
    for target in targets_to_use:
        target_id = target["id"]
        prompt = prompt_get_diseases_for_target.replace("TARGET_ID",target_id)
        response = requests.post(graphql_URL, json={'query': prompt})
        data = response.json()

        print("  Info about each disease related to target",target_id)
        min_score = 0.33
        all_diseases_for_target = []
        if 'data' in data and data['data']['target']['associatedDiseases']['rows']:
            for row in data['data']['target']['associatedDiseases']['rows']:
                score = row["score"]
                if score < min_score:
                    continue
                disease = row['disease']
                disease_id = disease["id"]
                if disease_id in disease_set  or  disease_id == main_disease_id:
                    continue
                disease_set.add(disease_id)
                disease_info = { 'id': disease_id, 'name': disease['name'], "score": score }
                all_diseases_for_target.append(disease_info)
                all_diseases_for_all_targets.append(disease_info)
                print("    ",disease_info)

    print("NUM DISEASES RELATED TO USABLE TARGETS",len(disease_set))

    print("\nStep 5: Getting drugs for all disease")
    all_drugs_for_all_diseases = []
    drug_set = set()
    for disease_info in all_diseases_for_all_targets:
        prompt = prompt_for_disease_drugs.replace("DISEASE_ID",disease_info["id"])
        response = requests.post(graphql_URL, json={'query': prompt})
        data = response.json()

        print("  Info about each drug for disease",disease_info["id"])
        all_drugs_for_disease = []
        if 'data' in data and data['data']['disease']['knownDrugs']['rows']:
            for row in data['data']['disease']['knownDrugs']['rows']:
                drug = row['drug']
                drug_id = drug["id"]
                if drug_id in drug_set:
                    continue
                drug_set.add(drug_id)
                drug_info = { 'id': drug_id, 'name': drug['name'] }
                print("    ",drug_info)
                ### now get main target for that drug
                prompt2 = prompt_get_targets_for_drug.replace("DRUG_ID",drug_id)
                response2 = requests.post(graphql_URL, json={'query': prompt2})
                data2 = response2.json()
                row = data2['data']['drug']['linkedTargets']['rows'][0]
                drug_info["target_id"] = row["id"]
                drug_info["target_symbol"] = row["approvedSymbol"]
                drug_info["target_name"] = row["approvedName"]
                # do these two after all drug_info established
                all_drugs_for_disease.append(drug_info)
                all_drugs_for_all_diseases.append(drug_info)

    print("NUM DRUGS RELATED TO ALL RELATED DISEASES",len(drug_set))

    print("\nDisease name:",main_disease_name)
    print("Disease id:",main_disease_id)
    print("Drugs associated with other diseases but not directly with the main disease:")
    candidate_drugs = drug_set - main_drug_set
    print("NUM DRUG CANDIDATES",len(candidate_drugs))
    for drug_id in candidate_drugs:
        for tempdrug in all_drugs_for_all_diseases:
            if tempdrug["id"] == drug_id:
                drug_name = tempdrug["name"]
                target_symbol = tempdrug["target_symbol"]
                target_name = tempdrug["target_name"]
                break
        print(f"   {drug_id:14s} {drug_name}; target_symbol: {target_symbol}   target_name: {target_name}")

if __name__ == "__main__":
    main()
