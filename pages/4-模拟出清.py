import copy
import sys
import warnings
import numpy as np
import pandas as pd
import streamlit as st
from copy import deepcopy
from data_process import data_process
from load_pred import load_pred
from new_supply_curve import supply_curve
from price_pred import price_pred
from thermal_load import thermal_load

warnings.filterwarnings("ignore")

sys.path.append('..')
from logger import Logger
from utils import get_time_index, str_to_list, merge_lists

# 获取日志对象
logger = Logger.get_logger(True, False)

st.set_page_config(page_title="模拟出清", page_icon="🌍", layout="wide")
# 去除页脚
st.markdown("""<style>footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

df, pl = None, None
if '机组报价表' in st.session_state:
    df = st.session_state['机组报价表']
    if df['机组名称'].isna().all():
        st.error("请在“数据准备”中复制好《机组报价表》！！", icon="🚨")
else:
    st.error("请在“数据准备”中复制好《机组报价表》！！", icon="🚨")
if '披露表' in st.session_state:
    pl = st.session_state['披露表']
else:
    st.error("请在“数据准备”中上传《事前信息披露表》！！", icon="🚨")

# 调频
min_cap = 0.55
max_cap = 0.95
fm_step = 0.05

startup_shutdown = None
stop_unit = None
fm_quotation = None
spinning_reserve = None
if '开停机' in st.session_state.keys():
    startup_shutdown = st.session_state['开停机']
if '停机机组' in st.session_state.keys():
    stop_unit = st.session_state['停机机组']
if '调频报价表' in st.session_state.keys():
    fm_quotation = st.session_state['调频报价表']
    fm_quotation.iloc[:, 1:] = fm_quotation.iloc[:, 1:].astype(float)
if '旋转备用' in st.session_state.keys():
    spinning_reserve = st.session_state['旋转备用']

# 生成00:15-00:00的96个点的时刻
time_list = [f"{hour:02d}:{minute:02d}" for hour in range(0, 24) for minute in range(0, 60, 15) if
             not (hour == 0 and minute < 15)] + ['00:00']
# 生成00:15-00:00的24个点的时刻
hour_list = ['{:02d}:15'.format(hour) for hour in range(24)]

# 集团列表
group_lists = ["赣能", "华能", "国家能源", "国家电投", '大唐']

# 能否出清标识
result_flag = False

# 峰平谷配置:
try:
    peak_valley_df = pd.read_csv('config/peak_valley_config.csv', encoding='gbk')
    peak_valley_df = peak_valley_df.astype(str)
    peak_valley_df = peak_valley_df.where(peak_valley_df != 'nan', None)
except Exception:
    peak_valley_df = None

# 机组爬坡速率配置
try:
    ramp_rate_df = pd.read_csv('config/ramp_rate.csv', encoding='gbk')
    ramp_rate_df = ramp_rate_df.where(ramp_rate_df != 'nan', None)
    ramp_rate_df['爬坡速率（MW/分钟）'] = ramp_rate_df['爬坡速率（MW/分钟）'].apply(lambda x: x * 15)  # 每15分钟的爬坡速率
except Exception:
    ramp_rate_df = None

# 机组开停机曲线配置
try:
    start_stop_curve_df = pd.read_excel('config/start_stop_curve.xlsx')
    start_stop_curve_df = start_stop_curve_df.astype(str)
    start_stop_curve_df = start_stop_curve_df.where(start_stop_curve_df != 'nan', None)
except Exception:
    start_stop_curve_df = None

if df is not None and pl is not None:

    @st.cache_data
    # 获取实验机组和开停机机组的时刻试验负荷和时刻关机机组（新增）
    def time_shut_exp_unit_and_load(uss_df: pd.DataFrame, ssc_df: pd.DataFrame):
        time_shut_set = [set() for _ in range(96)]  # 构建包含96个空set的列表
        time_exp_set = [set() for _ in range(96)]  # 构建包含96个空set的列表
        time_exp_load_list = [0] * 96  # 构建包含96个0的列表
        curve_dict = {'机组名称': [], '开机曲线': [], '停机曲线': [], '区间索引': []}
        if uss_df is not None:
            for _, row in uss_df.iterrows():
                unit_name = row['机组名称']
                start_flag = row['开机状态']
                start_time = row['开机时间']
                shut_time = row['停机时间']
                curve_list = []
                index_list = []

                ssc_rows = ssc_df.loc[ssc_df['机组名称'] == unit_name]  # 获取机组的开停机曲线
                if len(ssc_rows) > 0:
                    ssc_row = ssc_rows.iloc[0]
                    stop_load_curve = ssc_row['停机曲线']
                    start_load_curve = ssc_row['开机曲线']
                    stop_load_curve = str_to_list(stop_load_curve, None)
                    start_load_curve = str_to_list(start_load_curve, None)
                else:
                    stop_load_curve = None
                    start_load_curve = None

                if start_flag:  # 如果是开机状态，那么只关注停机时间
                    if shut_time is not pd.NaT:
                        time_index = get_time_index(shut_time)
                        for i in range(time_index + 1, 96):
                            time_shut_set[i].add(unit_name)
                            if stop_load_curve is not None:  # 固定负荷中加入停机曲线的负荷
                                curve_index = i - time_index - 1
                                if curve_index < len(stop_load_curve):
                                    curve_list.append(stop_load_curve[curve_index])
                                    index_list.append(i)
                        if stop_load_curve is not None:  # 数据加入到dict中
                            curve_dict['机组名称'].append(unit_name)
                            curve_dict['开机曲线'].append([])
                            curve_dict['停机曲线'].append(curve_list)
                            curve_dict['区间索引'].append(index_list)
                else:  # 如果是关机状态， 那么只关注开机时间
                    if start_time is not pd.NaT:
                        time_index = get_time_index(start_time)
                        for i in range(0, time_index + 1):
                            time_shut_set[i].add(unit_name)
                        if start_load_curve is not None:  # 固定负荷中加入开机曲线的负荷
                            for j in range(time_index + 1, 96):
                                curve_index = j - time_index - 1
                                if curve_index < len(start_load_curve):
                                    curve_list.append(start_load_curve[curve_index])
                                    index_list.append(j)
                            curve_dict['机组名称'].append(unit_name)
                            curve_dict['开机曲线'].append(curve_list)
                            curve_dict['停机曲线'].append([])
                            curve_dict['区间索引'].append(index_list)
                    else:  # 如果没有开机时间，那就是全天关机
                        for time_shut_list in time_shut_set:
                            time_shut_list.add(unit_name)

                for i in range(1, 4):  # 总实验次数为3
                    exp_start = row['试验开始时间' + str(i)]
                    exp_end = row['试验结束时间' + str(i)]
                    exp_loads = row['试验负荷' + str(i)]
                    if exp_start is not pd.NaT and exp_end is not pd.NaT and not pd.isna(exp_loads):
                        start_time_index = get_time_index(exp_start)
                        end_time_index = get_time_index(exp_end)
                        load_list = str_to_list(exp_loads, end_time_index - start_time_index)
                        for i in range(start_time_index + 1, end_time_index + 1):  # 实验区间的时刻
                            time_exp_set[i].add(unit_name)
                            time_exp_load_list[i] += load_list[i - start_time_index - 1]
        return time_shut_set, time_exp_set, time_exp_load_list, pd.DataFrame(curve_dict)

    # 关机机组和试验机组合并开停机灵活曲线，爬坡约束负荷和固定负荷合并
    def load_list_combine_flexible_df(tel_list, flex_df, trr_df):
        flexible_time_exp_load_list = deepcopy(tel_list)
        for _, row in flex_df.iterrows():
            index_list = row['区间索引']
            start_curve = row['开机曲线']
            stop_curve = row['停机曲线']
            if len(start_curve) == 0 and len(stop_curve) > 0:  # 停机
                for index in index_list:
                    flexible_time_exp_load_list[index] += stop_curve[index - index_list[0]]
            if len(stop_curve) == 0 and len(start_curve) > 0:  # 开机
                for index in index_list:
                    flexible_time_exp_load_list[index] += start_curve[index - index_list[0]]
        for _, row in trr_df.iterrows():
            index_list = row['index']
            fixed_load_list = row['fixed_load']
            for i in range(len(index_list)):
                flexible_time_exp_load_list[index_list[i]] += fixed_load_list[i]
        return flexible_time_exp_load_list


    def remove_set_combine_ramp_rate(rus, trr_df):
        turn_remove_unit_set = deepcopy(rus)
        if not trr_df.empty:
            for _, row in trr_df.iterrows():
                unit_name = row['unit']
                index_list = row['index']
                for index in index_list:
                    turn_remove_unit_set[index].add(unit_name)
        return turn_remove_unit_set


    def fm_exp_unit(index, unit_name, tse_list):
        tse_start_index = index * 4  # 00:15, 00:30, 00:45, 01:00
        tse_end_index = (index + 1) * 4
        for i in range(tse_start_index, tse_end_index):
            if unit_name in tse_list[i]:
                return True
        return False

    @st.cache_data
    # 获取每小时参与调频的机组
    def get_hour_fm_unit(fq_df: pd.DataFrame, hour_fm, tse_set):
        if hour_fm is None:
            return [[] for _ in range(24)]
        hour_fm_unit_lists = []
        for index, total_fm_cap in enumerate(hour_fm):  # 遍历24小时的调频需求
            fm_unit_list = []  # 参与调频的机组
            if total_fm_cap == 0:
                hour_fm_unit_lists.append(fm_unit_list)
                continue
            quotation_column = '调频报价' + str(index + 1)
            quotation_list = []  # 最终调频报价
            param_k_list = []  # 调频K指标
            unit_capacity_list = []  # 机组容量
            unit_name_list = []  # 机组名称
            for i, row in fq_df.iterrows():  # 遍历调频机组报价
                unit_name = row['机组名称']
                if fm_exp_unit(index, unit_name, tse_set):  # 关机试验机组不能参与调频
                    continue
                quotation = float(row[quotation_column])
                all_quotation = float(row['调频统一报价'])
                param_k = float(row['调频指标K'])
                unit_name = row['机组名称']
                if param_k >= 0.9:  # 系数不低于0.9
                    if (not pd.isna(all_quotation)) or (not pd.isna(quotation)):  # 统一报价和时刻报价都不为空
                        if not pd.isna(all_quotation):
                            quotation = all_quotation
                        final_quotation = quotation / param_k
                        quotation_list.append(final_quotation)
                        param_k_list.append(param_k)
                        unit_capacity = df.loc[df['机组名称'] == unit_name, '机组容量(MW)'].iloc[0]  # 获取机组容量
                        unit_capacity_list.append(float(unit_capacity))
                        unit_name_list.append(unit_name)
            # 从低到高进行排序，相同时的对比顺序为调频报价从低到高，K从高到低，容量从高到低
            indices = list(range(len(quotation_list)))
            sorted_indices = sorted(indices,
                                    key=lambda i: (quotation_list[i], -param_k_list[i], -unit_capacity_list[i]))
            # 确定调频出清机组
            fm_cap = 0
            if total_fm_cap is not None:
                for idx in sorted_indices:
                    unit_name = unit_name_list[idx]
                    unit_cap = unit_capacity_list[idx] * fm_step
                    fm_cap += unit_cap
                    fm_unit_list.append(unit_name)
                    if fm_cap >= total_fm_cap:
                        break
            hour_fm_unit_lists.append(fm_unit_list)
        return hour_fm_unit_lists

    # 计算不同供给曲线的分段区间
    def get_diff_sc_period(ru_set):
        period = []  # 返回连续的数字区间字符串列表
        start_unit_flag = ru_set[0]  # 标识阶段起始的机组set，初始化为第一个
        start_flag = 0  # 阶段起始的时间， 初始化为第一个
        for index, unit_set in enumerate(ru_set):
            if unit_set != start_unit_flag:  # 如果当前时刻的机组不等于上一阶段
                time_unit_map = {}
                time_period = str(start_flag) + '-' + str(index - 1)
                time_unit_map[time_period] = ru_set[index - 1]
                period.append(time_unit_map)
                start_unit_flag = unit_set
                start_flag = index
            if index == len(ru_set) - 1:  # 遍历到最后
                time_unit_map = {}
                time_period = str(start_flag) + '-' + str(index)
                time_unit_map[time_period] = unit_set
                period.append(time_unit_map)
        return period

    def get_exp_load_from_index(uss_df, unit_name, idx):
        row = uss_df[uss_df['机组名称'] == unit_name].iloc[0]
        for i in range(1, 4):
            exp_start = row['试验开始时间' + str(i)]
            exp_end = row['试验结束时间' + str(i)]
            exp_load = row['试验负荷' + str(i)]
            if exp_start is not pd.NaT and exp_end is not pd.NaT and exp_load is not None:
                start_time_index = get_time_index(exp_start) + 1
                end_time_index = get_time_index(exp_end)
                if start_time_index <= idx <= end_time_index:
                    load_list = str_to_list(exp_load, end_time_index - start_time_index + 1)
                    return load_list[idx - start_time_index]

    def get_unit_cap(q_df, unit_name):
        row = q_df[q_df['机组名称'] == unit_name].iloc[0]
        return row['机组容量(MW)']

    def get_unit_sr(sr_df, unit_name):
        try:
            row = sr_df[sr_df['机组名称'] == unit_name].iloc[0]
            return float(row['旋备容量(MW)'])
        except Exception:
            return 0

    def get_unit_ramp_rate(rr_df, unit_name):
        try:
            row = rr_df[rr_df['机组名称'] == unit_name].iloc[0]
            return float(row['爬坡速率（MW/分钟）'])
        except Exception:
            return None

    # 机组出力值调整（新增）
    def result_unit_load_df_process(rul_df, uss_df, q_df, sr_df, flex_df, ts_set, te_set, minflu_set, maxflu_set, slu_set, trr_df):
        for idx, unit_set in enumerate(ts_set):  # 停机机组
            if len(unit_set) != 0:
                for unit_name in unit_set:
                    rul_df.at[idx, unit_name] = 0
        for _, row in flex_df.iterrows():  # 开停机曲线限制机组
            unit_name = row['机组名称']
            index_list = row['区间索引']
            start_curve = row['开机曲线']
            stop_curve = row['停机曲线']
            if len(start_curve) == 0 and len(stop_curve) > 0:  # 停机
                for i in range(len(stop_curve)):
                    rul_df.at[index_list[i], unit_name] = stop_curve[i]
            if len(stop_curve) == 0 and len(start_curve) > 0:  # 开机
                for i in range(len(start_curve)):
                    rul_df.at[index_list[i], unit_name] = start_curve[i]
        for idx, unit_set in enumerate(te_set):  # 试验机组
            if len(unit_set) != 0:
                for unit_name in unit_set:
                    rul_df.at[idx, unit_name] = get_exp_load_from_index(uss_df, unit_name, idx)
        for idx, unit_set in enumerate(minflu_set):  # 限制最小出力机组
            if len(unit_set) != 0:
                for unit_name in unit_set:
                    rul_df.at[idx, unit_name] = get_unit_cap(q_df, unit_name) * min_cap
        for idx, unit_set in enumerate(maxflu_set):  # 限制最大出力机组
            if len(unit_set) != 0:
                for unit_name in unit_set:
                    rul_df.at[idx, unit_name] = get_unit_cap(q_df, unit_name) * max_cap
        for idx, unit_set in enumerate(slu_set):  # 旋备限制最大出力机组
            if len(unit_set) != 0:
                for unit_name in unit_set:
                    if pd.isna(rul_df.at[idx, unit_name]):
                        rul_df.at[idx, unit_name] = get_unit_cap(q_df, unit_name) - get_unit_sr(sr_df, unit_name)
                    else:
                        rul_df.at[idx, unit_name] = rul_df.at[idx, unit_name] - get_unit_sr(sr_df, unit_name)
        if not trr_df.empty:  # 爬坡约束机组
            for _, row in trr_df.iterrows():
                unit_name = row['unit']
                index = row['index']
                fixed_load_list = row['fixed_load']
                for i in range(len(index)):
                    rul_df.at[index[i], unit_name] = fixed_load_list[i]
        # 如果一天全为0，那么去除该机组
        for column in rul_df.columns:
            if (rul_df[column] == 0).all():
                rul_df = rul_df.drop(column, axis=1)
        return rul_df

    # 爬坡边界条件限制（优先满足）
    def ramp_rate_boundary(rul_df: pd.DataFrame, rr_df: pd.DataFrame, flex_df):
        new_turn_ramp_rate_df = pd.DataFrame(columns=['unit', 'index', 'fixed_load'])
        unit_load_dict = rul_df.to_dict(orient='list')  # 转dict
        for key, value in unit_load_dict.items():  # 遍历机组
            ramp_rate = get_unit_ramp_rate(rr_df, key)
            rows = flex_df[flex_df['机组名称'] == key]
            start_index = None
            # 判断停机起始index
            if len(rows) > 0:
                row = rows.iloc[0]
                if len(row['停机曲线']) > 0:
                    index_list = row['区间索引']
                    start_index = index_list[0]
            if not pd.isna(ramp_rate):  # 机组存在爬坡约束
                for i in range(len(value) - 1):  # 判断前后两个值之间的差值是否满足爬坡速率
                    before_value = value[i]
                    after_value = value[i + 1]
                    delta = after_value - before_value
                    abs_delta = abs(delta)
                    if abs_delta > ramp_rate:  # 不满足时
                        if start_index is not None and (i + 1) > start_index:  # 后一个索引超过关机区间时不做处理，第一个停机时间点的值放过，因为要作为修正的边界条件
                            continue
                        if delta > 0:  # 增加出力时超过爬坡约束
                            value[i + 1] = before_value + ramp_rate
                        else:  # 降低出力时超过爬坡约束
                            value[i + 1] = before_value - ramp_rate
                        rul_df.at[i + 1, key] = value[i + 1]
                        if start_index is not None and (i+1) == start_index:  # 不包括起始第一个点
                            continue
                        else:
                            new_turn_ramp_rate_df = insert_ramp_rate_unit(new_turn_ramp_rate_df, i+1, key, value[i+1])
                # 根据停机曲线第一个时间的负荷进行灵活曲线调整
                rul_df, flex_df = flexible_df_adjust(key, rul_df, flex_df)
        new_turn_ramp_rate_df = new_turn_ramp_rate_df.reset_index(drop=True)  # 索引重置
        return new_turn_ramp_rate_df, flex_df

    # 插入数据进去
    def insert_ramp_rate_unit(new_turn_ramp_rate_df, index, unit_name, value):
        exists = unit_name in new_turn_ramp_rate_df['unit'].values
        if exists:
            result = new_turn_ramp_rate_df[new_turn_ramp_rate_df['unit'] == unit_name]
            result_row = result.iloc[0]
            result_row['index'].append(index)
            result_row['fixed_load'].append(value)
        else:
            insert_df = pd.DataFrame(data={'unit': unit_name, 'index': [[index]], 'fixed_load': [[value]]})
            new_turn_ramp_rate_df = pd.concat([new_turn_ramp_rate_df, insert_df])
        return new_turn_ramp_rate_df

    # 开停机灵活曲线动态调整
    def flexible_df_adjust(unit_name, rul_df, flex_df):
        rows = flex_df[flex_df['机组名称'] == unit_name]
        ramp_rate = get_unit_ramp_rate(ramp_rate_df, unit_name)
        if len(rows) > 0:
            row = rows.iloc[0]
            stop_curve = row['停机曲线']
            index_list = row['区间索引']
            if len(stop_curve) > 0:
                start_load = stop_curve[0]
                start_index = index_list[0]
                real_load = rul_df.at[start_index, unit_name]  # 真实负荷
                if start_load != real_load:  # 不相等时需要进行调整
                    new_stop_curve = []
                    new_index_list = []
                    start_stop_row = start_stop_curve_df[start_stop_curve_df['机组名称'] == unit_name].iloc[0]
                    origin_stop_curve = start_stop_row['停机曲线']
                    origin_stop_curve = str_to_list(origin_stop_curve, None)
                    origin_start_load = origin_stop_curve[0]
                    while real_load > origin_start_load:
                        new_stop_curve.append(real_load)
                        new_index_list.append(start_index)
                        real_load = max(real_load - ramp_rate, origin_start_load)
                        if real_load == origin_start_load:
                            break
                        else:
                            start_index += 1
                    start_index = start_index + 1
                    for load in origin_stop_curve:
                        if start_index <= 95:
                            new_stop_curve.append(load)
                            new_index_list.append(start_index)
                            rul_df.at[start_index, unit_name] = load
                            start_index += 1
                        else:
                            break
                    row_index = flex_df.index[flex_df['机组名称'] == unit_name][0]
                    flex_df.at[row_index, '停机曲线'] = new_stop_curve
                    flex_df.at[row_index, '区间索引'] = new_index_list
        return rul_df, flex_df

    # 合并
    def ramp_rate_integrate(trr_df, ntrr_df, rul_df, rr_df):
        if trr_df.empty:
            return ntrr_df
        else:
            for _, row in trr_df.iterrows():  # 遍历之前的数据，判断当前迭代下出清，是否依然存在前迭代的爬坡限制
                unit_name = row['unit']
                ramp_rate = get_unit_ramp_rate(rr_df, unit_name)
                index_list = row['index']
                fixed_load_list = row['fixed_load']
                new_index_list = []
                new_fixed_load_list = []
                for i in range(len(index_list)):
                    index = index_list[i]
                    load = fixed_load_list[i]
                    clearing_load = rul_df.at[index, unit_name]
                    before_clearing_load = rul_df.at[index - 1, unit_name]
                    delta = abs(clearing_load - before_clearing_load)
                    if delta == ramp_rate:  # 如果delta和ramp_rate一样则保留
                        new_index_list.append(index)
                        new_fixed_load_list.append(load)

                if len(new_index_list) > 0:  # 把数据合并到新的 trr_df 中
                    exists = unit_name in ntrr_df['unit'].values
                    if exists:  # 存在时按index顺序合并
                        result = ntrr_df[ntrr_df['unit'] == unit_name]
                        result_row = result.iloc[0]
                        result_index = result.index[0]
                        merged_index, merged_load = merge_lists(new_index_list, new_fixed_load_list, result_row['index'], result_row['fixed_load'])  # 合并
                        ntrr_df.loc[result_index, 'index'] = merged_index
                        ntrr_df.loc[result_index, 'fixed_load'] = merged_load
                    else:  # 不存在时插入
                        new_row = pd.DataFrame(data={'unit': unit_name, 'index': [new_index_list], 'fixed_load': [new_fixed_load_list]})
                        ntrr_df = pd.concat([ntrr_df, new_row])
            return ntrr_df

    # 其余边界条件限制
    def boundary_condition(rul_df: pd.DataFrame, hfu_list, te_set, fl_list, q_df: pd.DataFrame,
                           sr_df: pd.DataFrame, rr_df: pd.DataFrame, trr_df):
        flag = True
        minfm_limit_unit_set= [set() for _ in range(96)]  # 因调频被限制最小出力的机组列表
        maxfm_limit_unit_set = [set() for _ in range(96)]  # 因调频被限制最大出力的机组列表
        sr_limit_unit_set = [set() for _ in range(96)]  # 因旋备被限制的机组列表
        for unit_name in rul_df.columns:
            unit_load = rul_df[unit_name].tolist()
            for idx, load in enumerate(unit_load):
                sr_load = get_unit_sr(sr_df, unit_name)  # 旋备容量
                cap = get_unit_cap(q_df, unit_name)  # 额定容量
                hour = idx // 4
                if unit_name in hfu_list[hour]:  # 如果是调频机组就要判断其出力值的合理性
                    max_limit = cap * max_cap - sr_load
                    min_limit = cap * min_cap
                    if load > max_limit:  # 超过最大
                        if sr_load != 0:  # 如果存在旋备
                            sr_limit_unit_set[idx].add(unit_name)
                        trr_df = remove_index(unit_name, idx, trr_df)
                        maxfm_limit_unit_set[idx].add(unit_name)
                        fl_list[idx] += max_limit
                        flag = False
                    if load < min_limit:  # 低于最小
                        index, _ = get_index(unit_name, idx, trr_df)
                        if index < 0:  # 不在爬坡约束里
                            flag = False
                            ramp_rate = get_unit_ramp_rate(rr_df, unit_name)
                            if ramp_rate is not None:  # 存在爬坡曲线
                                if idx > 0:
                                    delta = rul_df.at[idx - 1, unit_name] + ramp_rate
                                    if delta >= min_limit:  # 如果机组可以通过爬坡到最小出力
                                        fl_list[idx] += min_limit
                                        minfm_limit_unit_set[idx].add(unit_name)
                                    else:  # 如果不行，就加入到爬坡约束
                                        trr_df = insert_ramp_rate_unit(trr_df, idx, unit_name, delta)
                                else:
                                    fl_list[idx] += min_limit
                                    minfm_limit_unit_set[idx].add(unit_name)
                            else:
                                fl_list[idx] += min_limit
                                minfm_limit_unit_set[idx].add(unit_name)
                else:
                    if unit_name not in te_set[idx]:  # 不是调频，并且不是试验机组，只考虑旋备
                        max_limit = cap - sr_load
                        if load > max_limit:
                            trr_df = remove_index(unit_name, idx, trr_df)
                            sr_limit_unit_set[idx].add(unit_name)
                            fl_list[idx] += max_limit
                            flag = False
        return flag, minfm_limit_unit_set, maxfm_limit_unit_set, sr_limit_unit_set, fl_list, trr_df

    def get_index(unit_name, idx, trr_df):
        exists = unit_name in trr_df['unit'].values
        if exists:
            try:
                result = trr_df[trr_df['unit'] == unit_name]
                result_row = result.iloc[0]
                index_list = result_row['index']
                data_index = index_list.index(idx)
            except ValueError:
                data_index = -1
                result_row = None
            return data_index, result_row
        else:
            return -1, None

    # 去除指定的数据
    def remove_index(unit_name, idx, trr_df):
        data_index, result_row = get_index(unit_name, idx, trr_df)
        if data_index > 0:
            index_list = result_row['index']
            fixed_load_list = result_row['fixed_load']
            data_index = index_list.index(idx)
            index_list.pop(data_index)  # 移除列表中指定索引的元素
            fixed_load_list.pop(data_index)
        return trr_df

    def getPeakValleyConfig(pvd: pd.DataFrame, date: str):
        month = date.split('-')[1]
        data_map = {}
        if peak_valley_df is not None:
            for _, row in pvd.iterrows():
                month_list = row['月份'].split(',')
                if month in month_list:
                    data_map[0] = row['尖峰'].split(',') if row['尖峰'] is not None else None
                    data_map[1] = row['高峰'].split(',') if row['高峰'] is not None else None
                    data_map[2] = row['平段'].split(',') if row['平段'] is not None else None
                    data_map[3] = row['低谷'].split(',') if row['低谷'] is not None else None
                    return data_map
        return None

    def getPeakValleyPrice(pvd: pd.DataFrame, ppd: pd.DataFrame, sd: pd.DataFrame, date: str):
        data_map = getPeakValleyConfig(pvd, date)
        price_list = ppd['pred_price'].tolist()
        space_list = sd['load'].tolist()
        result_list = []
        if data_map is not None:
            for i in range(4):
                hour_list = data_map[i]
                if hour_list is not None:
                    price_total = 0
                    space_total = 0
                    for hour in hour_list:
                        start_index = get_time_index(hour)
                        if start_index == 95:
                            start_index = -1
                        for j in range(4):
                            price_total += price_list[start_index + 1 + j] * space_list[start_index + 1 + j]
                            space_total += space_list[start_index + 1 + j]
                    result_list.append(round(price_total / space_total, 4))
                else:
                    result_list.append(0)
        return result_list

    @st.cache_data
    def clearing_out(df, pl, fm_quotation, spinning_reserve, startup_shutdown):
        # 开停机数据整理
        unit_start_stop_df = pd.DataFrame()
        for _, value in startup_shutdown.items():
            unit_start_stop_df = pd.concat([unit_start_stop_df, value])
        unit_start_stop_df.reset_index(inplace=True)
        unit_start_stop_df.rename(columns={'index': '机组名称'}, inplace=True)

        # 24时段调频容量
        result = pl[pl['信息披露名称'] == '日前调频需求']
        fm_part = result.iloc[0].tolist()
        fm_part = fm_part[2:26]
        fm_list = [float(x) for x in fm_part]

        # 数据准备
        time_shut_set, time_exp_set, time_exp_load_list, flexible_df = time_shut_exp_unit_and_load(unit_start_stop_df, start_stop_curve_df)  # 每15min的关机机组，试验机组，试验负荷的list
        time_shut_exp_set = [set1.union(set2) for set1, set2 in zip(time_shut_set, time_exp_set)]  # 关机和试验机list合并
        hour_fm_unit_list = get_hour_fm_unit(fm_quotation, fm_list, time_shut_exp_set)  # 每小时参与调频的机组

        load_pred_df = thermal_load(pl)
        space_list = load_pred_df['load'].tolist()  # 火电空间
        remove_unit_set = time_shut_exp_set  # 要去除的机组
        fixed_load_list = time_exp_load_list  # 固定负荷

        turn_ramp_rate_df = pd.DataFrame(columns=['unit', 'index', 'fixed_load'])  # 每迭代一次就会有一个新的
        min_fm_limit_unit_set = [set() for _ in range(96)]  # 因调频被限制最小出力的机组列表
        max_fm_limit_unit_set = [set() for _ in range(96)]  # 因调频被限制最大出力的机组列表
        sr_limit_unit_set = [set() for _ in range(96)]  # 因旋备被限制的机组列表
        clearing_flag = False
        result_price_pred_df = pd.DataFrame()
        result_unit_load_df = pd.DataFrame()
        times = 0
        logger.info('---------------------------------------------')
        logger.info(f'start clearing')

        # 循环出清直到满足边界条件
        while not clearing_flag:  # 不满足出清的边界条件就继续循环
            times += 1
            logger.info(f'clearing times: {times}')
            result_price_pred_df = pd.DataFrame()
            result_unit_load_df = pd.DataFrame()
            now_space_list = copy.deepcopy(space_list)

            # 固定负荷调整
            flexible_load_list = load_list_combine_flexible_df(fixed_load_list, flexible_df, turn_ramp_rate_df)  # 和开停机灵活曲线df以及爬坡df合并
            # 移除的机组调整
            turn_remove_unit_set = remove_set_combine_ramp_rate(remove_unit_set, turn_ramp_rate_df)

            period_list_map = get_diff_sc_period(turn_remove_unit_set)  # 阶段供给曲线
            for period in period_list_map:
                period_range = None
                all_remove_unit_set = None
                for key, value in period.items():  # 字典里只有一组数据
                    period_range = key
                    all_remove_unit_set = value
                start_period = int(period_range.split('-')[0])
                end_period = int(period_range.split('-')[1])
                for i in range(start_period, end_period + 1):  # 遍历负荷
                    now_space_list[i] = space_list[i] - flexible_load_list[i]

                # 主程序部分
                data_df, station_df = data_process(df, all_remove_unit_set)  # 报价表数据处理，从中去除掉部分机组
                supply_df, station_df = supply_curve(data_df, station_df)  # 供给曲线
                price_pred_df = price_pred(now_space_list, supply_df)  # 电价预测
                unit_load_df = load_pred(data_df, station_df, price_pred_df)  # 各机组出力值预测

                # 数据合并
                result_price_pred_df = pd.concat([result_price_pred_df, price_pred_df.iloc[start_period: end_period + 1]], ignore_index=True, sort=False)
                result_unit_load_df = pd.concat([result_unit_load_df, unit_load_df.iloc[start_period: end_period + 1]], ignore_index=True, sort=False)

            # 机组出清数据整合
            result_unit_load_df = result_unit_load_df_process(result_unit_load_df, unit_start_stop_df, df,
                                                              spinning_reserve, flexible_df,
                                                              time_shut_set, time_exp_set,
                                                              min_fm_limit_unit_set, max_fm_limit_unit_set,
                                                              sr_limit_unit_set, turn_ramp_rate_df)

            # 爬坡速率条件限制，获取新一轮迭代的 turn_ramp_rate和 flexible_df
            new_turn_ramp_rate_df, flexible_df = ramp_rate_boundary(result_unit_load_df, ramp_rate_df, flexible_df)
            # 爬坡速率条件限制的整合
            turn_ramp_rate_df = ramp_rate_integrate(turn_ramp_rate_df, new_turn_ramp_rate_df, result_unit_load_df, ramp_rate_df)

            # 其他边界条件判断
            # 爬坡固定负荷转灵活
            clearing_flag, new_minfm_limit_unit_set, new_maxfm_limit_unit_set, new_sr_limit_unit_set, new_fixed_load_list, turn_ramp_rate_df = \
                boundary_condition(result_unit_load_df, hour_fm_unit_list, time_exp_set, fixed_load_list, df, spinning_reserve, ramp_rate_df, turn_ramp_rate_df)

            # 固定负荷重置
            fixed_load_list = new_fixed_load_list

            min_fm_limit_unit_set = [set1.union(set2) for set1, set2 in
                                      zip(min_fm_limit_unit_set, new_minfm_limit_unit_set)]  # 更新数据
            max_fm_limit_unit_set = [set1.union(set2) for set1, set2 in
                                      zip(max_fm_limit_unit_set, new_maxfm_limit_unit_set)]
            sr_limit_unit_set = [set1.union(set2) for set1, set2 in zip(sr_limit_unit_set, new_sr_limit_unit_set)]
            remove_unit_set = [set1.union(set2, set3, set4) for set1, set2, set3, set4 in
                                zip(remove_unit_set, min_fm_limit_unit_set, max_fm_limit_unit_set,
                                    sr_limit_unit_set)]

        logger.info(f'clearing end')
        logger.info('---------------------------------------------')
        return result_price_pred_df, result_unit_load_df

    # 出清结果处理
    result_price_pred_df, result_unit_load_df = clearing_out(df, pl, fm_quotation, spinning_reserve, startup_shutdown)
    price_pred_df = result_price_pred_df
    station_load_df = result_unit_load_df

    st.markdown('电价数据')
    q1, q2, q3 = st.tabs(['曲线', '数据', '峰平谷电价'])
    with q1:
        date = pl['所属日期'].values[0]
        st.line_chart(price_pred_df['pred_price'].tolist())
    with q2:
        price_df = pd.DataFrame()
        for i in range(12):
            price_df['时间' + str(i + 1)] = time_list[8 * i: 8 * i + 8]
            price_df['价格' + str(i + 1)] = price_pred_df['pred_price'].tolist()[8 * i:8 * i + 8]
        st.write(price_df)
    with q3:
        space_df = thermal_load(pl)
        price_avg_list = getPeakValleyPrice(peak_valley_df, price_pred_df, space_df, date)
        price_avg_df = pd.DataFrame(columns=['尖峰平均电价', '高峰平均电价', '平段平均电价', '低谷平均电价'])
        new_row_series = pd.Series(price_avg_list, index=price_avg_df.columns)
        price_avg_df = pd.concat([price_avg_df, new_row_series.to_frame().T], ignore_index=True)
        st.table(price_avg_df)

    unit_df = st.session_state['机组关系表']
    # 求全省各个集团的信息
    st.markdown('各集团出清结果')
    df1 = pd.DataFrame(index=["全省", "赣能", "华能", "国家能源", "国家电投", '大唐'],
                       columns=['装机容量', '开机容量', '发电量', '最高价格', '最低价格', '平均价格', '负荷率',
                                '发电进度'])
    for ji_tuan in group_lists:
        unit_list = unit_df.loc[unit_df['集团'] == ji_tuan, '机组名称'].tolist()
        start_unit = list(set(unit_list).intersection(set(station_load_df.columns.tolist())))
        df1.loc[ji_tuan, '装机容量'] = sum(
            df.loc[df['机组名称'].isin(unit_list), '机组容量(MW)'].astype(float).tolist())
        df1.loc[ji_tuan, '开机容量'] = sum(
            df.loc[df['机组名称'].isin(start_unit), '机组容量(MW)'].astype(float).tolist())
        df1.loc[ji_tuan, '发电量'] = sum(station_load_df.loc[:, start_unit].sum(axis=1).tolist()) / 4
        all_price = 0
        for unit in start_unit:
            all_price += sum(station_load_df[unit] * price_pred_df['pred_price'])
        df1.loc[ji_tuan, '平均价格'] = all_price / df1.loc[ji_tuan, '发电量'] / 4
        df1.loc[ji_tuan, '负荷率'] = df1.loc[ji_tuan, '发电量'] / df1.loc[ji_tuan, '开机容量'] / 24
    df1.loc['全省', ['装机容量', '开机容量', '发电量']] = sum(
        df1.loc['赣能':, ['装机容量', '开机容量', '发电量']].values)
    df1.loc['全省', '平均价格'] = np.mean(df1.loc['赣能':, '平均价格'].values)
    df1.loc['全省', '负荷率'] = df1.loc['全省', '发电量'] / df1.loc['全省', '开机容量'] / 24
    df1.loc['全省', '发电进度'] = 1
    df1['最高价格'] = price_pred_df['pred_price'].max()
    df1['最低价格'] = price_pred_df['pred_price'].min()
    for ji_tuan in ["赣能", "华能", "国家能源", "国家电投", '大唐']:
        df1.loc[ji_tuan, '发电进度'] = df1.loc[ji_tuan, '发电量'] / df1.loc[ji_tuan, '装机容量'] / (
                df1.loc['全省', '发电量'] / df1.loc['全省', '装机容量'])

    # 求各个机组的信息
    tab1, tab2, tab3, tab4, tab5 = st.tabs(group_lists)
    jt_map = {tab1: "赣能", tab2: "华能", tab3: "国家能源", tab4: "国家电投", tab5: '大唐'}
    for ji_tuan in group_lists:
        i = next(key for key, value in jt_map.items() if value == ji_tuan)  # 获取当前集团的key值，也就是tab
        unit_list = []
        origin_unit_list = unit_df.loc[unit_df['集团'] == ji_tuan, '机组名称'].tolist()
        for unit in origin_unit_list:
            unit_cap = df.loc[df['机组名称'] == unit, '机组容量(MW)'].values  # 装机容量为机组容量
            if unit_cap.size == 0 or unit_cap is None:
                continue
            else:
                unit_list.append(unit)
        start_unit = list(set(unit_list).intersection(set(station_load_df.columns.tolist())))  # 每个集团的开机机组
        df2 = pd.DataFrame(index=[ji_tuan] + unit_list,
                           columns=['装机容量', '开机容量', '发电量', '最高价格', '最低价格', '平均价格', '负荷率',
                                    '发电进度'])  # 集团总的和各机组的数据
        df2.loc[ji_tuan] = df1.loc[ji_tuan]
        for unit in unit_list:
            unit_cap = df.loc[df['机组名称'] == unit, '机组容量(MW)'].values  # 装机容量为机组容量
            df2.loc[unit, '装机容量'] = unit_cap[0]
            if unit in start_unit:
                df2.loc[unit, '开机容量'] = df.loc[df['机组名称'] == unit, '机组容量(MW)'].values  # 开机容量为开机机组容量之和
                df2.loc[unit, '发电量'] = station_load_df.loc[:, unit].sum() / 4
                df2.loc[unit, '平均价格'] = sum(
                    station_load_df[unit] * price_pred_df['pred_price']) / station_load_df.loc[:, unit].sum()
                df2.loc[unit, '负荷率'] = df2.loc[unit, '发电量'] / float(df2.loc[unit, '开机容量']) / 24
            else:
                df2.loc[unit, ['开机容量', '发电量', '平均价格', '负荷率', '发电进度']] = 0
        df2['最高价格'] = df2['最高价格'][0]
        df2['最低价格'] = df2['最低价格'][0]
        for unit in start_unit:
            df2.loc[unit, '发电进度'] = df2.loc[unit, '发电量'] / float(df2.loc[unit, '装机容量']) / (
                    df1.loc['全省', '发电量'] / df1.loc['全省', '装机容量'])
        df2[['发电量', '最高价格', '最低价格', '平均价格']] = df2[['发电量', '最高价格', '最低价格', '平均价格']].round(
            2)
        df2[['负荷率', '发电进度']] = df2[['负荷率', '发电进度']].apply(lambda x: x.map('{:.2%}'.format))
        with i:
            df2['装机容量'] = df2['装机容量'].astype(float)
            df2['开机容量'] = df2['开机容量'].astype(float)
            st.write(df2)

    st.markdown('全省出清统计')
    df1[['发电量', '最高价格', '最低价格', '平均价格']] = df1[['发电量', '最高价格', '最低价格', '平均价格']].round(2)
    df1[['负荷率', '发电进度']] = df1[['负荷率', '发电进度']].apply(lambda x: x.map('{:.2%}'.format))
    st.write(df1)

    st.markdown('全省机组出清表')
    c1, c2 = st.tabs(['数据', '曲线'])
    time_list[-1] = '24:00'
    station_load_df['time'] = time_list
    station_load_df.set_index('time', inplace=True)
    with c1:
        st.write(station_load_df)
    with c2:
        stations = station_load_df.columns
        options = st.multiselect('选择机组', stations)
        line_df = station_load_df[options]
        st.line_chart(line_df)
