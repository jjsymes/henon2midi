def rescale_number_to_range(
    x: float,
    initial_range: tuple[float, float],
    new_range: tuple[float, float],
    clip_value: bool = True,
) -> float:
    if clip_value:
        if x < initial_range[0]:
            x = initial_range[0]
        elif x > initial_range[1]:
            x = initial_range[1]
    else:
        if x < initial_range[0] or x > initial_range[1]:
            raise ValueError(f"x ({x}) is not within initial_range ({initial_range})")

    initial_range_min = initial_range[0]
    initial_range_max = initial_range[1]
    initial_range_size = initial_range_max - initial_range_min

    new_range_min = new_range[0]
    new_range_max = new_range[1]
    new_range_size = new_range_max - new_range_min

    scale_factor = new_range_size / initial_range_size
    x_rescaled = ((x - initial_range_min) * scale_factor) + new_range_min

    return x_rescaled
