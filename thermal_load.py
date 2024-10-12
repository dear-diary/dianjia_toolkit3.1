import pandas as pd


def thermal_load(data_df):
    # 火电负荷数据
    data_df = data_df.iloc[0:5, :]
    data_df = data_df[data_df.columns[2:]].astype(float)
    # 逐列减去后面行的相应列数据
    for col in data_df.columns:
        data_df.loc[0, col] -= data_df.iloc[1:, :][col].sum()
    data_list = data_df.iloc[0].tolist()
    column_list = data_df.columns.tolist()
    data_df = pd.DataFrame({'time': column_list, 'load': data_list})
    return data_df
