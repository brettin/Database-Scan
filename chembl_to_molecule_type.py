import sys, json, requests

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

def get_molecule_type(data):
    molecule_type = data.get('molecule_type')    
    return molecule_type

def get_molecule_name(data):
    # Get the preferred name if available, otherwise pref_name
    molecule_name = data.get('pref_name')
    if not molecule_name:
        # Fall back to molecule dictionary name if pref_name is not available
        molecule_name = data.get('molecule_dictionary', {}).get('pref_name')
    return molecule_name

def main(chembl_id):
    url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/{chembl_id}.json"
    data = get_data(url)
    molecule_type = get_molecule_type(data)
    molecule_name = get_molecule_name(data)
    
    return molecule_type, molecule_name

if __name__ == "__main__":
    if len(sys.argv) == 2:
        chembl_id = sys.argv[1]
    else:
        chembl_id = "CHEMBL2007641" # Example: Antibody
        #chembl_id = "CHEMBL25"  # Example: Aspirin

    molecule_type, molecule_name = main(chembl_id)
    print(f'{chembl_id}\t{molecule_type}\t{molecule_name}')
