def binary_search_with_ceiling(arr, target):
    left = 0
    right = len(arr) - 1

    while left <= right:
        mid = (left + right) // 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    if left < len(arr):
        return arr[left]
    else:
        return None
    
arr = [2, 4, 6, 8, 10]

print(binary_search_with_ceiling(arr, 6))
print(binary_search_with_ceiling(arr, 5))
print(binary_search_with_ceiling(arr, 11))