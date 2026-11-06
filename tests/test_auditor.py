import unittest
from auditor import audit


def trace(steps):
    return {'policy': {'allowed_tools': ['lookup'],
                       'required_arguments': {'lookup': ['query']}}, 'steps': steps}


CALL = {'id': 'c1', 'type': 'tool_call', 'tool': 'lookup', 'arguments': {'query': 'test'}}
RESULT = {'id': 'r1', 'type': 'tool_result', 'call_id': 'c1', 'status': 'success'}


class AuditTests(unittest.TestCase):
    def test_valid_completion(self):
        report = audit(trace([CALL, RESULT, {'id': 'f', 'type': 'final',
                             'claims_completion': True, 'evidence': ['c1']}]))
        self.assertTrue(report['checks_passed'])

    def test_failure_cannot_support_completion(self):
        report = audit(trace([CALL, dict(RESULT, status='error'),
                             {'id': 'f', 'type': 'final', 'evidence': ['c1']}]))
        self.assertEqual(report['findings'][0]['code'], 'INVALID_EVIDENCE')

    def test_future_result_does_not_justify_earlier_claim(self):
        report = audit(trace([CALL, {'id': 'f', 'type': 'final', 'evidence': ['c1']}, RESULT]))
        self.assertEqual(report['finding_count'], 1)

    def test_unapproved_tool_and_missing_result(self):
        report = audit(trace([dict(CALL, tool='delete')]))
        self.assertEqual({f['code'] for f in report['findings']},
                         {'UNAPPROVED_TOOL', 'MISSING_RESULT'})

    def test_missing_argument(self):
        report = audit(trace([dict(CALL, arguments={}), RESULT]))
        self.assertEqual(report['findings'][0]['code'], 'MISSING_ARGUMENT')

    def test_orphan_and_duplicate_results(self):
        report = audit(trace([dict(RESULT, id='r0'), CALL, RESULT, dict(RESULT, id='r2')]))
        self.assertEqual({f['code'] for f in report['findings']},
                         {'ORPHAN_RESULT', 'DUPLICATE_RESULT'})

    def test_empty_evidence(self):
        report = audit(trace([{'id': 'f', 'type': 'final', 'claims_completion': True}]))
        self.assertFalse(report['checks_passed'])

    def test_malformed_traces(self):
        for bad in ({}, trace([CALL, CALL]), trace([{'id': 'x', 'type': 'unknown'}])):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                audit(bad)


if __name__ == '__main__':
    unittest.main()
