"""Tests for the new Coder-output safety gates:
  - injection-pattern lint (Coder must not INTRODUCE eval/exec/__import__/etc.)
  - scope_guard mass-drop (declared removal intent doesn't waive a big API drop)
"""
from app.services.coder_orchestrator import _lint_coder_output
from app.agents.coder_agent import CoderOutput
from app.services import scope_guard as sg


def _co(path, new_content, rationale="fix"):
    return CoderOutput(
        files=[{"path": path, "new_content": new_content, "rationale": rationale}],
        summary="a sufficiently long summary describing the change in detail",
    )


class TestInjectionLint:
    def test_introduced_eval_is_flagged(self):
        co = _co("h.py", "def f(x):\n    return eval(x)\n")
        issues = _lint_coder_output(co, {"h.py": "def f(x):\n    return int(x)\n"}, ["h.py"])
        assert any("dynamic-execution" in i for i in issues)

    def test_preexisting_eval_not_flagged(self):
        # eval present in BOTH original and new -> not this patch's fault
        co = _co("h.py", "def f(x):\n    return eval(x)  # kept\n")
        issues = _lint_coder_output(co, {"h.py": "def f(x):\n    return eval(x)\n"}, ["h.py"])
        assert not any("dynamic-execution" in i for i in issues)

    def test_introduced_shell_true_is_flagged(self):
        co = _co("h.py", "import subprocess\nsubprocess.run(cmd, shell=True)\n")
        issues = _lint_coder_output(co, {"h.py": "import subprocess\n"}, ["h.py"])
        assert any("dynamic-execution" in i for i in issues)

    def test_method_named_eval_not_flagged(self):
        # ast.literal_eval( must NOT match (negative lookbehind on `.`)
        co = _co("h.py", "import ast\nv = ast.literal_eval(s)\n")
        issues = _lint_coder_output(co, {"h.py": "v = s\n"}, ["h.py"])
        assert not any("dynamic-execution" in i for i in issues)


class TestScopeGuardMassDrop:
    def test_small_declared_cleanup_allowed(self):
        original = "def keep(): pass\ndef _dupe(): pass\n"
        new = "def keep(): pass\n"
        # declared removal intent on a 1-of-2 drop -> allowed
        assert sg.check_file("x.py", original, new, rationale="remove the duplicate _dupe") == []

    def test_mass_drop_blocked_even_with_intent(self):
        # 10 defs, drop 9, with a "refactor" rationale -> STILL blocked
        original = "\n".join(f"def fn{i}(): pass" for i in range(10))
        new = "def fn0(): pass"
        issues = sg.check_file("big.py", original, new, rationale="refactor and consolidate")
        assert issues and "DROPS 9" in issues[0]

    def test_mass_drop_without_intent_blocked(self):
        original = "\n".join(f"def fn{i}(): pass" for i in range(10))
        new = "def fn0(): pass"
        assert sg.check_file("big.py", original, new) != []
