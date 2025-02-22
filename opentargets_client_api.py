import requests, json, os, sys, pandas as pd



graphql_url = "https://api.platform.opentargets.org/api/v4/graphql"

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

prompt_for_disease_name = """
query diseaseName {
  disease(efoId: "DISEASE_ID") {
    name
  }
}
""".strip()

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
""".strip()

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

prompt_get_pathways_for_target = """
query TargetPathways {
  target(ensemblId: "TARGET_ID") {
  id
    pathways {
      pathway
      pathwayId
      topLevelTerm
    }
  }
}
""".strip()

def get_diseases(disease_name, graphql_url):
    """Get the disease ID from Open Targets Platform given a disease name."""
    prompt = prompt_for_disease_id.replace("DISEASE_NAME", disease_name)
    response = requests.post(graphql_url, json={'query': prompt})
    jdata = response.json()
    # print(f"jdata={json.dumps(jdata, indent=2)}")
    hits = []
    hits_set = set()
    for hit in jdata["data"]["search"]["hits"]:
        if hit["id"] not in hits_set:
            hits_set.add(hit["id"])
            hits.append(hit)
    return hits, hits_set

def get_disease_name(disease_id, graphql_url):
    prompt = prompt_for_disease_name.replace("DISEASE_ID", disease_id)
    response = requests.post(graphql_url, json={'query': prompt})
    data = response.json()
    data["data"]["disease"]["id"] = disease_id
    hits = []
    hits_set = set()

    hits.append(data['data']['disease'])
    hits_set.add(data['data']['disease']['name'])

    return hits, hits_set
    
def get_disease_targets(diseases, graphql_url, min_score=0.33):
    """Get targets associated with multiple disease IDs above a minimum score."""
    all_targets = []
    target_set = set()  # To avoid duplicates
    
    for disease in diseases:
        prompt = prompt_for_disease_targets.replace("DISEASE_ID", disease['id'])
        response = requests.post(graphql_url, json={'query': prompt})
        data = response.json()
        
        if 'data' in data and data['data']['disease']:
            for row in data['data']['disease']['associatedTargets']['rows']:
                target = row['target']
                score = row['score']
                if score >= min_score and target['id'] not in target_set:
                    target_set.add(target['id'])
                    all_targets.append({
                        'id': target['id'],
                        'symbol': target['approvedSymbol'],
                        'score': score,
                        'disease_id': disease['id']
                    })
    
    return all_targets, target_set

def get_diseases_for_targets(targets, diseases, graphql_url, min_score=0.33):
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
    
    return all_diseases, disease_set

def get_drugs_for_diseases(diseases, graphql_url):
    """Get all drugs associated with a list of disease IDs."""
    drugs = []
    drug_set = set()
    
    for disease in diseases:
        prompt = prompt_for_disease_drugs.replace("DISEASE_ID", disease['id'])
        response = requests.post(graphql_url, json={'query': prompt})
        data = response.json()
        
        if 'data' in data and data['data']['disease']['knownDrugs']['rows']:
            for row in data['data']['disease']['knownDrugs']['rows']:
                drug = row['drug']
                drug_id = drug["id"]
                if drug_id not in drug_set:
                    drug_set.add(drug_id)
                    drugs.append({'id': drug_id, 'name': drug['name'], 'phase': row['phase'], 'disease_id': disease['id']})
    return drugs, drug_set

def get_drug_info_for_diseases(diseases, graphql_url):
    """Get drugs and their target information for a list of diseases."""
    all_drugs = []
    drug_set = set()
    
    # Get drugs for each disease
    for disease_info in diseases:
        #print(f"disease_info={disease_info}")
        prompt = prompt_for_disease_drugs.replace("DISEASE_ID", disease_info["id"])
        response = requests.post(graphql_url, json={'query': prompt})
        data = response.json()
        print(f"data={json.dumps(data, indent=2)}")
        
        # Get drugs for the disease
        if 'data' in data and data['data']['disease']['knownDrugs']['rows']:
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
                linked_targets = []  # Initialize the list here
                #print(f"data2={json.dumps(data2, indent=2)}")
                for row in data2['data']['drug']['linkedTargets']['rows']:
                    linked_targets.append(row['id'])
                #if linked_targets:
                #    print(f"linked_targets={linked_targets}")
                
                #row = data2['data']['drug']['linkedTargets']['rows'][0] # This is the first target for the drug
                #print(f"row={row}")
                drug_info.update({
                    #"target_id": row["id"],
                    #"target_symbol": row["approvedSymbol"],
                    #"target_name": row["approvedName"],
                    "linked_targets": linked_targets
                })
                all_drugs.append(drug_info)
    
    return all_drugs, drug_set

def get_targets_for_drugs(drugs, graphql_url):
    """Get targets for a list of drugs."""
    targets = []
    target_set = set()
    for drug in drugs:
        print(f"Getting targets for drug={drug}")
        prompt = prompt_get_targets_for_drug.replace("DRUG_ID", drug["id"])
        response = requests.post(graphql_url, json={'query': prompt})
        data = response.json()
        # print(f"data={json.dumps(data, indent=2)}")
        for row in data['data']['drug']['linkedTargets']['rows']:
          targets.append(row)
          target_set.add(row['id'])
  
    return targets, target_set  

def get_pathways_for_targets(targets, graphql_url):
    """Get pathways for a list of targets."""
    pathways = []
    pathway_set = set()
    
    for target in targets:
        prompt = prompt_get_pathways_for_target.replace("TARGET_ID", target["id"])
        response = requests.post(graphql_url, json={'query': prompt})
        data = response.json()
        print(f"data={json.dumps(data, indent=2)}")
        if 'data' in data and data['data']['target']['pathways']:
            for pathway in data['data']['target']['pathways']:
                print(f"pathway={pathway}")
                pathway_id = pathway["pathwayId"]
                if pathway_id not in pathway_set:
                    pathway_set.add(pathway_id)
                    pathways.append({
                        'pathwayID': pathway_id,
                        'pathway': pathway['pathway'],
                        'topLevelTerm': pathway['topLevelTerm'],
                    })
    
    return pathways, pathway_set

# Test functions
def test_get_diseases():
    print(f"\n\nget_diseases\n\n")
    hits, hits_set = get_diseases("ovarian carcinoma", graphql_url)
    df = pd.DataFrame(hits)
    print(f"\n\n{df}\n\n")

def test_get_disease_name():
    print(f"\n\nget_disease_name\n\n")
    for disease_id in ["EFO_0000313", "EFO_0002618", "EFO_1000218", "EFO_0000305", "EFO_0001663"]:
        disease_name, disease_name_set   = get_disease_name(disease_id, graphql_url)
        df = pd.DataFrame(disease_name)
        print(f"\n\n{df}\n\n")
    return

def test_get_drugs_for_diseases():
    print(f"\n\nget_drugs_for_diseases\n\n")
    diseases = [{"id": "EFO_0001075"}, {"id": "EFO_0001076"}, {"id": "EFO_0001663"}]
    drugs, drug_set = get_drugs_for_diseases(diseases, graphql_url)
    df = pd.DataFrame(drugs)
    print(f"\n\n{df}\n\n")
    return

def test_get_drug_info_for_diseases():
    print(f"\n\nget_drug_info_for_diseases\n\n")
    diseases = [{"id": "EFO_0001075"}]
    drugs, drug_set = get_drug_info_for_diseases(diseases, graphql_url)
    df = pd.DataFrame(drugs)
    print(f"\n\n{df}\n\n")
    return

def test_get_disease_targets():
    print(f"\n\nget_disease_targets\n\n")
    diseases = [{"id": "EFO_0001075"}]
    targets, target_set = get_disease_targets(diseases, graphql_url)
    df = pd.DataFrame(targets)
    print(f"\n\n{df}\n\n")
    return

def test_get_targets_for_drugs():
    print(f"\n\ntest_get_targets_for_drugs\n\n")
    drugs = [{"id": "CHEMBL112"}]
    targets, target_set = get_targets_for_drugs(drugs, graphql_url)
    df = pd.DataFrame(targets)
    print(f"\n\n{df}\n\n")
    return


def test_get_diseases_for_targets():
    print(f"\n\nget_diseases_for_targets\n\n")
    targets = [{"id": "ENSG00000012048"}]
    diseases = [{"id": "EFO_0001075"}]
    diseases, disease_set = get_diseases_for_targets(targets, diseases, graphql_url)
    df = pd.DataFrame(diseases)
    print(f"\n\n{df}\n\n")
    return

def test_get_pathways_for_targets(targets=[{"id": "ENSG00000012048"}]):
    print(f"\n\nget_pathways_for_targets {targets}\n\n")
    pathways, pathway_set = get_pathways_for_targets(targets, graphql_url)
    df = pd.DataFrame(pathways)
    print(f"\n\n{df}\n\n")
    return

if __name__ == "__main__":
    #test_get_diseases()
    # test_get_disease_name()
    #test_get_drugs_for_diseases()
    #test_get_disease_targets()
    #test_get_diseases_for_targets()
    test_get_drug_info_for_diseases()
    #test_get_diseases_for_targets([{"id": "ENSG00000198785"}])
    #test_get_pathways_for_targets()
    #test_get_targets_for_drugs()