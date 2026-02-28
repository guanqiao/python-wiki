"""
LLM 配置对话框
"""

from pathlib import Path
from typing import Optional

from pydantic import SecretStr

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QHBoxLayout,
    QWidget,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from pywiki.config.models import LLMConfig, LLMProvider


class LLMTestThread(QThread):
    """LLM 连接测试线程"""
    
    test_completed = pyqtSignal(bool, str)
    
    def __init__(self, config: LLMConfig):
        super().__init__()
        self.config = config
    
    def run(self):
        try:
            from pywiki.llm.client import LLMClient
            import asyncio
            
            client = LLMClient.from_config(self.config)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(client.test_connection())
                if success:
                    self.test_completed.emit(True, "连接测试成功！")
                else:
                    self.test_completed.emit(False, "连接测试失败：服务器无响应")
            finally:
                loop.close()
                
        except Exception as e:
            self.test_completed.emit(False, f"连接测试失败：{str(e)}")


class LLMConfigDialog(QDialog):
    """LLM 配置对话框"""

    def __init__(self, current_config: LLMConfig, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_config = current_config
        self.setWindowTitle("LLM 配置")
        self.setMinimumWidth(500)
        self._init_ui()
        self._load_config()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.provider_combo = QComboBox()
        for provider in LLMProvider:
            self.provider_combo.addItem(provider.value, provider)
        form_layout.addRow("Provider:", self.provider_combo)

        self.endpoint_edit = QLineEdit()
        self.endpoint_edit.setPlaceholderText("https://api.openai.com/v1")
        form_layout.addRow("Endpoint URL:", self.endpoint_edit)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("API Key")
        form_layout.addRow("API Key:", self.api_key_edit)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("gpt-4")
        form_layout.addRow("Model:", self.model_edit)

        ca_layout = QHBoxLayout()
        self.ca_cert_edit = QLineEdit()
        self.ca_cert_edit.setPlaceholderText("CA 证书路径 (可选)")
        self.ca_browse_button = QPushButton("浏览...")
        self.ca_browse_button.clicked.connect(self._browse_ca_cert)
        ca_layout.addWidget(self.ca_cert_edit)
        ca_layout.addWidget(self.ca_browse_button)
        form_layout.addRow("CA 证书:", ca_layout)

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

        layout.addLayout(form_layout)

        self._test_button = QPushButton("测试连接")
        self._test_button.clicked.connect(self._test_connection)
        layout.addWidget(self._test_button)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.accept)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def _load_config(self) -> None:
        if not self._current_config:
            return

        index = self.provider_combo.findData(self._current_config.provider)
        if index >= 0:
            self.provider_combo.setCurrentIndex(index)

        self.endpoint_edit.setText(self._current_config.endpoint)
        self.api_key_edit.setText(self._current_config.api_key.get_secret_value())
        self.model_edit.setText(self._current_config.model)

        if self._current_config.ca_cert:
            self.ca_cert_edit.setText(str(self._current_config.ca_cert))

        self.timeout_spin.setValue(self._current_config.timeout)
        self.max_retries_spin.setValue(self._current_config.max_retries)
        self.temperature_spin.setValue(self._current_config.temperature)
        self.max_tokens_spin.setValue(self._current_config.max_tokens)

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
        config = self._get_temp_config()
        if not config:
            QMessageBox.warning(self, "警告", "请先填写 API Key")
            return
        
        self._test_button.setText("测试中...")
        self._test_button.setEnabled(False)
        
        self._test_thread = LLMTestThread(config)
        self._test_thread.test_completed.connect(self._on_test_completed)
        self._test_thread.start()
    
    def _get_temp_config(self) -> Optional[LLMConfig]:
        """获取临时配置用于测试"""
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            return None
        
        ca_cert = self.ca_cert_edit.text().strip()
        return LLMConfig(
            provider=self.provider_combo.currentData(),
            endpoint=self.endpoint_edit.text().strip(),
            api_key=SecretStr(api_key),
            model=self.model_edit.text().strip(),
            ca_cert=Path(ca_cert) if ca_cert else None,
            timeout=self.timeout_spin.value(),
        )
    
    def _on_test_completed(self, success: bool, message: str) -> None:
        self._test_button.setText("测试连接")
        self._test_button.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "测试连接", message)
        else:
            QMessageBox.warning(self, "测试连接", message)

    def get_llm_config(self) -> Optional[LLMConfig]:
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            return None

        ca_cert = self.ca_cert_edit.text().strip()
        return LLMConfig(
            provider=self.provider_combo.currentData(),
            endpoint=self.endpoint_edit.text().strip(),
            api_key=SecretStr(api_key),
            model=self.model_edit.text().strip(),
            ca_cert=Path(ca_cert) if ca_cert else None,
            timeout=self.timeout_spin.value(),
            max_retries=self.max_retries_spin.value(),
            temperature=self.temperature_spin.value(),
            max_tokens=self.max_tokens_spin.value(),
        )
