import pytest

from henon2midi.henon_equations import RadiallyExpandingHenonMappingsGenerator


@pytest.mark.parametrize(
    ("starting_radius"),
    [
        (0.0),
        (0.1),
        (0.5),
        (1.0),
    ],
)
def test_radially_expanding_henon_mappings_generator_initial_data_point(
    starting_radius,
):
    data_point_generator = RadiallyExpandingHenonMappingsGenerator(
        a_parameter=1.333,
        starting_radius=starting_radius,
    )
    assert data_point_generator.get_current_data_point() == (
        starting_radius,
        starting_radius,
    )


def test_radially_expanding_henon_mappings_generator_changing_orbit():
    iterations_per_orbit = 3
    starting_radius = 0.0
    radial_step = 0.2
    data_point_generator = RadiallyExpandingHenonMappingsGenerator(
        a_parameter=1.333,
        iterations_per_orbit=iterations_per_orbit,
        starting_radius=starting_radius,
        radial_step=radial_step,
    )

    assert data_point_generator.get_current_radius() == starting_radius

    for _ in range(iterations_per_orbit):
        data_point_generator.generate_next_data_point()

    assert data_point_generator.get_current_radius() == starting_radius

    data_point_generator.generate_next_data_point()

    assert data_point_generator.get_current_radius() == starting_radius + radial_step


def test_radially_expanding_henon_mappings_generator_state():
    iterations_per_orbit = 3
    starting_radius = 0.0
    radial_step = 0.2
    data_point_generator = RadiallyExpandingHenonMappingsGenerator(
        a_parameter=1.333,
        iterations_per_orbit=iterations_per_orbit,
        starting_radius=starting_radius,
        radial_step=radial_step,
    )
    assert data_point_generator.get_current_iteration() == 0
    assert data_point_generator.get_current_orbital_iteration() == 0
    assert data_point_generator.get_current_radius() == starting_radius

    end_radius = 1.0
    number_of_orbits = int(end_radius / radial_step) + 1
    number_of_iterations = number_of_orbits * iterations_per_orbit
    for _ in range(number_of_iterations):
        data_point_generator.generate_next_data_point()

    assert data_point_generator.get_current_iteration() == number_of_iterations
    assert data_point_generator.get_current_orbital_iteration() == number_of_orbits
    assert data_point_generator.get_current_radius() == end_radius

    data_point = data_point_generator.generate_next_data_point()

    assert data_point_generator.get_current_iteration() == 1
    assert data_point_generator.get_current_orbital_iteration() == 1
    assert data_point_generator.get_current_radius() == starting_radius
    assert data_point_generator.get_current_data_point() == data_point
    assert data_point_generator.get_times_reset() == 1


def test_radially_expanding_henon_mappings_generator_resets_when_generator_ends_iteration(
    mocker,
):
    iterations_per_orbit = 200
    starting_radius = 1.0
    radial_step = 0.2
    data_point_generator = RadiallyExpandingHenonMappingsGenerator(
        a_parameter=1.333,
        iterations_per_orbit=iterations_per_orbit,
        starting_radius=starting_radius,
        radial_step=radial_step,
    )

    restart_data_point_generator_method = mocker.patch.object(
        data_point_generator, "restart_data_point_generator"
    )

    with pytest.raises(StopIteration):
        for _ in range(1000):
            data_point_generator.generate_next_data_point()

    assert restart_data_point_generator_method.call_count == 1


def test_radially_expanding_henon_mappings_generator_does_not_raise_exception_when_generator_ends_iteration():
    iterations_per_orbit = 200
    starting_radius = 1.0
    radial_step = 0.2
    data_point_generator = RadiallyExpandingHenonMappingsGenerator(
        a_parameter=1.333,
        iterations_per_orbit=iterations_per_orbit,
        starting_radius=starting_radius,
        radial_step=radial_step,
    )

    for _ in range(1000):
        data_point_generator.generate_next_data_point()

    assert data_point_generator.get_current_radius() == 1.0


def test_radially_expanding_henon_mappings_generator_is_iterable():
    iterations_per_orbit = 5
    starting_radius = 0.0
    radial_step = 0.2
    data_point_generator = RadiallyExpandingHenonMappingsGenerator(
        a_parameter=1.333,
        iterations_per_orbit=iterations_per_orbit,
        starting_radius=starting_radius,
        radial_step=radial_step,
    )
    end_radius = 1.0
    number_of_orbits = int(end_radius / radial_step) + 1
    expected_number_of_iterations = number_of_orbits * iterations_per_orbit

    assert iter(data_point_generator) == data_point_generator
    assert (len(list(data_point_generator))) == expected_number_of_iterations
