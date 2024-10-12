# 新计算供给曲线的方法
import numpy as np
import pandas as pd

# 报价最小和最大值
min_value = 0
max_value = 1500
# 报价次数
times = 10


# 列项数据合并到第1,2列后面
def column_combine(data_df):
    new_df = data_df[data_df.columns[:2]]
    for i in range(1, times):
        part_df = data_df[data_df.columns[i * 2:(i + 1) * 2]]
        part_df.columns = new_df.columns
        new_df = pd.concat([new_df, part_df])
    return new_df


def supply_curve(data_df, station_df):
    # 每个场站横向数据处理
    start_value = 0
    min_value_increment = 0
    right_value_increment = 0
    stations = len(data_df)
    quotation_set = set()
    quotation_map = {}
    supply_curve_df = pd.DataFrame(columns=['报价', '出力值'])
    min_delta_list = []
    max_delta_list = []
    for i in range(stations):
        # 构建左边两个0的报价和右边两个1500的报价
        part_df = column_combine(data_df.loc[i].to_frame().T)  # 行数据转列项df处理
        part_df = part_df.reset_index()
        part_df = part_df.dropna(subset=['报价', '出力值'], how='any')  # 去除空值数据
        min_df = part_df[part_df['报价'] == min_value]
        max_df = part_df[part_df['报价'] == max_value]
        stations_min_list = min_df['出力值'].values.tolist()
        stations_max_list = max_df['出力值'].values.tolist()
        min_len = len(stations_min_list)
        max_len = len(stations_max_list)
        min_delta = 0
        max_delta = 0
        if min_len > 0:
            start_value += stations_min_list[0]  # 最左值的构建过程
            if min_len > 1:
                min_delta = stations_min_list[min_len - 1] - stations_min_list[0]
                min_value_increment += min_delta  # 最左到最小值增量构建过程
        if max_len > 1:
            max_delta = stations_max_list[max_len - 1] - stations_max_list[0]
            right_value_increment += max_delta  # 最大值到最右值增量构建过程
        min_delta_list.append(min_delta)
        max_delta_list.append(max_delta)
        # 计算每段报价的斜率值
        quotation_list = part_df['报价'].unique()
        quotation_list.sort()
        quotation_list = [float(x) for x in quotation_list]
        quotation_set.update(quotation_list)
        k_list = []
        map_list = []
        for j in range(len(quotation_list)-1):  # 获取斜率list，个数为报价数减1，区间判断时为左开右闭
            now_q = quotation_list[j]
            next_q = quotation_list[j+1]
            now_l = part_df[part_df['报价'] == now_q].iloc[-1]['出力值']  # 当存在多个0和1500时，获取最后一个0和第一个1500
            next_l = part_df[part_df['报价'] == next_q].iloc[0]['出力值']
            k = (next_q - now_q) / (next_l - now_l)
            k_list.append(k)
        map_list.append(quotation_list)
        map_list.append(k_list)
        quotation_map[i] = map_list

    quotation_set.discard(0)  # 去除0的报价
    quotation_list = list(quotation_set)
    quotation_list.sort()
    supply_curve_df['报价'] = [float(0), float(0)] + quotation_list
    supply_curve_df['出力值'] = [float(start_value), float(min_value_increment)] + [np.nan] * len(quotation_list)
    supply_curve_df = supply_curve_df.astype(float)
    for idx, quotation in enumerate(quotation_list):
        delta_x = 0
        if idx == 0:
            delta_y = quotation - 0
            for key, lists in quotation_map.items():
                if lists[0][0] < quotation <= lists[0][1]:
                    k = lists[1][idx]
                    delta_x += delta_y / k
        else:
            for key, lists in quotation_map.items():
                for in_idx, unit_quotation in enumerate(lists[0]):
                    if quotation < unit_quotation and in_idx == 0:  # 机组报价都在这个报价之上
                        break
                    if quotation > unit_quotation and in_idx == len(lists[0]) - 1:  # 机组报价都在这个报价之下
                        continue
                    if unit_quotation < quotation <= lists[0][in_idx + 1]:  # 机组报价包含这个报价
                        k = lists[1][in_idx]
                        delta_y = quotation - quotation_list[idx - 1]
                        delta_x += (delta_y / k)
        supply_curve_df.iloc[idx + 2, 1] = float(delta_x)

    # 追加最右侧的1500
    new_row = {'报价': [1500], '出力值': [float(right_value_increment)]}
    last_df = pd.DataFrame(new_row)
    supply_curve_df = pd.concat([supply_curve_df, last_df], ignore_index=True)
    supply_curve_df = supply_curve_df.astype(float)
    supply_curve_df['出力值'] = supply_curve_df['出力值'].cumsum()
    # station追加列
    if min_value_increment == 0:
        station_df['min_k'] = min_delta_list
    else:
        min_delta_list = [x / min_value_increment for x in min_delta_list]
        station_df['min_k'] = min_delta_list
    if right_value_increment == 0:
        station_df['max_k'] = max_delta_list
    else:
        max_delta_list = [x / right_value_increment for x in max_delta_list]
        station_df['max_k'] = max_delta_list
    return supply_curve_df, station_df
