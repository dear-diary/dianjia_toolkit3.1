# 关注数据列起始index
output_value_index = 0
quoted_price_index = 1

# 报价次数
times = 10


def data_process(data_df, all_stop_unit):
    station_df = data_df[data_df.columns[0:2]]  # 场站容量df
    station_df = station_df.rename(columns={station_df.columns[0]: 'name', station_df.columns[1]: 'cap'})

    # 关闭机组和试验机组去除
    mask = data_df['机组名称'].isin(all_stop_unit)
    drop_index = data_df[mask].index.tolist()
    data_df = data_df[data_df.columns[2:]]

    # 数据类型转换
    data_df.iloc[:, output_value_index:times * 2 + output_value_index - 1] = data_df.iloc[:, output_value_index:times * 2 + output_value_index - 1].astype(float)

    # 数据df处理
    data_df = data_df.drop(drop_index).astype(float)
    data_df.columns.values[0] = '出力值'      # 修改第1、2列的列名
    data_df.columns.values[1] = '报价'
    data_df = data_df.reset_index()
    data_df = data_df.drop(columns=['index'])
    # 场站df处理
    station_df = station_df.drop(drop_index)
    station_df = station_df.reset_index()
    station_df = station_df.drop(columns=['index'])
    station_df['cap'] = station_df['cap'].astype(float)
    return data_df, station_df
