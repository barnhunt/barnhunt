import random

global_random = random.Random()


def random_rats(n=5, min=1, max=5, seed=None):
    """Generate random rat numbers.

    By default returns a tuple of five random integers in the range [1, 5].

    If ``seed`` is not ``None``, it is used to seed the random number
    generator used to generate the rat counts.  For a given seed, the
    returned rat counts will be the same.  (Generally the seed should
    be an integer.  For certain non-integer types, the interpretation of the
    seed value may depend on the setting of PYTHONHASHSEED.)

    If ``seed`` is ``None``, a global random number generator is used.
    In this case, each call will yield different results.

    """
    r = random.Random(seed) if seed is not None else global_random
    return tuple(r.randint(min, max) for _ in range(n))
