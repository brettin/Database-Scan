import requests, sys, time, json
from rdkit import Chem


def get_data(url):
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data == None:
            print("data is None")
    else:
        print(f"Error fetching url: {url}: HTTP {response.status_code}")
        return None

    return data


def chembl_to_smiles(chembl_id):

    url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/{chembl_id}.json"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data == None:
            print("data is None")
        try:
            smiles = data.get("molecule_structures", {}).get("canonical_smiles")
        except Exception as e:
            smiles = None
            molecule_type = data.get('molecule_type')
        return smiles
    else:
        print(f"Error fetching ChEMBL ID {chembl_id}: HTTP {response.status_code}")
        return None


def verify_canonical_smiles(chembl_id):

    smiles = chembl_to_smiles(chembl_id)
    
    if smiles:
        mol = Chem.MolFromSmiles(smiles)  # Convert to RDKit molecule
        rdkit_smiles = Chem.MolToSmiles(mol, canonical=True)  # RDKit canonical SMILES
        return smiles == rdkit_smiles  # Check if they match
    else:
        return False


def main(chembl_id):

    smiles = chembl_to_smiles(chembl_id)
    is_canonical = verify_canonical_smiles(chembl_id)
    return smiles, is_canonical

if __name__ == "__main__":

    if len(sys.argv) == 2:
        chembl_id=sys.argv[1]
    else:
        chembl_id = "CHEMBL2007641" # Example: Antibody
        #chembl_id = "CHEMBL25"  # Example: Aspirin

    smiles, is_canonical = main(chembl_id)
    print(f"{chembl_id}\t{smiles}\t{is_canonical}")
