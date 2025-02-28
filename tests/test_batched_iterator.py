from moo_sim_interface.utils.batched_iterator import BatchedIterator


def test_batched_iterator_basic_10_mod_3():
    data = list(range(10))  # Example data
    batch_size = 3
    expected_batches = [
        [0, 1, 2],
        [3, 4, 5],
        [6, 7, 8],
        [9]
    ]

    batched_iterator = BatchedIterator(data, batch_size)
    result_batches = [batch for batch in batched_iterator]

    assert result_batches == expected_batches


def test_batched_iterator_empty_data():
    data = []  # Empty data
    batch_size = 3
    expected_batches = []

    batched_iterator = BatchedIterator(data, batch_size)
    result_batches = [batch for batch in batched_iterator]

    assert result_batches == expected_batches


def test_batched_iterator_single_batch_2_mod_3():
    data = list(range(2))  # Example data
    batch_size = 3
    expected_batches = [
        [0, 1]
    ]

    batched_iterator = BatchedIterator(data, batch_size)
    result_batches = [batch for batch in batched_iterator]

    assert result_batches == expected_batches


def test_batched_iterator_exact_6_mod_2():
    data = list(range(6))  # Example data
    batch_size = 2
    expected_batches = [
        [0, 1],
        [2, 3],
        [4, 5]
    ]

    batched_iterator = BatchedIterator(data, batch_size)
    result_batches = [batch for batch in batched_iterator]

    assert result_batches == expected_batches
