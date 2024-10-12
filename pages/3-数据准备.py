import pandas as pd
import streamlit as st
import sys
from constants import Constants
from datetime import time

sys.path.append('..')
from logger import Logger

# 获取日志对象
logger = Logger.get_logger(True, False)

# df1是机组报价表， df2是集团机组对应关系， df3是调频市场报价表， df4是旋转备用表， df5是披露信息表
# 每次点击左边的功能栏时，对应页面的py文件运行一次；支持动态渲染，可实时更新代码
st.set_page_config(page_title="数据准备", page_icon="📈", layout="wide")

st.markdown("""<style>footer {visibility: hidden;}</style>""", unsafe_allow_html=True)  # 去除页脚
st.markdown("提示：")
st.caption('1、请将报价表的核心区域数据整体复制到报价表单中，选中第一个格子进行复制。')
st.caption('2、该页面所有数据准备好之后，需要点击保存数据按钮进行保存。')
st.caption('3、事前披露信息表上传原始文件的excel文件即可。')
st.caption('4、试验负荷可填多个负荷，负荷之间用英文逗号隔开，且保持和试验区间长度的一致性。（只有一个值时，默认为定负荷）')

st.markdown("报价表单")
units_quotation_df = Constants.get_units_quotation_df()
uq_tab1, uq_tab2 = st.tabs(["输入数据", "保存的数据"])
with uq_tab1:
    df1 = st.data_editor(units_quotation_df, num_rows="dynamic")
    df1.iloc[:, 1:] = df1.iloc[:, 1:].applymap(lambda x: float(x) if x else None)  # 字符串数字处理成float
    # 数据去除空行
    df1.dropna(subset=['机组名称'], inplace=True)
    df1.reset_index(drop=True, inplace=True)
    info1 = False
    if not df1['机组名称'].isna().all():  # 如果有机组的数据
        info1 = True
with uq_tab2:
    if '机组报价表' in st.session_state:
        st.write(st.session_state['机组报价表'])
    else:
        st.write(units_quotation_df)


# 检查字符串是否包含中文
def contains_chinese(station):
    for char in str(station):
        if u'\u4e00' <= char <= u'\u9fa5':
            return True
    return False


# 判断数据的准确性
def info_test(info_, df_, df1_):
    if info_:
        try:
            check_cn = [contains_chinese(unit) for unit in df_['机组名称']]
        except Exception:
            st.error("复制格式错误，请重新复制！！", icon="🚨")
            raise
        if not any(check_cn):  # 如果机组数据中全都不包含中文
            try:
                df_['机组名称'] = df1_.set_index('编码')['机组名称'].loc[
                    df_['机组名称'].tolist()].tolist()  # 机组名称替换成中文名称
            except Exception:
                st.error("复制格式错误，请重新复制！！", icon="🚨")
                raise
        return True
    else:
        return False

# 机组集团df
try:
    df2 = pd.read_excel('config/group_unit.xlsx')
    df2 = df2.astype(str)
    df2 = df2.where(df2 != 'nan', None)
except Exception:
    df2 = None
col1, col2 = st.columns([7, 2])

with col1:
    st.markdown("调频市场报价")
    df3 = Constants.get_fm_quotation_df()
    df3 = st.data_editor(df3, num_rows="dynamic", column_config=
    {
        '机组名称': st.column_config.Column('机组名称', disabled=False),
        '机组容量': st.column_config.Column('机组容量', disabled=True),
    })
    # 数据去除空行
    df3.dropna(subset=['机组名称'], inplace=True)
    df3.reset_index(drop=True, inplace=True)
    info2 = False
    if not df3['机组名称'].isna().all():  # df3存在机组名称
        info2 = True
with col2:
    st.markdown("旋转备用容量")
    sr_df = Constants.get_spinning_reserve_df()
    df4 = st.data_editor(sr_df, num_rows='dynamic', column_config={
        '机组名称': st.column_config.TextColumn('机组名称'),
        '机组容量': st.column_config.NumberColumn('机组容量'),
        '旋备容量': st.column_config.NumberColumn('旋备容量')
    })
    # 数据去除空行
    df4.dropna(subset=['机组名称'], inplace=True)
    df4.reset_index(drop=True, inplace=True)
    info3 = False
    if not df4['机组名称'].isna().all():  # df3存在机组名称
        info3 = True

if info1:
    info_test(info1, df1, df2)
if info2:
    info_test(info2, df3, df2)
if info3:
    info_test(info3, df4, df2)

# 事前披露表
df5 = None
disclosure_information_file = st.sidebar.file_uploader(label='请上传事前披露信息表', type=['xlsx', 'xls'])
if disclosure_information_file is not None:
    df5 = pd.read_excel(disclosure_information_file)

