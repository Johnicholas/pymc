import unittest

import itertools
from checks import *
from pymc import *
from numpy import array, inf
import numpy

from scipy import integrate
from knownfailure import *


class Domain(object):
    def __init__(self, vals, dtype = None, edges=None, shape = None):
        avals = array(vals)

        if edges is None:
            edges = array(vals[0]), array(vals[-1])
            vals = vals[1:-1]
        if shape is None:
            shape = avals[0].shape


        self.vals = vals
        self.shape = shape

        self.lower, self.upper = edges
        self.dtype = avals.dtype

    def __neg__(self):
        return Domain([-v for v in self.vals], self.dtype, (-self.lower, -self.upper), self.shape)

def product(domains):
    return itertools.product(*[d.vals for d in domains])

R = Domain([-inf, -2.1, -1, -.01, .0, .01, 1, 2.1, inf])
Rplus = Domain([0, .01, .1, .9, .99, 1, 1.5, 2, 100, inf])
Rplusbig = Domain([0, .5, .9, .99, 1, 1.5, 2, 20, inf])
Unit = Domain([0, .001, .1, .5, .75, .99, 1])

Runif = Domain([-1, -.4, 0, .4, 1])
Rdunif = Domain([-10, 0, 10.])
Rplusunif = Domain([0, .5, inf])
Rplusdunif = Domain([2, 10, 100], 'int64')

I = Domain([-1000, -3, -2, -1, 0, 1, 2, 3, 1000], 'int64')

NatSmall = Domain([0, 3, 4, 5, 1000], 'int64')
Nat = Domain([0, 1, 2, 3, 2000], 'int64')
NatBig = Domain([0, 1, 2, 3, 5000, 50000], 'int64')

Bool = Domain([0, 0, 1, 1], 'int64')


Vec2small = Domain([
    [.1, 0.0],
    [-2.3, .1],
    [-2.3, 1.5],
    ],
    edges = ([ -25, -25], [25, 25]))

Vec3small = Domain([
    [.1, 0.0, 0],
    [-2.3, .1,1],
    [-2.3, 1.5, 2],
    ],
    edges = ([ -12, -12, -12], [12, 12,12]))

PdMatrix2 = Domain([
    np.eye(2),
    [[.5, .05],
     [.05, 4.5]]
    ],
    edges = (None,None))

PdMatrix3 = Domain([
    np.eye(3),
    [[.5, .1,0],
     [.1, 1, 0],
     [0, 0, 2.5]]
    ],
    edges = (None,None))




def test_unif():
    checkd(Uniform, Runif, {'lower': -Rplusunif, 'upper': Rplusunif})


def test_discrete_unif():
    checkd(DiscreteUniform, Rdunif,
           {'lower': -Rplusdunif, 'upper': Rplusdunif})


def test_flat():
    checkd(Flat, Runif, {}, checks = (check_dlogp,))


def test_normal():
    checkd(Normal, R, {'mu': R, 'tau': Rplus})


def test_beta():
    # TODO this fails with `Rplus`
    checkd(Beta, Unit, {'alpha': Rplusbig, 'beta': Rplusbig})


def test_exponential():
    checkd(Exponential, Rplus, {'lam': Rplus})


def test_geometric():
    checkd(Geometric, NatBig, {'p': Unit})


def test_negative_binomial():
    checkd(NegativeBinomial, Nat, {'mu': Rplusbig, 'alpha': Rplusbig})


def test_laplace():
    checkd(Laplace, R, {'mu': R, 'b': Rplus})

def test_lognormal():
    checkd(Lognormal, Rplus, {'mu': R, 'tau': Rplus}, (check_dlogp,))

def test_t():
    checkd(T, R, {'nu': Rplus, 'mu': R, 'lam': Rplus})


def test_cauchy():
    checkd(Cauchy, R, {'alpha': R, 'beta': Rplusbig})


def test_gamma():
    checkd(Gamma, Rplus, {'alpha': Rplusbig, 'beta': Rplusbig})


def test_tpos():
    checkd(Tpos, Rplus, {'nu': Rplus, 'mu': R, 'lam': Rplus}, checks=(check_dlogp,))


def test_binomial():
    checkd(Binomial, Nat, {'n': NatSmall, 'p': Unit})


def test_betabin():
    checkd(BetaBin, Nat, {'alpha': Rplus, 'beta': Rplus, 'n': NatSmall})


