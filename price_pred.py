import pandas as pd
import numpy as np

time_list = ["00:15", "00:30", "00:45", "01:00", "01:15", "01:30", "01:45", "02:00", "02:15", "02:30", "02:45", "03:00",
             "03:15", "03:30", "03:45", "04:00", "04:15", "04:30", "04:45", "05:00", "05:15", "05:30", "05:45", "06:00",
             "06:15", "06:30", "06:45", "07:00", "07:15", "07:30", "07:45", "08:00", "08:15", "08:30", "08:45", "09:00",
             "09:15", "09:30", "09:45", "10:00", "10:15", "10:30", "10:45", "11:00", "11:15", "11:30", "11:45", "12:00",
             "12:15", "12:30", "12:45", "13:00", "13:15", "13:30", "13:45", "14:00", "14:15", "14:30", "14:45", "15:00",
             "15:15", "15:30", "15:45", "16:00", "16:15", "16:30", "16:45", "17:00", "17:15", "17:30", "17:45", "18:00",
             "18:15", "18:30", "18:45", "19:00", "19:15", "19:30", "19:45", "20:00", "20:15", "20:30", "20:45", "21:00",
             "21:15", "21:30", "21:45", "22:00", "22:15", "22:30", "22:45", "23:00", "23:15", "23:30", "23:45", "00:00"]


def price_pred(pred_load_list, supply_df):
    pred_price_list = []
    type_info = []
    over_load_list = []

    load_list = supply_df['出力值'].values.tolist()
    left_load = load_list[0]
    min_load = load_list[1]
    right_load = load_list[len(load_list) - 1]
    max_load = load_list[len(load_list) - 2]

    for i in range(len(pred_load_list)):
        pred_load = pred_load_list[i]
        insert_index = np.searchsorted(supply_df['出力值'], pred_load)

        # 判断负荷区间, 电价新增特征列, 并获取超过的部分
        type = 0
        over_load = 0
        if pred_load <= min_load:
            type = -1
            over_load = pred_load - left_load
            if pred_load <= left_load:
                type = -2
                over_load = 0
        if pred_load >= max_load:
            type = 1
            over_load = pred_load - max_load
            if pred_load >= right_load:
                type = 2
                over_load = 0
        type_info.append(type)
        over_load_list.append(over_load)

        if 1 < insert_index < len(supply_df) - 1:
            nearest_indexes = [insert_index - 1, insert_index]
            start_price = supply_df.iloc[nearest_indexes[0], 0]
            end_price = supply_df.iloc[nearest_indexes[1], 0]
            start_load = supply_df.iloc[nearest_indexes[0], 1]
            end_load = supply_df.iloc[nearest_indexes[1], 1]
            pred_price = (end_price * (pred_load - start_load) + start_price * (end_load - pred_load)) / (
                    end_load - start_load)
            pred_price_list.append(pred_price)
        if insert_index <= 1:
            pred_price_list.append(0)
        if insert_index >= len(supply_df) - 1:
            pred_price_list.append(1500)
    pred_df = pd.DataFrame({'time': time_list, 'pred_price': pred_price_list, 'type_info': type_info, 'over_load': over_load_list})
    return pred_df
