import numpy as np

def is_subarray_found(arr1, arr2):
    arr1 = np.array(arr1)
    arr2 = np.array(arr2)
    
    len1 = arr1.size
    len2 = arr2.size
    
    # 如果第二个数组长度大于第一个数组长度，直接返回False
    if len2 > len1:
        return False
    
    # 创建一个滑动窗口视图
    for i in range(len1 - len2 + 1):
        if np.array_equal(arr1[i:i+len2], arr2):
            return True
    
    return False

# 示例数组
arr1 = [True, True, False, False, False, True]
arr2 = [False, False, False, False]

# 判断是否找到
result = is_subarray_found(arr1, arr2)
print(result)  # 输出: True
