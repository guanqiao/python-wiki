"""
配置面板
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QFileDialog,
)
from PyQt6.QtCore import Qt

from pywiki.config.models import LLMConfig, LLMProvider


class ConfigPanel(QWidget):
    """LLM 配置面板"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        llm_group = QGroupBox("LLM 配置")
        form_layout = QFormLayout(llm_group)

        self.provider_combo = QComboBox()
        for provider in LLMProvider:
            self.provider_combo.addItem(provider.value, provider)
        form_layout.addRow("Provider:", self.provider_combo)

        self.endpoint_edit = QLineEdit()
        self.endpoint_edit.setPlaceholderText("https://api.openai.com/v1")
        form_layout.addRow("Endpoint:", self.endpoint_edit)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("sk-...")
        form_layout.addRow("API Key:", self.api_key_edit)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("gpt-4")
        form_layout.addRow("Model:", self.model_edit)

        self.ca_cert_edit = QLineEdit()
        self.ca_cert_edit.setPlaceholderText("CA 证书路径 (可选)")
        ca_cert_button = QPushButton("浏览...")
        ca_cert_button.clicked.connect(self._browse_ca_cert)
        ca_cert_layout = QVBoxLayout()
        ca_cert_layout.addWidget(self.ca_cert_edit)
        ca_cert_layout.addWidget(ca_cert_button)
        form_layout.addRow("CA 证书:", ca_cert_layout)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 300)
        self.timeout_spin.setValue(60)
        self.timeout_spin.setSuffix(" 秒")
        form_layout.addRow("Timeout:", self.timeout_spin)

        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(0, 10)
        self.max_retries_spin.setValue(3)
        form_layout.addRow("最大重试:", self.max_retries_spin)

        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setValue(0.7)
        self.temperature_spin.setSingleStep(0.1)
        form_layout.addRow("Temperature:", self.temperature_spin)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 32000)
        self.max_tokens_spin.setValue(4096)
        form_layout.addRow("Max Tokens:", self.max_tokens_spin)

        layout.addWidget(llm_group)

        test_button = QPushButton("测试连接")
        test_button.clicked.connect(self._test_connection)
        layout.addWidget(test_button)

        layout.addStretch()

    def _browse_ca_cert(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 CA 证书",
            "",
            "证书文件 (*.pem *.crt *.cer);;所有文件 (*)"
        )
        if file_path:
            self.ca_cert_edit.setText(file_path)

    def _test_connection(self) -> None:
        pass

    def get_config(self) -> dict:
        return {
            "provider": self.provider_combo.currentData(),
            "endpoint": self.endpoint_edit.text(),
            "api_key": self.api_key_edit.text(),
            "model": self.model_edit.text(),
            "ca_cert": self.ca_cert_edit.text() or None,
            "timeout": self.timeout_spin.value(),
            "max_retries": self.max_retries_spin.value(),
            "temperature": self.temperature_spin.value(),
            "max_tokens": self.max_tokens_spin.value(),
        }

    def set_config(self, config: LLMConfig) -> None:
        index = self.provider_combo.findData(config.provider)
        if index >= 0:
            self.provider_combo.setCurrentIndex(index)

        self.endpoint_edit.setText(config.endpoint)
        self.api_key_edit.setText(config.api_key.get_secret_value())
        self.model_edit.setText(config.model)

        if config.ca_cert:
            self.ca_cert_edit.setText(str(config.ca_cert))

        self.timeout_spin.setValue(config.timeout)
        self.max_retries_spin.setValue(config.max_retries)
        self.temperature_spin.setValue(config.temperature)
        self.max_tokens_spin.setValue(config.max_tokens)
