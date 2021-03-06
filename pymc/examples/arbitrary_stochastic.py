from pymc import *
import numpy as np
with Model() as model:
    lam = Exponential('lam', 1)

    failure = np.array([0, 1])
    value = np.array([1, 0])

    def logp(failure, value):
        return sum(failure * log(lam) - lam * value)

    x = DensityDist('x', logp, observed=(failure, value))

if __name__ == "__main__":

    with model:

        start = model.test_point
        h = find_hessian(start)
        step = Metropolis(model.vars, h)
        trace = sample(3000, step, start)
