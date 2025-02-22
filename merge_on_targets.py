import sys
import pandas as pd

if sys.argv == 3:
	f1=sys.argv[1]
	f2=sys.argv[2]
else:
	f1="main_targets.csv"
	f2="related_drugs_info.csv"

df1=pd.read_csv(f1, header=0)
df2=pd.read_csv(f2, header=0)

df_merged_on_target=df1.merge(df2, left_on="id", right_on="target_id", how="inner")

df_merged_on_target.drop(columns=['Unnamed: 0_x'], inplace=True)
df_merged_on_target.drop(columns=['Unnamed: 0_y'], inplace=True)

df_merged_on_target.rename(columns={'id_x':'main_target_id', 'disease_id': 'main_disease_id', 'id_y':'related_drug_id', 'target_id':'related_target_id', 'disease_id_x':'main_disease_id','disease_id_y':'related_disease_id'}, inplace=True)

df_merged_on_target.rename(columns={'disease_name':'releated_disease_name'})
print(f'df_merged_on_target:\n\n{df_merged_on_target}')
df_merged_on_target.to_csv("merged_on_target.csv")

# what I want here is the related target disease

