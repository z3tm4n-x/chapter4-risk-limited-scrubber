# Chapter 4 rate-burst stress certificate

## Pre-registration

- The rate_cv2=0 sanity case should reproduce the existing Poisson measured-policy seed-sweep within Monte Carlo tolerance.
- The final focused grid is selected from the pilot run before increasing seed_count from 5 to 30.
- The admissible boundary is expected between rate_cv2=0.5 and 0.75 for 300 s and 600 s bursts, between 0.75 and 1.0 for 900 s bursts, and above 1.0 for 1800 s bursts.
- The boundary is expected to move to lower admissible rate_cv2 as burst_duration_seconds decreases.
- The always_tau_min_1s baseline is expected to remain sampled-admissible on the tested finite-correlation grid, but no claim is made for arbitrary unbounded burstiness.
- Failures are interpreted as the boundary between temporally resolvable accumulated single-error control and unresolved burst/instantaneous mechanisms.

## Model

- Type: `piecewise_gamma_rate_multiplier`
- Count model: `poisson_conditional_on_rate_path`
- Hourly mean preservation: normalize multipliers inside each hour so the time average of g(t) over the hour is exactly 1
- Seed count: `30`

## Summary

| Kind | Policy | Scenario | Burst duration, s | requested CV^2 | achieved CV^2 mean | achieved CV^2 max | Target met fraction | p99 util. | Max util. | Pass mean | Sampled p99 pass | All pass |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| baseline_expected | always_tau_min_1s | burst_1800s_cv2_1 | 1800 | 1 | 0.333103141457 | 0.999995760534 | 1 | 0.157445900581 | 0.157624503192 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_1800s_cv2_2 | 1800 | 2 | 0.499761247497 | 0.999999999998 | 1 | 0.181447166202 | 0.182451805893 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_1800s_cv2_4 | 1800 | 4 | 0.666413803644 | 1 | 1 | 0.196748483054 | 0.196770808381 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_1800s_cv2_8 | 1800 | 8 | 0.800429538707 | 1 | 1 | 0.207125140825 | 0.207125140825 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_300s_cv2_0.5 | 300 | 0.5 | 0.44016832606 | 3.68398386951 | 1 | 0.170619318716 | 0.172347671073 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_300s_cv2_0.6 | 300 | 0.6 | 0.524087347576 | 3.98507786126 | 1 | 0.177756302174 | 0.178217692254 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_300s_cv2_0.65 | 300 | 0.65 | 0.565507793059 | 4.97110936522 | 1 | 0.18987099944 | 0.191150984824 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_300s_cv2_0.7 | 300 | 0.7 | 0.606384413489 | 4.49388055131 | 1 | 0.195117258698 | 0.196000969537 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_300s_cv2_0.75 | 300 | 0.75 | 0.646724125019 | 5.64832838172 | 1 | 0.197065977424 | 0.197123651184 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_600s_cv2_0.5 | 600 | 0.5 | 0.384659508481 | 3.43796577081 | 1 | 0.163683776423 | 0.164334931778 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_600s_cv2_0.6 | 600 | 0.6 | 0.453996949169 | 3.50856344568 | 1 | 0.170560105279 | 0.171892183091 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_600s_cv2_0.65 | 600 | 0.65 | 0.488446575269 | 3.70893526064 | 1 | 0.177087568832 | 0.178025232543 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_600s_cv2_0.7 | 600 | 0.7 | 0.522748302902 | 4.05378180603 | 1 | 0.176923978078 | 0.178512797144 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_600s_cv2_0.75 | 600 | 0.75 | 0.555316361014 | 4.16355905797 | 1 | 0.1886552956 | 0.188725992467 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_900s_cv2_0.75 | 900 | 0.75 | 0.47398297239 | 2.91219268236 | 1 | 0.175040759807 | 0.176620276654 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_900s_cv2_0.85 | 900 | 0.85 | 0.525870123946 | 2.89604380636 | 1 | 0.18114211756 | 0.181393277483 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_900s_cv2_0.9 | 900 | 0.9 | 0.551344975125 | 2.91811231981 | 1 | 0.183446630139 | 0.184222435233 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_900s_cv2_0.95 | 900 | 0.95 | 0.57561340398 | 2.97468644575 | 1 | 0.193008413493 | 0.193460501354 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_900s_cv2_1 | 900 | 1 | 0.600016586472 | 2.98950848907 | 1 | 0.191329010056 | 0.192305743089 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | poisson_sanity | 0 | 0 | 0 | 0 | 1 | 0.109625051304 | 0.109625051304 | 157766400 | true | true |
| policy | measured_q16_high1_max3600 | burst_1800s_cv2_1 | 1800 | 1 | 0.333103141457 | 0.999995760534 | 1 | 0.910691024065 | 0.913523092484 | 6309002.86667 | true | true |
| policy | measured_q16_high1_max3600 | burst_1800s_cv2_2 | 1800 | 2 | 0.499761247497 | 0.999999999998 | 0 | 1.2489793072 | 1.28001624138 | 6205723.36667 | false | false |
| policy | measured_q16_high1_max3600 | burst_1800s_cv2_4 | 1800 | 4 | 0.666413803644 | 1 | 0 | 1.51099497026 | 1.52791476803 | 6083624.5 | false | false |
| policy | measured_q16_high1_max3600 | burst_1800s_cv2_8 | 1800 | 8 | 0.800429538707 | 1 | 0 | 1.84490536083 | 1.86140432044 | 5968979.66667 | false | false |
| policy | measured_q16_high1_max3600 | burst_300s_cv2_0.5 | 300 | 0.5 | 0.44016832606 | 3.68398386951 | 1 | 0.967135542104 | 0.971666850253 | 6298777.63333 | true | true |
| policy | measured_q16_high1_max3600 | burst_300s_cv2_0.6 | 300 | 0.6 | 0.524087347576 | 3.98507786126 | 0.833333333333 | 1.01230638604 | 1.01503678915 | 6269917.33333 | false | false |
| policy | measured_q16_high1_max3600 | burst_300s_cv2_0.65 | 300 | 0.65 | 0.565507793059 | 4.97110936522 | 0.166666666667 | 1.05648813739 | 1.06286391983 | 6256527.3 | false | false |
| policy | measured_q16_high1_max3600 | burst_300s_cv2_0.7 | 300 | 0.7 | 0.606384413489 | 4.49388055131 | 0 | 1.05982701915 | 1.06296407969 | 6243212.16667 | false | false |
| policy | measured_q16_high1_max3600 | burst_300s_cv2_0.75 | 300 | 0.75 | 0.646724125019 | 5.64832838172 | 0 | 1.08134972851 | 1.08239541544 | 6227743.7 | false | false |
| policy | measured_q16_high1_max3600 | burst_600s_cv2_0.5 | 600 | 0.5 | 0.384659508481 | 3.43796577081 | 1 | 0.911347081477 | 0.911419699141 | 6313441.5 | true | true |
| policy | measured_q16_high1_max3600 | burst_600s_cv2_0.6 | 600 | 0.6 | 0.453996949169 | 3.50856344568 | 1 | 0.954973931532 | 0.955090118875 | 6286554.56667 | true | true |
| policy | measured_q16_high1_max3600 | burst_600s_cv2_0.65 | 600 | 0.65 | 0.488446575269 | 3.70893526064 | 1 | 0.972542264461 | 0.973820325121 | 6274370 | true | true |
| policy | measured_q16_high1_max3600 | burst_600s_cv2_0.7 | 600 | 0.7 | 0.522748302902 | 4.05378180603 | 1 | 0.997473473498 | 0.999361520483 | 6260181.13333 | true | true |
| policy | measured_q16_high1_max3600 | burst_600s_cv2_0.75 | 600 | 0.75 | 0.555316361014 | 4.16355905797 | 0.533333333333 | 1.03539863846 | 1.03827427834 | 6251206 | false | false |
| policy | measured_q16_high1_max3600 | burst_900s_cv2_0.75 | 900 | 0.75 | 0.47398297239 | 2.91219268236 | 1 | 0.974468904803 | 0.976574814075 | 6279098.26667 | true | true |
| policy | measured_q16_high1_max3600 | burst_900s_cv2_0.85 | 900 | 0.85 | 0.525870123946 | 2.89604380636 | 0.966666666667 | 1.01317229864 | 1.0187928517 | 6259590.3 | false | false |
| policy | measured_q16_high1_max3600 | burst_900s_cv2_0.9 | 900 | 0.9 | 0.551344975125 | 2.91811231981 | 0.566666666667 | 1.02800922398 | 1.03226458315 | 6251392.5 | false | false |
| policy | measured_q16_high1_max3600 | burst_900s_cv2_0.95 | 900 | 0.95 | 0.57561340398 | 2.97468644575 | 0.133333333333 | 1.06067057222 | 1.06967516713 | 6242321.03333 | false | false |
| policy | measured_q16_high1_max3600 | burst_900s_cv2_1 | 900 | 1 | 0.600016586472 | 2.98950848907 | 0 | 1.07922843151 | 1.08149413189 | 6227321.56667 | false | false |
| policy | measured_q16_high1_max3600 | poisson_sanity | 0 | 0 | 0 | 0 | 1 | 0.693503784104 | 0.694970648979 | 6462227.56667 | true | true |

## Interpretation notes

- The measured policy rows are pathwise Monte Carlo over the realized rate-burst and count process.
- The always-tau_min rows are expected-risk baselines over the same sampled rate paths, not pass-by-pass count simulations.
- `requested CV^2` is the gamma-generator dispersion before per-hour mean normalization.
- `achieved CV^2 mean` and `achieved CV^2 max` summarize the normalized multiplier paths actually used in the simulation.
- `rate_cv2=0` is the Poisson sanity case.
- Failures at high requested/achieved CV^2 and short burst duration indicate the boundary of temporally resolvable accumulated-error control, not the instantaneous MBU/MCU mapping channel.