def test_bernoulli():
    checkd(Bernoulli, Bool, {'p': Unit})


def test_poisson():
    checkd(Poisson, Nat, {'mu': Rplus})


def test_constantdist():
    checkd(ConstantDist, I, {'c': I})


def test_zeroinflatedpoisson():
    checkd(ZeroInflatedPoisson, Nat, {'theta': Rplus, 'z': Bool})

def test_mvnormal2():
    checkd(MvNormal, Vec2small, {'mu': R, 'tau': PdMatrix2}, checks=(check_dlogp, check_int_to_1))

@unittest.skip('Takes too long for travis.')
def test_mvnormal3():
    checkd(MvNormal, Vec3small, {'mu': R, 'tau': PdMatrix3}, checks=(check_dlogp, check_int_to_1))


def test_densitydist():
    def logp(x):
        return -log(2 * .5) - abs(x - .5) / .5

    checkd(DensityDist, R, {}, extra_args={'logp': logp})


def test_addpotential():
    with Model() as model:
        x = Normal('x', 1, 1)
        model.AddPotential(-x ** 2)

        check_dlogp(model, x, R, [])



def test_wishart_initialization():
    with Model() as model:
        x = Wishart('wishart_test', n=3, p=2, V=numpy.eye(2), shape = [2,2])


def test_bound():
    with Model() as model:
        PositiveNormal = Bound(Normal, -.2)
        x = PositiveNormal('x', 1, 1)

        Rplus2 = Domain([-.2, -.19,-.1, 0, .5, 1, inf])

        check_dlogp(model, x, Rplus2, [])

def check_int_to_1(model, value, domain, paramdomains):
    pdf = compilef(exp(model.logp))
    names = map(str, model.vars)

    for a in product(paramdomains):
        a = a + (value.tag.test_value,)
        pt = Point(zip(names, a), model=model)

        bij = DictToVarBijection(value, (), pt)

        pdfx = bij.mapf(pdf)

        area = integrate_nd(pdfx, domain, value.dshape, value.dtype)

        assert_almost_equal(area, 1, err_msg=str(pt))

def integrate_nd(f, domain, shape, dtype):

    if shape == () or shape == (1,):
        if dtype in continuous_types:
            return integrate.quad(f, domain.lower, domain.upper, epsabs=1e-8)[0]
        else:
            return np.sum(map(f, np.arange(domain.lower, domain.upper + 1)))
    elif shape == (2,):
        def f2(a,b):
            return f([a,b])

        return integrate.dblquad(f2,
                domain.lower[0], domain.upper[0],
                lambda a: domain.lower[1], lambda a: domain.upper[1])[0]
    elif shape == (3,):
        def f3(a,b,c):
            return f([a,b,c])

        return integrate.tplquad(f3,
                domain.lower[0], domain.upper[0],
                lambda a: domain.lower[1], lambda a: domain.upper[1],
                lambda a, b: domain.lower[2], lambda a,b: domain.upper[2])[0]
    else:
        raise ValueError("Dont know how to integrate shape: " + str(shape))

def check_dlogp(model, value, domain, paramdomains):
    try:
        from numdifftools import Gradient
    except ImportError:
        return

    domains = paramdomains + [domain]
    bij = DictToArrayBijection(
        ArrayOrdering(model.cont_vars), model.test_point)

    if not model.cont_vars:
        return

    dlogp = bij.mapf(model.dlogpc())
    logp = bij.mapf(model.logpc)

    ndlogp = Gradient(logp)
    names = map(str, model.vars)

    for a in product(domains):
        pt = Point(zip(names, a), model=model)

        pt = bij.map(pt)

        assert_almost_equal(dlogp(pt), ndlogp(pt),
                            decimal=6, err_msg=str(pt))

def build_model(distfam, valuedomain, vardomains, extra_args={}):
    with Model() as m:
        vars = dict((v, Flat(
            v, dtype=dom.dtype, shape=dom.shape, testval=dom.vals[0])) for v, dom in vardomains.iteritems())
        vars.update(extra_args)

        value = distfam(
            'value', shape=valuedomain.shape, **vars)
    return m

def checkd(distfam, valuedomain, vardomains,
           checks=(check_int_to_1, check_dlogp), extra_args={}):

        m = build_model(distfam, valuedomain, vardomains, extra_args=extra_args)

        domains = [vardomains[str(v)] for v in m.vars[:-1]]

        for check in checks:
            check(m, m.named_vars['value'], valuedomain, domains)
