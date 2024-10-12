import pandas as pd
import numpy as np
from new_supply_curve import column_combine


def load_pred(data_df, station_df, price_pred_df):
    stations_load_df = pd.DataFrame()
    pred_price_list = price_pred_df['pred_price'].values.tolist()
    pred_price_type = price_pred_df['type_info'].values.tolist()
    over_load_list = price_pred_df['over_load'].values.tolist()
    for i in range(len(data_df)):
        part_df = column_combine(data_df.loc[i].to_frame().T)  # 行数据转列项df处理
        part_df = part_df.dropna(subset=['出力值', '报价'], how='any')
        part_df = part_df.reset_index()
        part_df = part_df.drop(columns=['index'])
        load_list = []
        for j in range(len(pred_price_list)):
            price = float(pred_price_list[j])
            type = pred_price_type[j]
            insert_index = np.searchsorted(part_df['报价'].astype(float), price)
            if 0 < insert_index < len(part_df):  # 如果电价在区间内
                if price == 1500 or price == 1500.0:  # 如果电价为1500
                    if type == 1:
                        if insert_index == len(data_df) - 1:  # 只有一个1500报价
                            load = part_df.iloc[insert_index, 0]
                        else:  # 报多个1500按照额定容量分
                            shared_load = over_load_list[j]
                            load = part_df.iloc[insert_index, 0] + shared_load * float(station_df.iloc[i, 3])
                        load_list.append(load)
                    if type == 2:
                        load_list.append(part_df.iloc[len(part_df) - 1, 0])
                else:  # 什么条件都不满足就走斜率相同路线
                    start_price = part_df.iloc[insert_index - 1, 1]
                    end_price = part_df.iloc[insert_index, 1]
                    start_load = part_df.iloc[insert_index - 1, 0]
                    end_load = part_df.iloc[insert_index, 0]
                    load = (end_load * (price - start_price) + start_load * (end_price - price)) / (
                            end_price - start_price)
                    load_list.append(load)
            if insert_index == 0:  # 如果电价为0，则获取最左边的负荷
                if type == -1:  # 加权计算
                    shared_load = over_load_list[j]
                    load = part_df.iloc[0, 0] + shared_load * float(station_df.iloc[i, 2])
                    load_list.append(load)
                if type == -2 or type == 0:
                    load_list.append(part_df.iloc[0, 0])
            if insert_index == len(part_df):  # 如果电价超过最大报价
                load_list.append(part_df.iloc[len(part_df) - 1, 0])
        stations_load_df[station_df.iloc[i, 0]] = load_list
    return stations_load_df
