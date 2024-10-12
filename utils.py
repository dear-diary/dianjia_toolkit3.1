from datetime import datetime


# 获取时间的index
def get_time_index(time):
    if isinstance(time, str):
        time = datetime.strptime(time, '%H:%M')
    base_time = datetime.strptime('00:00', '%H:%M')
    if time.strftime("%H:%M") == '00:00':
        return 95
    time_diff = time - base_time
    total_minutes = time_diff.seconds // 60
    time_slot_number = total_minutes // 15
    return time_slot_number - 1


# 字符串转list
def str_to_list(load_str, time_len):
    if load_str is None:
        return None
    if time_len is None:
        output_list = load_str.split(',')
    else:
        output_list = load_str.split(',')
        if len(output_list) == 1:
            output_list = output_list * time_len
        else:
            if len(output_list) != time_len:
                return None
    output_list = [float(num) for num in output_list]
    return output_list


def merge_lists(old_index_list, old_load_list, new_index_list, new_load_list):
    # 创建旧的index和load的字典
    index_load_dict = dict(zip(old_index_list, old_load_list))

    # 更新字典中的值为新的index和load
    for idx, load in zip(new_index_list, new_load_list):
        index_load_dict[idx] = load

    # 将字典按index排序
    sorted_items = sorted(index_load_dict.items())

    # 提取排序后的index和load
    merged_index_list, merged_load_list = zip(*sorted_items)

    return list(merged_index_list), list(merged_load_list)
