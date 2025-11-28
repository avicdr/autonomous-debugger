"""
Holds module-mapping constants for AST auto-import and name resolution.
No imports from ast_fixer.py (avoid circular import).
"""

# ------------------------------------------------------------------------------
#  FUNCTION → MODULE MAPPING
# ------------------------------------------------------------------------------

FUNC_TO_MODULE = {
    # math
    "sqrt": "math", "sin": "math", "cos": "math", "tan": "math",
    "asin": "math", "acos": "math", "atan": "math", "atan2": "math",
    "log": "math", "log10": "math", "log2": "math", "exp": "math",
    "floor": "math", "ceil": "math", "fabs": "math", "factorial": "math",
    "degrees": "math", "radians": "math", "hypot": "math",
    "fmod": "math", "trunc": "math", "isfinite": "math", "isinf": "math",
    "isnan": "math", "gamma": "math", "lgamma": "math", "comb": "math", "perm": "math",

    "pi": "math", "e": "math", "tau": "math", "inf": "math", "nan": "math",

    # random
    "random": "random", "randint": "random", "uniform": "random",
    "choice": "random", "shuffle": "random", "sample": "random",
    "randrange": "random", "seed": "random",

    # statistics
    "mean": "statistics", "median": "statistics", "mode": "statistics",
    "stdev": "statistics", "variance": "statistics",

    # regex
    "search": "re", "match": "re", "fullmatch": "re", "sub": "re",
    "findall": "re", "finditer": "re", "split": "re", "compile": "re",

    # json
    "loads": "json", "dumps": "json", "load": "json", "dump": "json",

    # datetime
    "datetime": "datetime", "timedelta": "datetime",
    "date": "datetime", "time": "datetime", "timezone": "datetime",

    # itertools
    "product": "itertools", "permutations": "itertools",
    "combinations": "itertools", "cycle": "itertools",
    "repeat": "itertools", "accumulate": "itertools",
    "chain": "itertools", "islice": "itertools",

    # functools
    "reduce": "functools", "lru_cache": "functools", "partial": "functools",

    # collections
    "deque": "collections", "Counter": "collections",
    "defaultdict": "collections",

    # heapq
    "heappush": "heapq", "heappop": "heapq", "heapify": "heapq",
    "nlargest": "heapq", "nsmallest": "heapq",

    # bisect
    "bisect": "bisect", "bisect_left": "bisect", "bisect_right": "bisect",
    "insort": "bisect", "insort_left": "bisect", "insort_right": "bisect",

    # pathlib
    "Path": "pathlib",

    # os.path
    "join": "os.path", "basename": "os.path", "dirname": "os.path",

    # numpy-style (fallback)
    "array": "numpy", "arange": "numpy", "zeros": "numpy",
    "ones": "numpy", "linspace": "numpy", "reshape": "numpy",

    # pandas
    "DataFrame": "pandas", "Series": "pandas", "read_csv": "pandas",
}

# ------------------------------------------------------------------------------
#  PREFERRED MODULES (when multiple exist)
# ------------------------------------------------------------------------------

PREFERRED_MODULES = {
    "sqrt": ["math", "numpy"],
    "sin": ["math", "numpy"],
    "cos": ["math", "numpy"],
    "log": ["math", "numpy"],
    "exp": ["math", "numpy"],

    "mean": ["statistics", "numpy"],
    "median": ["statistics", "numpy"],
    "mode": ["statistics"],

    "random": ["random", "numpy.random"],
    "randint": ["random", "numpy.random"],

    "search": ["re"],
    "sub": ["re"],

    "Path": ["pathlib"],
    "join": ["os.path", "pathlib"],

    "array": ["numpy"],
    "arange": ["numpy"],
}
