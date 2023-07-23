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
    assert data_point_generator.current_data_point == (starting_radius, starting_radius)


def test_radially_expanding_henon_mappings_generator_changing_orbit():
    iterations_per_orbit = 3
    initial_radius = 0.0
    radial_step = 0.2
    data_point_generator = RadiallyExpandingHenonMappingsGenerator(
        a_parameter=1.333,
        iterations_per_orbit=iterations_per_orbit,
        starting_radius=initial_radius,
        radial_step=radial_step,
    )

    assert data_point_generator.current_radius == initial_radius

    for _ in range(iterations_per_orbit):
        data_point_generator.generate_next_data_point()

    assert data_point_generator.current_radius == initial_radius

    data_point_generator.generate_next_data_point()

    assert data_point_generator.current_radius == initial_radius + radial_step


def test_radially_expanding_henon_mappings_generator_state():
    iterations_per_orbit = 3
    initial_radius = 0.0
    radial_step = 0.2
    data_point_generator = RadiallyExpandingHenonMappingsGenerator(
        a_parameter=1.333,
        iterations_per_orbit=iterations_per_orbit,
        starting_radius=initial_radius,
        radial_step=radial_step,
    )
    assert data_point_generator.current_iteration == 0
    assert data_point_generator.current_orbital_iteration == 0
    assert data_point_generator.current_radius == initial_radius

    destination_radius = 1.0
    number_of_orbits = int(destination_radius / radial_step)
    number_of_iterations = number_of_orbits * iterations_per_orbit
    for _ in range(number_of_iterations):
        data_point_generator.generate_next_data_point()

    assert data_point_generator.current_iteration == number_of_iterations
    assert data_point_generator.current_orbital_iteration == number_of_orbits
    assert data_point_generator.current_radius == destination_radius - radial_step

    data_point = data_point_generator.generate_next_data_point()

    assert data_point_generator.current_iteration == number_of_iterations + 1
    assert data_point_generator.current_orbital_iteration == number_of_orbits + 1
    assert data_point_generator.current_radius == destination_radius
    assert data_point_generator.current_data_point == data_point


def test_radially_expanding_henon_mappings_generator_resets_when_generator_ends_iteration(
    mocker,
):
    iterations_per_orbit = 200
    initial_radius = 1.0
    radial_step = 0.2
    data_point_generator = RadiallyExpandingHenonMappingsGenerator(
        a_parameter=1.333,
        iterations_per_orbit=iterations_per_orbit,
        starting_radius=initial_radius,
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
    initial_radius = 1.0
    radial_step = 0.2
    data_point_generator = RadiallyExpandingHenonMappingsGenerator(
        a_parameter=1.333,
        iterations_per_orbit=iterations_per_orbit,
        starting_radius=initial_radius,
        radial_step=radial_step,
    )

    for _ in range(1000):
        data_point_generator.generate_next_data_point()

    assert data_point_generator.current_iteration == 1000
    assert data_point_generator.current_orbital_iteration > 5
    assert data_point_generator.current_radius == 1.0
