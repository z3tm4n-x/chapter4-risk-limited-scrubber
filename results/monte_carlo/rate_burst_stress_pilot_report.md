# Chapter 4 rate-burst stress certificate

## Pre-registration

- The rate_cv2=0 sanity case should reproduce the existing Poisson measured-policy seed-sweep within Monte Carlo tolerance.
- The measured_q16_high1_max3600 policy is expected to remain sampled-admissible for sufficiently weak finite-correlation bursts.
- The boundary is expected to move to lower admissible rate_cv2 as burst_duration_seconds decreases.
- The always_tau_min_1s baseline is expected to remain sampled-admissible on the tested finite-correlation grid, but no claim is made for arbitrary unbounded burstiness.
- Failures are interpreted as the boundary between temporally resolvable accumulated single-error control and unresolved burst/instantaneous mechanisms.

## Model

- Type: `piecewise_gamma_rate_multiplier`
- Count model: `poisson_conditional_on_rate_path`
- Hourly mean preservation: normalize multipliers inside each hour so the time average of g(t) over the hour is exactly 1
- Seed count: `5`

## Summary

| Kind | Policy | Scenario | Burst duration, s | rate CV^2 | Target met fraction | p99 util. | Max util. | Pass mean | Sampled p99 pass | All pass |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| baseline_expected | always_tau_min_1s | burst_1800s_cv2_0.1 | 1800 | 0.1 | 1 | 0.119368131707 | 0.1194789885 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_1800s_cv2_0.25 | 1800 | 0.25 | 1 | 0.132359932029 | 0.132643232723 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_1800s_cv2_0.5 | 1800 | 0.5 | 1 | 0.137256107073 | 0.137262265784 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_1800s_cv2_0.75 | 1800 | 0.75 | 1 | 0.145995317623 | 0.146115412483 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_1800s_cv2_1 | 1800 | 1 | 1 | 0.146883711649 | 0.146962235211 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_300s_cv2_0.1 | 300 | 0.1 | 1 | 0.120803111311 | 0.120806960505 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_300s_cv2_0.25 | 300 | 0.25 | 1 | 0.138172985135 | 0.138327209517 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_300s_cv2_0.5 | 300 | 0.5 | 1 | 0.162768566344 | 0.162801669414 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_300s_cv2_0.75 | 300 | 0.75 | 1 | 0.187599718239 | 0.187680294705 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_300s_cv2_1 | 300 | 1 | 1 | 0.219924481436 | 0.220000695481 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_600s_cv2_0.1 | 600 | 0.1 | 1 | 0.120924745848 | 0.120941682303 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_600s_cv2_0.25 | 600 | 0.25 | 1 | 0.133830324219 | 0.133900636167 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_600s_cv2_0.5 | 600 | 0.5 | 1 | 0.15378095446 | 0.154031921923 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_600s_cv2_0.75 | 600 | 0.75 | 1 | 0.181261635041 | 0.181297047628 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_600s_cv2_1 | 600 | 1 | 1 | 0.189903332672 | 0.189906412027 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_900s_cv2_0.1 | 900 | 0.1 | 1 | 0.119185679901 | 0.119209544905 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_900s_cv2_0.25 | 900 | 0.25 | 1 | 0.130320628933 | 0.130352962164 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_900s_cv2_0.5 | 900 | 0.5 | 1 | 0.158519055928 | 0.158740769515 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_900s_cv2_0.75 | 900 | 0.75 | 1 | 0.183067676968 | 0.183606564158 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | burst_900s_cv2_1 | 900 | 1 | 1 | 0.191973942547 | 0.192305743089 | 157766400 | true | true |
| baseline_expected | always_tau_min_1s | poisson_sanity | 0 | 0 | 1 | 0.109625051304 | 0.109625051304 | 157766400 | true | true |
| policy | measured_q16_high1_max3600 | burst_1800s_cv2_0.1 | 1800 | 0.1 | 1 | 0.714660401388 | 0.714952873031 | 6436614.8 | true | true |
| policy | measured_q16_high1_max3600 | burst_1800s_cv2_0.25 | 1800 | 0.25 | 1 | 0.748765399501 | 0.748807467309 | 6417428.6 | true | true |
| policy | measured_q16_high1_max3600 | burst_1800s_cv2_0.5 | 1800 | 0.5 | 1 | 0.812636448773 | 0.813461781754 | 6374698.4 | true | true |
| policy | measured_q16_high1_max3600 | burst_1800s_cv2_0.75 | 1800 | 0.75 | 1 | 0.851182557859 | 0.851322784003 | 6352461.2 | true | true |
| policy | measured_q16_high1_max3600 | burst_1800s_cv2_1 | 1800 | 1 | 1 | 0.892387005348 | 0.892589331359 | 6308740 | true | true |
| policy | measured_q16_high1_max3600 | burst_300s_cv2_0.1 | 300 | 0.1 | 1 | 0.741495674723 | 0.741746078531 | 6415635.6 | true | true |
| policy | measured_q16_high1_max3600 | burst_300s_cv2_0.25 | 300 | 0.25 | 1 | 0.816130030187 | 0.816316330695 | 6379881.6 | true | true |
| policy | measured_q16_high1_max3600 | burst_300s_cv2_0.5 | 300 | 0.5 | 1 | 0.95628203917 | 0.956842943671 | 6311772.8 | true | true |
| policy | measured_q16_high1_max3600 | burst_300s_cv2_0.75 | 300 | 0.75 | 0 | 1.07461486727 | 1.07463289647 | 6222487.4 | false | false |
| policy | measured_q16_high1_max3600 | burst_300s_cv2_1 | 300 | 1 | 0 | 1.20567221937 | 1.20579441652 | 6166627.2 | false | false |
| policy | measured_q16_high1_max3600 | burst_600s_cv2_0.1 | 600 | 0.1 | 1 | 0.728751126319 | 0.728925407446 | 6435340.8 | true | true |
| policy | measured_q16_high1_max3600 | burst_600s_cv2_0.25 | 600 | 0.25 | 1 | 0.803691974925 | 0.804046546824 | 6381425 | true | true |
| policy | measured_q16_high1_max3600 | burst_600s_cv2_0.5 | 600 | 0.5 | 1 | 0.912970193376 | 0.913422923385 | 6318079.8 | true | true |
| policy | measured_q16_high1_max3600 | burst_600s_cv2_0.75 | 600 | 0.75 | 0.4 | 1.01150710153 | 1.01168138275 | 6251736 | false | false |
| policy | measured_q16_high1_max3600 | burst_600s_cv2_1 | 600 | 1 | 0 | 1.11310296786 | 1.11359576393 | 6187481.2 | false | false |
| policy | measured_q16_high1_max3600 | burst_900s_cv2_0.1 | 900 | 0.1 | 1 | 0.728763145751 | 0.729025569009 | 6431915.8 | true | true |
| policy | measured_q16_high1_max3600 | burst_900s_cv2_0.25 | 900 | 0.25 | 1 | 0.785087973491 | 0.785216180263 | 6391834.6 | true | true |
| policy | measured_q16_high1_max3600 | burst_900s_cv2_0.5 | 900 | 0.5 | 1 | 0.88629518133 | 0.886980286167 | 6336297.4 | true | true |
| policy | measured_q16_high1_max3600 | burst_900s_cv2_0.75 | 900 | 0.75 | 1 | 0.962241655276 | 0.962702398157 | 6268606.4 | true | true |
| policy | measured_q16_high1_max3600 | burst_900s_cv2_1 | 900 | 1 | 0 | 1.04425391218 | 1.04443420278 | 6224348 | false | false |
| policy | measured_q16_high1_max3600 | poisson_sanity | 0 | 0 | 1 | 0.684617957322 | 0.684704096252 | 6457828.6 | true | true |

## Interpretation notes

- The measured policy rows are pathwise Monte Carlo over the realized rate-burst and count process.
- The always-tau_min rows are expected-risk baselines over the same sampled rate paths, not pass-by-pass count simulations.
- `rate_cv2=0` is the Poisson sanity case.
- Failures at high `rate_cv2` and short burst duration indicate the boundary of temporally resolvable accumulated-error control, not the instantaneous MBU/MCU mapping channel.
