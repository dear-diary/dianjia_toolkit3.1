import streamlit as st
import os

st.set_page_config(page_title="日志查看", page_icon="📝", layout="wide")
# 去除页脚
st.markdown("""<style>footer {visibility: hidden;}</style>""", unsafe_allow_html=True)


# 读取日志文件
def read_log_file(filepath):
    with open(filepath) as file:
        lines = file.readlines()
    return lines


default_file_name = 'log_info.log'
filename = st.text_input("请输入日志文件名:", value=default_file_name, placeholder=default_file_name)
clear_button = st.button("清空日志")
try:
    current_path = os.path.abspath(os.getcwd())
    file_path = current_path + '/logs/' + filename
    if clear_button:
        # 打开文件并使用 'w' 模式写入，这会清空文件内容
        with open(file_path, 'w'):
            pass
    lines = read_log_file(file_path)
    # 将文件内容展示到页面上
    for line in lines:
        st.text(line)
except Exception as e:
    st.error(str(e))
