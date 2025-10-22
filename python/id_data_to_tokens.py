import pandas as pd

# Load data
cart_df = pd.read_excel("datos\\intensifier_data_CART_101825.xlsx")
id_df = pd.read_excel("datos\\CARTIDs101825.xlsx")

def iterate_df_and_update(df, output_filepath):
    transformed_data = []

    # Iterate through each row in df
    for _, row in df.iterrows():
        ID = row['ID']
        id_row = id_df[id_df['ID'] == ID]

        if not id_row.empty:
            # Convert id_row to a dict, excluding the ID column
            id_data = id_row.iloc[0].to_dict()
            id_data.pop("ID", None)

            # Combine row data with id_data
            merged_row = {**row.to_dict(), **id_data}
            transformed_data.append(merged_row)

    transformed_df = pd.DataFrame(transformed_data)
    transformed_df.to_excel(output_filepath, index=False)
    print(f"Transformed data saved to {output_filepath}")

iterate_df_and_update(cart_df, "Verbose_IntData_Cart_101925.xlsx")
