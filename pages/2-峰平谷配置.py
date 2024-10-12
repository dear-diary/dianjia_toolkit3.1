import streamlit as st
import pandas as pd

on_editor = False

st.write("峰平谷配置表")
st.markdown("提示：")
st.caption('1、多个数据之间用 "," 隔开 ')
st.caption('2、月份格式为MM（两位数字）, 时间格式为HH\:mm（目前只支持整点时刻）')

try:
    df = pd.read_csv('config/peak_valley_config.csv', encoding='gbk')
except Exception as e:
    df = None

if df is None:  # 没有保存过配置文件
    peak_valley_df = pd.DataFrame(columns=['月份', '尖峰', '高峰', '平段', '低谷'])
    on_editor = True
    st.session_state['peak_valley_df'] = peak_valley_df
else:
    peak_valley_df = df

if on_editor:
    peak_valley_df = st.session_state['peak_valley_df']

peak_valley_df = peak_valley_df.astype(str)
peak_valley_df = peak_valley_df.where(peak_valley_df != 'nan', None)
edit_df = st.data_editor(peak_valley_df, num_rows="dynamic", width=1000, column_config={
    '月份': st.column_config.TextColumn('月份'),
    '尖峰': st.column_config.TextColumn('尖峰'),
    '高峰': st.column_config.TextColumn('高峰'),
    '平段': st.column_config.TextColumn('平段'),
    '低谷': st.column_config.TextColumn('低谷'),
})

save_config_button = st.button("保存配置")
if save_config_button:
    edit_df = edit_df.fillna('')
    edit_df.to_csv('config/peak_valley_config.csv', encoding='gbk', index=False)
    st.write('保存成功!')
