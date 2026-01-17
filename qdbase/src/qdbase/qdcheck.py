"""
qdbase.qdcheck - Standardized check/validation framework for QuickDev

Provides a consistent API for validating service configurations with three modes:
- VALIDATE: Check configuration and report issues
- TEST: Validate + run functional tests
- CORRECT: Validate + auto-fix issues where possible

Each service package (qdflask, qdimages, qdcomments) implements a CheckRunner
subclass with its specific checks.

Example usage:
    from qdbase.qdcheck import CheckRunner, CheckResult, CheckStatus, CheckMode

    class MyServiceChecker(CheckRunner):
        service_name = "myservice"
        service_display_name = "My Service"
        config_filename = "myservice.yaml"

        def _run_checks(self):
            self._check_config_exists()
            self._check_database()

        def _check_config_exists(self):
            # ... implementation
            self.add_result(CheckResult(
                name="Config File",
                status=CheckStatus.PASS,
                message="Configuration loaded"
            ))
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any
from enum import Enum
import sys


class CheckMode(Enum):
    """Check operation modes."""
    VALIDATE = 1    # Validate/report only
    TEST = 2        # Test if possible (e.g., send test email)
    CORRECT = 3     # Correct/create if possible


class CheckStatus(Enum):
    """Result status for checks."""
    PASS = "pass"           # Check passed
    FAIL = "fail"           # Check failed
    WARNING = "warning"     # Non-critical issue
    SKIPPED = "skipped"     # Check was skipped
    CORRECTED = "corrected" # Issue was auto-corrected


@dataclass
class CheckResult:
    """
    Result of a single check operation.

    Attributes:
        name: Short check name (e.g., "SECRET_KEY exists")
        status: Pass/fail/warning/skipped/corrected
        message: Human-readable message
        remediation: How to fix (if failed)
        details: Additional data for programmatic use
        sub_results: Nested results for grouped checks
    """
    name: str
    status: CheckStatus
    message: str
    remediation: Optional[str] = None
    details: Optional[dict] = None
    sub_results: List['CheckResult'] = field(default_factory=list)

    @property
    def symbol(self) -> str:
        """Unicode symbol for display (matching check_email.py pattern)."""
        symbols = {
            CheckStatus.PASS: "\u2713",      # ✓
            CheckStatus.FAIL: "\u2717",      # ✗
            CheckStatus.WARNING: "\u26a0",   # ⚠
            CheckStatus.SKIPPED: "\u25cb",   # ○
            CheckStatus.CORRECTED: "\u27f3", # ⟳
        }
        return symbols.get(self.status, "?")

    @property
    def is_success(self) -> bool:
        """True if this result represents a successful outcome."""
        return self.status in (CheckStatus.PASS, CheckStatus.CORRECTED, CheckStatus.SKIPPED)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'remediation': self.remediation,
            'details': self.details,
            'sub_results': [r.to_dict() for r in self.sub_results],
            'is_success': self.is_success,
        }


class CheckRunner:
    """
    Base class for all check modules.

    Each service package (qdflask, qdimages, qdcomments) implements
    a CheckRunner subclass with its specific checks.

    Subclasses must:
    1. Set class attributes: service_name, service_display_name, config_filename
    2. Override _run_checks() to implement specific checks
    3. Call self.add_result() for each check performed

    Example:
        class UserSystemChecker(CheckRunner):
            service_name = "qdflask"
            service_display_name = "Flask Authentication"
            config_filename = "qdflask.yaml"

            def _run_checks(self):
                self._check_secret_key()
                self._check_database()
    """

    # Subclasses must override these
    service_name: str = ""              # e.g., "qdflask"
    service_display_name: str = ""      # e.g., "Flask Authentication"
    config_filename: str = ""           # e.g., "qdflask.yaml"

    def __init__(self, conf_dir: str = None, mode: CheckMode = CheckMode.VALIDATE):
        """
        Initialize check runner.

        Args:
            conf_dir: Path to conf/ directory (auto-detected if None)
            mode: Operation mode (VALIDATE, TEST, or CORRECT)
        """
        self.mode = mode
        self.conf_dir = conf_dir
        self._conf = None  # Lazy-loaded QdConf instance
        self.results: List[CheckResult] = []

    @property
    def conf(self):
        """Lazy-load QdConf to avoid circular imports."""
        if self._conf is None:
            from qdbase.qdconf import QdConf
            self._conf = QdConf(conf_dir=self.conf_dir)
        return self._conf

    def is_service_enabled(self) -> bool:
        """
        Check if this service is enabled in conf/<service>.yaml.

        Returns True if:
        - service_enabled is True
        - service_enabled key doesn't exist (default enabled)
        - config file doesn't exist (default enabled)

        Returns False only if service_enabled is explicitly False.
        """
        try:
            enabled = self.conf.get(f'{self.service_name}.service_enabled', True)
            return enabled is not False
        except (KeyError, FileNotFoundError, ValueError):
            return True  # Default to enabled if no config

    def run_all(self) -> List[CheckResult]:
        """
        Run all checks for this service.

        Returns:
            List of CheckResult objects
        """
        self.results = []

        if not self.is_service_enabled():
            self.results.append(CheckResult(
                name=f"{self.service_display_name} Service",
                status=CheckStatus.SKIPPED,
                message=f"Service disabled in conf/{self.config_filename}"
            ))
            return self.results

        # Call subclass-specific checks
        self._run_checks()
        return self.results

    def _run_checks(self):
        """
        Subclasses override this to implement specific checks.

        Each check should call self.add_result() with a CheckResult.
        """
        raise NotImplementedError("Subclasses must implement _run_checks()")

    def add_result(self, result: CheckResult):
        """Add a check result to the results list."""
        self.results.append(result)

    def print_results(self, file=None):
        """
        Print results in check_email.py style.

        Args:
            file: Output file (defaults to sys.stdout)
        """
        if file is None:
            file = sys.stdout

        print("=" * 60, file=file)
        print(f"{self.service_display_name} Configuration Check", file=file)
        print("=" * 60, file=file)

        for result in self.results:
            self._print_result(result, indent=0, file=file)

        # Summary
        print(file=file)
        passed = sum(1 for r in self.results if r.is_success)
        total = len(self.results)
        print(f"Results: {passed}/{total} checks passed", file=file)

    def _print_result(self, result: CheckResult, indent: int, file):
        """Print a single result with indentation."""
        prefix = "  " * indent
        print(f"{prefix}{result.symbol} {result.name}: {result.message}", file=file)

        if result.remediation and result.status == CheckStatus.FAIL:
            print(f"{prefix}  \u2192 {result.remediation}", file=file)  # → arrow

        for sub in result.sub_results:
            self._print_result(sub, indent + 1, file=file)

    @property
    def success(self) -> bool:
        """True if all checks passed (no failures)."""
        return all(r.is_success for r in self.results)

    @property
    def error_count(self) -> int:
        """Count of failed checks."""
        return sum(1 for r in self.results if r.status == CheckStatus.FAIL)

    @property
    def warning_count(self) -> int:
        """Count of warning checks."""
        return sum(1 for r in self.results if r.status == CheckStatus.WARNING)

    def get_summary(self) -> dict:
        """
        Get summary of check results.

        Returns:
            Dictionary with counts and status
        """
        return {
            'service': self.service_name,
            'total': len(self.results),
            'passed': sum(1 for r in self.results if r.status == CheckStatus.PASS),
            'failed': self.error_count,
            'warnings': self.warning_count,
            'skipped': sum(1 for r in self.results if r.status == CheckStatus.SKIPPED),
            'corrected': sum(1 for r in self.results if r.status == CheckStatus.CORRECTED),
            'success': self.success,
        }


# Registry of check modules for discovery
# Format: {'service_name': 'module.path.CheckerClass'}
CHECK_REGISTRY: dict = {}


def register_checker(service_name: str, checker_path: str):
    """
    Register a check module for a service.

    Args:
        service_name: Service identifier (e.g., 'qdflask')
        checker_path: Import path to checker class (e.g., 'qdflask.check_users.UserSystemChecker')
    """
    CHECK_REGISTRY[service_name] = checker_path


def get_checker_class(service_name: str) -> Optional[type]:
    """
    Get the checker class for a service.

    Args:
        service_name: Service identifier

    Returns:
        CheckRunner subclass or None if not found
    """
    if service_name not in CHECK_REGISTRY:
        return None

    checker_path = CHECK_REGISTRY[service_name]
    try:
        module_name, class_name = checker_path.rsplit('.', 1)
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        print(f"Warning: Could not load checker for {service_name}: {e}")
        return None


def run_all_checks(conf_dir: str = None, mode: CheckMode = CheckMode.VALIDATE) -> dict:
    """
    Run checks for all registered services.

    Args:
        conf_dir: Path to conf/ directory
        mode: Check mode (VALIDATE, TEST, CORRECT)

    Returns:
        Dictionary with results from all services
    """
    results = {}

    for service_name in CHECK_REGISTRY:
        checker_class = get_checker_class(service_name)
        if checker_class:
            checker = checker_class(conf_dir=conf_dir, mode=mode)
            checker.run_all()
            results[service_name] = {
                'results': [r.to_dict() for r in checker.results],
                'summary': checker.get_summary(),
            }

    return results


# Register built-in checkers
# These will be imported when the respective packages are available
register_checker('qdflask', 'qdflask.check_users.UserSystemChecker')
register_checker('qdimages', 'qdimages.check_images.ImageSystemChecker')
register_checker('qdcomments', 'qdcomments.check_comments.CommentSystemChecker')
