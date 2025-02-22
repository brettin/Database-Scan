# 1. Take the genes (G1s) found for disease (D1)
# 2. Look for other diseases (D2s) that are also connected to these same genes
# 3. Find what drugs (S2s) are being used to treat those other diseases

import sys, os, json, re, requests, pandas as pd, time
#from pathways_query import get_pathways_for_target
from opentargets_client_api import get_diseases
from opentargets_client_api import get_drug_info_for_diseases
from opentargets_client_api import get_drugs_for_diseases
from opentargets_client_api import get_disease_targets
from opentargets_client_api import get_diseases_for_targets
from opentargets_client_api import get_pathways_for_targets
from opentargets_client_api import get_targets_for_drugs
from opentargets_client_api import get_disease_name

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)


graphql_URL = "https://api.platform.opentargets.org/api/v4/graphql"



prompt_for_disease_id = """
{
  search(queryString: "DISEASE_NAME") {
    hits {
      id
      name
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

'''def get_disease_targets(disease_id, graphql_url, min_score=0.33):
    """Get targets associated with a disease ID above a minimum score."""
    prompt = prompt_for_disease_targets.replace("DISEASE_ID", disease_id)
    response = requests.post(graphql_url, json={'query': prompt})
    data = response.json()
    
    all_targets = []
    if 'data' in data and data['data']['disease']:
        for row in data['data']['disease']['associatedTargets']['rows']:
            target = row['target']
            score = row['score']
            all_targets.append({
                'id': target['id'],
                'symbol': target['approvedSymbol'],
                'score': score
            })
    
    return [target for target in all_targets if target["score"] >= min_score]
'''

'''def get_diseases_for_targets(targets, diseases, graphql_url, min_score=0.33):
    """Get diseases related to a list of targets, excluding the input diseases."""
    all_diseases = []
    disease_set = set()
    main_disease_ids = {disease['id'] for disease in diseases}
    
    for target in targets:
        prompt = prompt_get_diseases_for_target.replace("TARGET_ID", target["id"])
        response = requests.post(graphql_url, json={'query': prompt})
        data = response.json()
        
        if 'data' in data and data['data']['target']['associatedDiseases']['rows']:
            for row in data['data']['target']['associatedDiseases']['rows']:
                score = row["score"]
                if score < min_score:
                    continue
                disease = row['disease']
                disease_id = disease["id"]
                if disease_id in disease_set or disease_id in main_disease_ids:
                    continue
                disease_set.add(disease_id)
                all_diseases.append({
                    'id': disease_id,
                    'target_id': target["id"],
                    'name': disease['name'],
                    "score": score
                })
    
    return all_diseases, disease_set'''

# This is the original function that gets the drugs and their targets for a list of diseases. It is used below.
# It should not be used in favor of the function in opentargets_client_api.py
def get_drug_info_for_diseases(diseases, graphql_url):
    """Get drugs and their target information for a list of diseases."""
    all_drugs = []
    drug_set = set()
    
    for disease_info in diseases:
        prompt = prompt_for_disease_drugs.replace("DISEASE_ID", disease_info["id"])
        response = requests.post(graphql_url, json={'query': prompt})
        data = response.json()
        
        if 'data' in data and data['data']['disease']['knownDrugs']['rows']:
            disease_id = data['data']['disease']['id']
            disease_name = data['data']['disease']['name']
            for row in data['data']['disease']['knownDrugs']['rows']:
                drug = row['drug']
                drug_id = drug["id"]
                if drug_id in drug_set:
                    continue
                
                drug_set.add(drug_id)
                drug_info = {'id': drug_id, 'name': drug['name']}
                
                # Get target information for the drug
                prompt2 = prompt_get_targets_for_drug.replace("DRUG_ID", drug_id)
                response2 = requests.post(graphql_url, json={'query': prompt2})
                data2 = response2.json()
                row = data2['data']['drug']['linkedTargets']['rows'][0] # This is the first target for the drug
                print(f"row={row}")
                drug_info.update({
                    "disease_id": disease_id,
                    "disease_name": disease_name,
                    "target_id": row["id"],
                    "target_symbol": row["approvedSymbol"],
                    "target_name": row["approvedName"]
                })
                all_drugs.append(drug_info)
    
    return all_drugs, drug_set

def remove_diseases(diseases, disease_set, disease_ids_to_remove):
  """Remove specified diseases from the diseases list and set.
        
  Args:
    diseases: List of disease dictionaries containing 'id' key
    disease_set: Set of disease IDs
    disease_ids_to_remove: List of disease IDs to remove
            
  Returns:
    Tuple of (filtered diseases list, filtered disease set)
  """
  filtered_diseases = [d for d in diseases if d['id'] not in disease_ids_to_remove]
  filtered_set = disease_set - set(disease_ids_to_remove)
  return filtered_diseases, filtered_set
    
def load_from_csv(filename):
    """Load data from a CSV file and return as a list of dictionaries and a set."""
    df = pd.read_csv(filename)
    records = df.to_dict('records')
    # Create set from 'id' column if it exists, otherwise return empty set
    id_set = set(df['id'].values) if 'id' in df.columns else set()
    return records, id_set

def main(main_disease_name, min_score, load_from_files=True):
    '''
    What we want is:
    Step 1: MainDisease = MainDisease
    Step 2: MainDrugs = Drugs_for_MainDisease
    Step 3: MainTargets = Targets_for_MainDisease
    Step 4: Diseases_for_MainTargets = Diseases_for_MainTargets
    Step 5: OtherDiseases = Diseases_for_MainTargets - MainDisease
    Step 6: OtherDrugs = Drugs_for_OtherDiseases
    CandidateDrugs = OtherDrugs - MainDrugs
    '''
    
    if load_from_files:
        # Load data from saved CSV files
        diseases, disease_set = load_from_csv("diseases.csv")
        main_drugs, main_drug_set = load_from_csv("main_drugs.csv") # used below
        main_targets, main_target_set = load_from_csv("main_targets.csv")
        related_diseases, related_disease_set = load_from_csv("related_diseases.csv") # used below
        related_drugs_info, related_drug_set = load_from_csv("related_drugs_info.csv")
        candidate_drugs, candidate_drug_set = load_from_csv("candidate_drugs.csv")
        
        # Print loaded data
        print(f"\nLoaded from CSV files:")
        print(f"Found {len(disease_set)} diseases for {main_disease_name}")
        print(f"Found {len(main_drug_set)} drugs for main diseases")
        print(f"Found {len(main_target_set)} targets with minimum score {min_score}")
        print(f"Found {len(related_disease_set)} related diseases")
        print(f"Found {len(related_drug_set)} drugs for related diseases")
        print(f"Found {len(candidate_drug_set)} candidate drugs")     # candidate_drug_set is broken, don't use it.   
        print(f'Found {len(candidate_drugs)} drugs associated with other diseases but not directly with the main disease')
        #candidate_drugs_df = pd.DataFrame(candidate_drugs)
        #print(f"\n\nFound {len(candidate_drugs_df)} candidate drugs\n\n")

        # TODO:At this point we have the main drugs and the related drugs. These need to be manually
        # checked as part of a quality control process to ensure that the drugs are not already
        # associated with the main disease. This can come about if the main disease is a broader
        # disease that includes the related disease.

        # RUN DRUGS THROUGH UNO
        # We should get the improve_ids for the candidate drugs and the related drugs and then
        # train an uno model to predict the growth response


        # Step 1: Get targets for related diseases
        print(f"\n\nStep 1: Getting targets for related diseases\n\n")
        combined_related_disease_targets = []
        combined_related_disease_target_set = set()
        count = 0
        for disease in related_diseases:
            print(f"Getting targets for related disease id={disease['id']} name={disease['name']}")
            disease_targets, disease_target_set = get_disease_targets([disease], graphql_URL)
            
            # add the disease id to disease_targets
            for target in disease_targets:
                target['disease_id'] = disease['id']
                target['disease_name'] = disease['name']
            
            combined_related_disease_targets.extend(disease_targets)
            combined_related_disease_target_set.update(disease_target_set)
            count += 1
            if count < 1000:
                # sleep for 1 second
                time.sleep(1)
              
             
        combined_related_disease_targets_df = pd.DataFrame(combined_related_disease_targets)
        print(f"\n\nStep 1: Combined related disease targets:\n\n{combined_related_disease_targets_df}\n\n")

        # Step 2: Get targets for candidate drugs
        combined_candidate_drug_targets = []
        combined_candidate_drug_target_set = set()
        count = 0
        for drug in candidate_drugs:
            if '0' in drug:
                drug['id'] = drug['0']
                del drug['0']
            print(f"Step 2: Getting targets for candidate drug={drug}")
            drug_targets, drug_target_set = get_targets_for_drugs([drug], graphql_URL)
            
            # add the drug id to drug_targets
            for target in drug_targets:
                target['drug_id'] = drug['id']
            combined_candidate_drug_targets.extend(drug_targets)
            combined_candidate_drug_target_set.update(drug_target_set)
            count += 1
            if count < 1000:
                time.sleep(1)
        
        combined_candidate_drug_targets_df = pd.DataFrame(combined_candidate_drug_targets)
        print(f"\n\nCombined candidate drug targets:\n\n{combined_candidate_drug_targets_df}\n\n")
        

        # find the intersection of the combined_related_disease_target_set and the combined_candidate_drug_target_set
        intersection = combined_related_disease_target_set & combined_candidate_drug_target_set
        print(f"\n\nIntersection of related disease targets and candidate drug targets: {intersection}\n\n")
        
        # join combined_related_disease_targets_df with combined_candidate_drug_targets_df on the target_id
        combined_related_disease_targets_df = combined_related_disease_targets_df.merge(combined_candidate_drug_targets_df, on='id', how='inner')
        print(f"\n\n{combined_related_disease_targets_df}\n\n")
        
        # save the combined_related_disease_targets_df to a csv file
        combined_related_disease_targets_df.to_csv("combined_related_disease_targets_df.csv")
        
        
        return
        
    # Original querying logic continues here
    # Step 1: Get diseases for main disease
    diseases, disease_set = get_diseases(main_disease_name, graphql_URL)
    diseases_to_remove = ["EFO_0000313", "EFO_0002618", "EFO_1000218", "EFO_0000305", "EFO_0001663"] 
    '''
    name                        id
    carcinoma                   EFO_0000313
    pancreatic carcinoma        EFO_0002618
    Digestive System Carcinoma  EFO_1000218
    breast carcinoma            EFO_0000305
    prostate carcinoma          EFO_0001663
    '''

    diseases, disease_set = remove_diseases(diseases, disease_set, diseases_to_remove)

    print(f"\nStep 1: Found diseases: {diseases} for {main_disease_name}")
    diseases_df = pd.DataFrame(diseases)
    print(f"\n\n{diseases_df}\n\n")
    diseases_df.to_csv("diseases.csv")

   
    # Step 2: Get drugs for main disease
    main_drugs, main_drug_set = get_drugs_for_diseases(diseases, graphql_URL)

    df = pd.DataFrame(main_drugs)
    print(f"Step 2: Drugs for Main Diseases (main_drug_set)")
    print(f"\n\n{df}\n\n")
    df.to_csv("main_drugs.csv")

  
    # Step 3: Get targets for main disease
    main_targets, main_target_set = get_disease_targets(diseases, graphql_URL, min_score=min_score)
    print(f"Found {len(main_target_set)} targets with minimum score {min_score}")
    #print(f"main_targets={main_targets}")

    df = pd.DataFrame(main_targets)
    print(f"Step 3: Targets for Main Diseases (main_target_set)")
    print(f"\n\n{df}\n\n")
    df.to_csv("main_targets.csv")


    # Step 4: Get related diseases for all targets
    related_diseases, related_disease_set = get_diseases_for_targets(main_targets, diseases, graphql_URL)
    print(f"Step 4: Found {len(related_disease_set)} related diseases")
    df = pd.DataFrame(related_diseases)
    print(f"Step 4: Related Diseases (related_disease_set)")
    print(f"\n\n{df}\n\n")
    df.to_csv("related_diseases.csv")


    # Step 5: Get drugs for all related diseases
    related_drugs_info, related_drug_set = get_drug_info_for_diseases(related_diseases, graphql_URL)
    print(f"Step 5: Found {len(related_drug_set)} drugs for related diseases")
    related_drug_info_df = pd.DataFrame(related_drugs_info)
    related_drug_info_df.to_csv("related_drugs_info.csv")
    print(f"\n\n{related_drug_info_df}\n\n")


    # Step 6:  Find candidate drugs (drugs not associated with main disease)
    candidate_drugs = related_drug_set - main_drug_set
    print(f'Step 6: Found {len(candidate_drugs)} drugs associated with other diseases but not directly with the main disease')
    candidate_drugs_df = pd.DataFrame(candidate_drugs, columns=['id'])
    candidate_drugs_df.to_csv("candidate_drugs.csv")
    print(f"\nStep 6: Found {len(candidate_drugs)} related_drug_set - main_drug_set")
    print(f"\n\n{candidate_drugs_df}\n\n")

        

if __name__ == "__main__":
    main_disease_name = "ovarian carcinoma" # MONDO:0005140
    min_score = 0.33
    main(main_disease_name, min_score, load_from_files=False)  # Set to True to load from files

