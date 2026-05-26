import pytest
from risk.options_vol_surface import OptionsVolatilitySurface, OptionStrike


def test_add_strike_and_gamma_exposure():
    surf = OptionsVolatilitySurface(spot=100.0)
    s = OptionStrike(
        strike=100.0,
        expiry_days=30.0,
        iv=0.20,
        open_interest=1000.0,
        volume=500.0,
        delta=0.5,
        gamma=0.05,
        theta=-0.01,
        vega=0.1,
    )
    surf.add_strike(s)
    assert surf.gamma_exposure() == pytest.approx(50.0)


def test_gamma_pinning():
    surf = OptionsVolatilitySurface(spot=100.0)
    surf.add_strike(
        OptionStrike(
            strike=95.0, expiry_days=30.0, iv=0.20, open_interest=500.0,
            volume=100.0, delta=0.4, gamma=0.03, theta=-0.01, vega=0.1,
        )
    )
    surf.add_strike(
        OptionStrike(
            strike=100.0, expiry_days=30.0, iv=0.20, open_interest=2000.0,
            volume=500.0, delta=0.5, gamma=0.08, theta=-0.01, vega=0.1,
        )
    )
    pinning = surf.gamma_pinning()
    assert pinning == 100.0


def test_detect_unusual_volume():
    surf = OptionsVolatilitySurface(spot=100.0)
    for i in range(10):
        surf.add_strike(
            OptionStrike(
                strike=90.0 + i, expiry_days=30.0, iv=0.20, open_interest=100.0,
                volume=100.0, delta=0.5, gamma=0.05, theta=-0.01, vega=0.1,
            )
        )
    # Add outlier
    surf.add_strike(
        OptionStrike(
            strike=200.0, expiry_days=30.0, iv=0.50, open_interest=100.0,
            volume=10000.0, delta=0.1, gamma=0.01, theta=-0.01, vega=0.1,
        )
    )
    unusual = surf.detect_unusual_volume(threshold_sigma=2.0)
    assert len(unusual) >= 1


def test_svi_fit_insufficient_data():
    surf = OptionsVolatilitySurface(spot=100.0)
    params = surf.svi_fit([100.0], [0.2])
    assert params == {}


def test_svi_fit_sufficient_data():
    surf = OptionsVolatilitySurface(spot=100.0)
    strikes = [90.0, 95.0, 100.0, 105.0, 110.0]
    ivs = [0.22, 0.21, 0.20, 0.21, 0.22]
    params = surf.svi_fit(strikes, ivs)
    assert "a" in params
    assert "b" in params
