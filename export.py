import pandas as pd

data = pd.read_pickle(r'C:\Users\cathy\Downloads\quest\output\step_1_elements.pkl')
data.to_excel(r'C:\Users\cathy\Downloads\quest\output\step_1_elements.xlsx', index=False)
print("Klaar! Bestand opgeslagen.")

data = pd.read_pickle(r'C:\Users\cathy\Downloads\quest\output\step_2_materials.pkl')
data.to_excel(r'C:\Users\cathy\Downloads\quest\output\step_2_materials.xlsx', index=False)
print("Klaar! Bestand opgeslagen.")
