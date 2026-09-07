"""LR2 language identification, split by concern: labeling, lexical
profiles, neural training, ad-hoc identification, and test-collection runs.
All the actual method math lives in lang-id-service; these services load and
persist data and decide which profiles to compare against."""

from .identification import LangIdIdentificationService
from .labeling import LangIdLabelingService
from .profiles import LangIdProfileService
from .test_runs import LangIdTestRunService
from .training import LangIdTrainingService

__all__ = [
    "LangIdLabelingService",
    "LangIdProfileService",
    "LangIdTrainingService",
    "LangIdIdentificationService",
    "LangIdTestRunService",
]
