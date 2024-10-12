import pandas as pd
import streamlit as st

st.write("机组配置信息")
st.markdown("提示：")
st.caption("1、机组没有设置爬坡速率时，默认该机组爬坡速率无限大")
st.caption("2、机组没有设置开停机曲线时，默认该机组没有该约束")
st.caption("3、开停机曲线数据之间用英文逗号连接，并且单调")

tab1, tab2, tab3 = st.tabs(["集团机组配置", "机组爬坡速率配置", "机组开停机曲线配置"])

# 机组开停机曲线设置
with tab1:
    group_unit_editor = False
    st.write("集团机组配置")
    try:
        df3 = pd.read_excel('config/group_unit.xlsx')
    except Exception as e:
        df3 = None
    if df3 is None:  # 没有保存过配置文件
        group_unit_df = pd.DataFrame(columns=['集团', '机组名称', '编码'])
        group_unit_editor = True
        st.session_state['group_unit_df'] = group_unit_df
    else:
        group_unit_df = df3

    if group_unit_editor:
        group_unit_df = st.session_state['group_unit_df']

    group_unit_df = group_unit_df.astype(str)
    group_unit_df = group_unit_df.where(group_unit_df != 'nan', None)
    edit_df3 = st.data_editor(group_unit_df, num_rows="dynamic", width=1000, column_config={
        '集团': st.column_config.TextColumn('集团'),
        '机组名称': st.column_config.TextColumn('机组名称'),
        '编码': st.column_config.TextColumn('编码'),
    })

    save_config_button3 = st.button("保存集团机组配置", key=3)
    if save_config_button3:
        edit_df3 = edit_df3.fillna('')
        edit_df3.to_excel('config/group_unit.xlsx', index=False)
        st.write('保存成功!')


# 机组爬坡速率设置
with tab2:
    ramp_rate_editor = False
    st.write("机组爬坡速率")
    try:
        df1 = pd.read_csv('config/ramp_rate.csv', encoding='gbk')
    except Exception as e:
        df1 = None
    if df1 is None:  # 没有保存过配置文件
        ramp_rate_df = pd.DataFrame(columns=['机组名称', '爬坡速率（MW/分钟）'])
        ramp_rate_editor = True
        st.session_state['ramp_rate_df'] = ramp_rate_df
    else:
        ramp_rate_df = df1

    if ramp_rate_editor:
        ramp_rate_df = st.session_state['ramp_rate_df']

    ramp_rate_df = ramp_rate_df.astype(str)
    ramp_rate_df = ramp_rate_df.where(ramp_rate_df != 'nan', None)
    edit_df1 = st.data_editor(ramp_rate_df, num_rows="dynamic", width=500, column_config={
        '机组名称': st.column_config.TextColumn('机组名称'),
        '爬坡速率（MW/分钟）': st.column_config.TextColumn('爬坡速率（MW/分钟）')
    })

    save_config_button1 = st.button("保存机组爬坡速率", key=1)
    if save_config_button1:
        edit_df1 = edit_df1.fillna('')
        edit_df1.to_csv('config/ramp_rate.csv', encoding='gbk', index=False)
        st.write('保存成功!')


# 机组开停机曲线设置
with tab3:
    start_stop_curve_editor = False
    st.write("机组开停机曲线")
    try:
        df2 = pd.read_excel('config/start_stop_curve.xlsx')
    except Exception as e:
        df2 = None
    if df2 is None:  # 没有保存过配置文件
        start_stop_curve_df = pd.DataFrame(columns=['机组名称', '最小技术出力', '开机曲线', '停机曲线'])
        start_stop_curve_editor = True
        st.session_state['start_stop_curve_df'] = start_stop_curve_df
    else:
        start_stop_curve_df = df2

    if start_stop_curve_editor:
        start_stop_curve_df = st.session_state['start_stop_curve_df']

    start_stop_curve_df = start_stop_curve_df.astype(str)
    start_stop_curve_df = start_stop_curve_df.where(start_stop_curve_df != 'nan', None)
    edit_df2 = st.data_editor(start_stop_curve_df, num_rows="dynamic", width=1000, column_config={
        '机组名称': st.column_config.TextColumn('机组名称'),
        '最小技术出力': st.column_config.TextColumn('最小技术出力'),
        '开机曲线': st.column_config.TextColumn('开机曲线'),
        '停机曲线': st.column_config.TextColumn('停机曲线'),
    })

    save_config_button2 = st.button("保存机组开停机曲线", key=2)
    if save_config_button2:
        edit_df2 = edit_df2.fillna('')
        edit_df2.to_excel('config/start_stop_curve.xlsx', index=False)
        st.write('保存成功!')
