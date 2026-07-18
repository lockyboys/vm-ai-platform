from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from src.common.navigation.navigation_model import NavigationModel


class BaseRenderer(ABC):
    """Navigation Renderer의 기본 클래스."""

    @abstractmethod
    def render(
        self,
        model: NavigationModel,
    ) -> str:
        """NavigationModel을 문자열로 변환한다."""
        raise NotImplementedError
