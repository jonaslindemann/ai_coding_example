# Running the tests

From this directory, run:

```bash
pytest -q
```

The intentionally broken starting point should fail at least the
`test_right_boundary_is_100_degrees` test.

After making the minimal fix, run the tests again.

The final result should be:

```text
3 passed
```

To inspect the temperature field visually, run:

```bash
python debug_temperature.py --plot
```

The plot is optional and is never opened by the tests.
