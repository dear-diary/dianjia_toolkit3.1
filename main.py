import streamlit as st


st.set_page_config(page_title="报价小工具", page_icon="👋", layout="wide")

# 去除页脚
st.markdown("""<style>footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

st.title('报价工具 👋')

st.markdown("- 由于电力市场变化快速、需求更迭频繁，传统软件开发模式难以跟上快速迭代的要求。")
st.markdown('- 创新性地提出用python小工具在两者中间，快速响应需求迭代。')
st.markdown('- 在小工具迭代到最终版后，平台开发人员也能迅速进行复现。')
st.divider()  # 下划线

st.markdown(
    """
    ### 👈 请选择你要使用的模块：
    - 数据准备：交易员导入报价数据、事前披露数据后，得到全省各机组报价明细。
    - 模拟出清：根据全省各机组报价，得出全省各机组的发电量、电价、负荷率等概览信息。
    - 日志查看：可以查看当前系统的日志文件，提供运维使用。
"""
)

# "🔥™🎉🚀🌌💣✨🌙🎆🎇💥🤩🤙🌛🤘⬆💡🤪🥂⚡💨🌠🎊🍿😛🔮🤟🌃🍃🍾💫▪🌴🎈🎬🌀🎄😝☔⛽🍂💃😎🍸🎨🥳☀😍
# 🅱🌞😻🌟😜💦💅🦄😋😉👻🍁🤤👯🌻‼🌈👌🎃💛😚🔫🙌👽🍬🌅☁🍷👭☕🌚💁👅🥰🍜😌🎥🕺❕🧡☄💕🍻✅🌸🚬🤓🍹
# ®☺💪😙☘🤠✊🤗🍵🤞😂💯😏📻🎂💗💜🌊❣🌝😘💆🤑🌿🦋😈⛄🚿😊🌹🥴😽💋😭🖤🙆👐⚪💟☃🙈🍭💻🥀🚗🤧🍝💎💓
# 🤝💄💖🔞⁉⏰🕊🎧☠♥🌳🏾🙉⭐💊🍳🌎🙊💸❤🔪😆🌾✈📚💀🏠✌🏃🌵🚨💂🤫🤭😗😄🍒👏🙃🖖💞😅🎅🍄🆓👉💩🔊🤷⌚
# 👸😇🚮💏👳🏽💘💿💉👠🎼🎶🎤👗❄🔐🎵🤒🍰👓🏄🌲🎮🙂📈🚙📍😵🗣❗🌺🙄👄🚘🥺🌍🏡♦💍🌱👑👙☑👾🍩🥶📣🏼🤣
# ☯👵🍫➡🎀😃✋🍞🙇😹🙏👼🐝⚫🎁🍪🔨🌼👆👀😳🌏📖👃🎸👧💇🔒💙😞⛅🏻🍴😼🗿🍗♠🦁✔🤖☮🐢🐎💤😀🍺😁😴📺
# ☹😲👍🎭💚🍆🍋🔵🏁🔴🔔🧐👰☎🏆🤡🐠📲🙋📌🐬✍🔑📱💰🐱💧🎓🍕👟🐣👫🍑😸🍦👁🆗🎯📢🚶🦅🐧💢🏀🚫💑🐟🌽
# 🏊🍟💝💲🐍🍥🐸☝♣👊⚓❌🐯🏈📰🌧👿🐳💷🐺📞🆒🍀🤐🚲🍔👹🙍🌷🙎🐥💵🔝📸⚠❓🎩✂🍼😑⬇⚾🍎💔🐔⚽💭🏌🐷🍍
# ✖🍇📝🍊🐙👋🤔🥊🗽🐑🐘🐰💐🐴♀🐦🍓✏👂🏴👇🆘😡🏉👩💌😺✝🐼🐒🐶👺🖕👬🍉🐻🐾⬅⏬▶👮🍌♂🔸👶🐮👪⛳🐐
# 🎾🐕👴🐨🐊🔹©🎣👦👣👨👈💬⭕📹📷"