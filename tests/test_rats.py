from barnhunt.rats import random_rats


class TestRandomRats(object):
    def check_rats(self, rats):
        assert len(rats) == 5
        for nr in rats:
            assert 1 <= nr <= 5

    def test(self):
        rats = random_rats()
        self.check_rats(rats)
        assert any(random_rats() != rats for _ in range(100))

    def test_min_arg(self):
        assert random_rats(min=5) == (5, 5, 5, 5, 5)

    def test_max_arg(self):
        assert random_rats(max=1) == (1, 1, 1, 1, 1)

    def test_seed(self):
        rats1 = random_rats(seed=1)
        self.check_rats(rats1)

        assert any(random_rats(seed=seed) != rats1
                   for seed in range(2, 100))

        assert random_rats(seed=1) == rats1
