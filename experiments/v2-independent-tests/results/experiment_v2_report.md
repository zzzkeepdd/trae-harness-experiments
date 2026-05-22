# Harness A/B v2: Independent Test-Driven Comparison

## Method
Each task's code from Group A (no-harness) and Group B (harness) is tested against
the **same independent test suite**. Tests are written based on task acceptance criteria,
not on Harness process artifacts.

## Metrics
| Metric | Group A | Group B |
|--------|---------|---------|
| Total Pass | 72 | 77 |
| Total Fail | 6 | 1 |
| Pass Rate | 92% | 99% |

## Failing Test Details

### Group A (no-harness)
- **l1-1-string-utils**: FAIL word_count: normal: got {}, expected {'hello': 2, 'world': 1}, FAIL word_count: single: got {}, expected {'test': 1}, FAIL word_count: case insensitive: got {}, expected {'hello': 3}
- **l3-1-task-queue**: FAIL timeout: returns error dict: got False, expected True
- **l3-2-session-manager**: FAIL logout: token invalidated: got TokenPayload(user_id='ccc2fa7c-3316-42e2-b46a-31c553e55b55', username='alice', roles=['user'], exp=1779459653.8482964), expected None, FAIL re-login: old token invalid: got TokenPayload(user_id='45c3501a-3d93-4ae5-932a-8c6c4a6527d7', username='bob', roles=['user'], exp=1779459653.9076154), expected None

### Group B (harness)
- **l1-1-string-utils**: FAIL is_palindrome: empty string: got False

## Conclusion
The difference in pass rates directly measures the quality gap between
direct model output and debate-refined output.
