"""SPDS main window rendered from authenticated UI Repository data."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from common.common_function import logger
from .ui_runtime import UIRuntimeRepository, UIRuntimeSnapshot


class MainWindow(QMainWindow):
    """Render only registered menus and actions granted to the verified member."""

    def __init__(self, member_id: str, runtime_repository: UIRuntimeRepository | None = None):
        super().__init__()
        self.setWindowTitle("Story Programming Document Studio (SPDS)")
        self.resize(1200, 800)
        self._member_id = member_id
        self._snapshot: UIRuntimeSnapshot | None = None
        self._repository = runtime_repository or UIRuntimeRepository()

        root = QWidget(self)
        layout = QHBoxLayout(root)
        self.menu_list = QListWidget(root)
        self.menu_list.setAccessibleName("허용된 UI 메뉴")
        layout.addWidget(self.menu_list, 1)

        self.detail = QWidget(root)
        self.detail_layout = QVBoxLayout(self.detail)
        self.title_label = QLabel("SPDS UI Runtime")
        self.screen_label = QLabel(
            "등록된 UI Screen, Menu, Action과 권한을 확인하는 중입니다."
        )
        self.action_layout = QVBoxLayout()
        self.detail_layout.addWidget(self.title_label)
        self.detail_layout.addWidget(self.screen_label)
        self.detail_layout.addLayout(self.action_layout)
        self.detail_layout.addStretch(1)
        layout.addWidget(self.detail, 3)
        self.setCentralWidget(root)

        status_bar = QStatusBar()
        status_bar.showMessage("UI Object·권한 Repository 확인 중")
        self.setStatusBar(status_bar)
        self.menu_list.currentItemChanged.connect(self._select_menu)

        try:
            self._snapshot = self._repository.load_for_member(member_id)
            self._render_snapshot(self._snapshot)
        except Exception as exc:
            # DB/schema/auth failures never fall back to an unrestricted placeholder UI.
            logger.error("SPDS UI Runtime load failed: %s", exc)
            self.screen_label.setText(
                "UI Runtime을 불러오지 못했습니다. 인증, UI Object, 스키마 또는 권한 설정을 확인하세요."
            )
            self.statusBar().showMessage("UI Runtime 접근 거부 또는 설정 오류")

    def _render_snapshot(self, snapshot: UIRuntimeSnapshot) -> None:
        self.menu_list.clear()
        for menu in snapshot.menus:
            item = QListWidgetItem(menu.menu_name)
            item.setData(Qt.ItemDataRole.UserRole, menu)
            self.menu_list.addItem(item)

        if not snapshot.menus:
            self.screen_label.setText("이 Member에게 허용된 활성 UI Menu가 없습니다.")
            if snapshot.unresolved_rule_permission_count:
                self.statusBar().showMessage(
                    "Member 권한 또는 활성 Role-Rule 연결 권한 없음"
                )
            else:
                self.statusBar().showMessage("허용된 UI Menu 없음")
            return

        self.statusBar().showMessage(
            f"Member {snapshot.member_id} | UI Object·Member/Rule 권한 검증 완료"
        )
        self.menu_list.setCurrentRow(0)

    def _select_menu(self, current: QListWidgetItem | None, _previous) -> None:
        if current is None:
            return
        menu = current.data(Qt.ItemDataRole.UserRole)
        self.title_label.setText(menu.menu_name)
        self.screen_label.setText(
            f"Screen ID: {menu.screen_id}\n"
            f"Menu Code: {menu.menu_code}\n"
            f"Screen Type: {menu.screen_type_code}\n"
            f"Menu Type: {menu.menu_type_code}\n"
            f"URL: {menu.menu_url or '(미설정)'}"
        )

        # The snapshot already limits buttons by permission; click-time execution rechecks grants.
        while self.action_layout.count():
            item = self.action_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for action in menu.actions:
            button = QPushButton(action.button_name)
            button.setToolTip(
                f"{action.permission_type_code} 권한 적용; 클릭 시 활성 Verified Query와 권한을 재확인합니다."
            )
            button.clicked.connect(
                lambda _checked=False, selected=action: self._execute_action(selected)
            )
            self.action_layout.addWidget(button)

    def _execute_action(self, action) -> None:
        """Run an authorized parameterless action and show a safe error to the user."""
        try:
            self._repository.execute_action_for_member(
                self._member_id,
                action.button_code,
            )
        except Exception as exc:
            # Keep SQL and database details in protected logs, not in a desktop dialog.
            logger.error(
                "SPDS UI Action failed: member_id=%s button_code=%s error_type=%s",
                self._member_id,
                action.button_code,
                type(exc).__name__,
            )
            self.statusBar().showMessage("UI Action 실패: 권한·Verified Query·입력 계약을 확인하세요.")
            QMessageBox.warning(
                self,
                "UI Action 실행 실패",
                "권한을 다시 확인했으며 작업이 실행되지 않았습니다. "
                "활성 Verified Query 또는 필수 입력값 설정을 확인하세요.",
            )
            return

        self.statusBar().showMessage(f"UI Action 완료: {action.button_name}")
        QMessageBox.information(self, "UI Action 완료", "검증된 작업을 실행했습니다.")