from multiprocessing.pool import ThreadPool


class ParallelUnorderedStarmap(object):
    """Multi-threaded version of itertools.starmap.
    """
    def __init__(self, processes=None, timeout=3600):
        self.pool = ThreadPool(processes)
        self.timeout = timeout

    def __call__(self, f, args):
        # Iterating without a timeout make things fairly unresponsive
        # to SIGINT.
        return self._iter_with_timeout(
            self.pool.imap_unordered(lambda args: f(*args), args))

    def _iter_with_timeout(self, imap_iter):
        try:
            while True:
                yield imap_iter.next(self.timeout)
        except StopIteration:
            pass