# 开停机及试验机组
# 获取报价中全都是1500或空的机组名称，这些机组为停机机组
st.markdown("开停机及试验机组修正")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["赣能", "华能", "国家能源", "国家电投", '大唐'])
output_columns = [col for col in df1.columns if '报价' in col]  # 获取全部报价列名
out_lists = df1[output_columns].values.tolist()
is_binary = [idx for idx, sublist in enumerate(out_lists) if
             all(num in [0, 1500] or pd.isna(num) for num in sublist)]
is_binary_unit = df1.loc[is_binary, '机组名称'].values


def time_column_format(column_name):
    return st.column_config.TimeColumn(
        column_name,
        min_value=time(0, 0, 0),
        max_value=time(23, 45, 0),
        step=60,
        format="HH:mm:ss"
    )


jt_map = {tab1: "赣能", tab2: "华能", tab3: "国家能源", tab4: "国家电投", tab5: '大唐'}
jt_kj_dict = {}  #
for ji_tuan in ["赣能", "华能", "国家能源", "国家电投", '大唐']:
    i = next(key for key, value in jt_map.items() if value == ji_tuan)  # 获取集团的所在tab
    jt_df_dict = {}  # 集团字典，存放集团的df
    with i:
        # 构建开停机表头，index为机组名称
        jt_df_dict[ji_tuan] = pd.DataFrame(index=df2.loc[df2['集团'] == ji_tuan, '机组名称'].values.tolist(),
                                           columns=['机组容量(MW)', '开机状态', '开机时间', '停机时间', '试验状态',
                                                    '试验开始时间1', '试验结束时间1', '试验负荷1', '试验开始时间2',
                                                    '试验结束时间2', '试验负荷2',
                                                    '试验开始时间3', '试验结束时间3', '试验负荷3'])
        # 数据类型处理-datetime
        for key1 in ['开机时间', '停机时间', '试验开始时间1', '试验结束时间1', '试验开始时间2', '试验结束时间2',
                     '试验开始时间3', '试验结束时间3']:
            jt_df_dict[ji_tuan][key1] = pd.to_datetime(jt_df_dict[ji_tuan][key1])
        # 数据类型处理-float
        for key2 in ['机组容量(MW)']:
            jt_df_dict[ji_tuan][key2] = jt_df_dict[ji_tuan][key2].astype(float)
        # 数据类型处理-bool
        for key3 in ['开机状态', '试验状态']:
            jt_df_dict[ji_tuan][key3] = False
        # 数据类型处理-str
        for key4 in ['试验负荷1', '试验负荷2', '试验负荷3']:
            jt_df_dict[ji_tuan][key2] = jt_df_dict[ji_tuan][key4].astype(str)
        # 如果机组报价表有数据
        if info1:
            for unit in df1['机组名称']:
                if unit in jt_df_dict[ji_tuan].index.tolist():
                    jt_df_dict[ji_tuan].loc[unit, '机组容量(MW)'] = \
                        df1.loc[df1['机组名称'] == unit, '机组容量(MW)'].tolist()[0]
            jt_df_dict[ji_tuan]['开机状态'] = True
            jt_df_dict[ji_tuan].loc[
                [value for value in is_binary_unit if
                 value in jt_df_dict[ji_tuan].index.values], '开机状态'] = False  # 判断机组是不是在全部为1500的里面
            jt_df_dict[ji_tuan]['试验状态'] = False

        jt_kj_dict[ji_tuan] = st.data_editor(
            jt_df_dict[ji_tuan],
            column_config=
            {
                '机组容量(MW)': st.column_config.Column(
                    '机组容量(MW)',
                    disabled=True
                ),
                '开机时间': time_column_format('开机时间'),
                '停机时间': time_column_format('停机时间'),
                '试验开始时间1': time_column_format('试验开始时间1'),
                '试验结束时间1': time_column_format('试验结束时间1'),
                '试验开始时间2': time_column_format('试验开始时间2'),
                '试验结束时间2': time_column_format('试验结束时间2'),
                '试验开始时间3': time_column_format('试验开始时间3'),
                '试验结束时间3': time_column_format('试验结束时间3')
            }
        )

st.sidebar.markdown("<hr>", unsafe_allow_html=True)
st.sidebar.markdown("点击保存数据后，进入模拟出清")
if st.sidebar.button('保存数据', type='primary'):
    # 报价表数据规整
    for i in range(2, len(df1.columns), 2):
        df1.iloc[:, i:i+2] = df1.iloc[:, i:i+2].apply(
            lambda row: [None, None] if all(row[0:2] == 0) else row, axis=1)
    st.session_state['机组报价表'] = df1
    st.session_state['机组关系表'] = df2
    st.session_state['调频报价表'] = df3
    st.session_state['旋转备用'] = df4
    st.session_state['披露表'] = df5
    st.session_state['停机机组'] = is_binary_unit
    st.session_state['开停机'] = jt_kj_dict
