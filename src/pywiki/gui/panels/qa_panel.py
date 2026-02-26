
"""
问答面板
"""
from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QSplitter,
    QLabel,
    QScrollArea,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QTextCursor


class QAAgent(QThread):
    """问答处理线程"""
    
    answer_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(
        self,
        question: str,
        vector_store,
        llm_client,
        wiki_dir: Optional[Path] = None,
    ):
        super().__init__()
        self.question = question
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.wiki_dir = wiki_dir
    
    def run(self):
        try:
            context = ""
            
            if self.vector_store:
                search_results = self.vector_store.search(self.question, k=5)
                if search_results:
                    context = "\n\n".join([
                        f"相关文档 {i+1}:\n{result['content']}"
                        for i, result in enumerate(search_results)
                    ])
            
            system_prompt = """你是一个专业的代码文档助手。请基于提供的上下文回答用户的问题。
如果上下文中没有相关信息，请诚实地说明。回答要清晰、准确、专业。"""
            
            prompt = f"""用户问题: {self.question}

相关上下文:
{context if context else '暂无相关上下文'}

请回答用户的问题。"""
            
            answer = self.llm_client.generate(prompt, system_prompt=system_prompt)
            self.answer_ready.emit(answer)
        except Exception as e:
            self.error_occurred.emit(str(e))


class QAPanel(QWidget):
    """问答面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vector_store = None
        self.llm_client = None
        self.wiki_dir = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("💬 智能问答")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("对话记录将显示在这里...")
        chat_layout.addWidget(self.chat_display)
        
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("输入你的问题，按 Enter 发送...")
        self.question_input.returnPressed.connect(self._on_send_question)
        input_layout.addWidget(self.question_input)
        
        self.send_button = QPushButton("发送")
        self.send_button.clicked.connect(self._on_send_question)
        input_layout.addWidget(self.send_button)
        
        chat_layout.addWidget(input_widget)
        
        splitter.addWidget(chat_widget)
        
        self.sources_widget = QWidget()
        sources_layout = QVBoxLayout(self.sources_widget)
        sources_layout.setContentsMargins(0, 0, 0, 0)
        
        sources_title = QLabel("📚 参考来源")
        sources_title_font = QFont()
        sources_title_font.setBold(True)
        sources_title.setFont(sources_title_font)
        sources_layout.addWidget(sources_title)
        
        self.sources_display = QTextEdit()
        self.sources_display.setReadOnly(True)
        self.sources_display.setPlaceholderText("检索到的相关文档将显示在这里...")
        sources_layout.addWidget(self.sources_display)
        
        splitter.addWidget(self.sources_widget)
        
        splitter.setSizes([600, 200])
        layout.addWidget(splitter)
        
        self._append_system_message("你好！我是 Python Wiki 智能助手。有什么关于代码库的问题吗？")
    
    def set_vector_store(self, vector_store):
        """设置向量存储"""
        self.vector_store = vector_store
    
    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self.llm_client = llm_client
    
    def set_wiki_dir(self, wiki_dir: Path):
        """设置 Wiki 目录"""
        self.wiki_dir = wiki_dir
    
    def _append_system_message(self, message: str):
        """添加系统消息"""
        self._append_message("system", message)
    
    def _append_user_message(self, message: str):
        """添加用户消息"""
        self._append_message("user", message)
    
    def _append_assistant_message(self, message: str):
        """添加助手消息"""
        self._append_message("assistant", message)
    
    def _append_message(self, role: str, message: str):
        """添加消息到聊天显示"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if role == "system":
            color = "#666"
            prefix = "🤖"
        elif role == "user":
            color = "#3498db"
            prefix = "👤"
        else:
            color = "#27ae60"
            prefix = "🤖"
        
        html = f"""
        &lt;div style="margin: 10px 0; padding: 10px; border-radius: 5px; background-color: #f5f5f5;"&gt;
            &lt;span style="font-weight: bold; color: {color};"&gt;{prefix}&lt;/span&gt;
            &lt;div style="margin-top: 5px; white-space: pre-wrap;"&gt;{message}&lt;/div&gt;
        &lt;/div&gt;
        """
        
        cursor.insertHtml(html)
        self.chat_display.setTextCursor(cursor)
    
    def _on_send_question(self):
        """发送问题"""
        question = self.question_input.text().strip()
        if not question:
            return
        
        if not self.llm_client:
            self._append_system_message("请先配置 LLM 客户端")
            return
        
        self.question_input.clear()
        self.question_input.setEnabled(False)
        self.send_button.setEnabled(False)
        
        self._append_user_message(question)
        
        self._display_sources(question)
        
        self.agent = QAAgent(
            question=question,
            vector_store=self.vector_store,
            llm_client=self.llm_client,
            wiki_dir=self.wiki_dir,
        )
        self.agent.answer_ready.connect(self._on_answer_ready)
        self.agent.error_occurred.connect(self._on_error)
        self.agent.start()
    
    def _display_sources(self, question: str):
        """显示参考来源"""
        if not self.vector_store:
            return
        
        try:
            results = self.vector_store.search(question, k=5)
            if results:
                sources_text = ""
                for i, result in enumerate(results):
                    sources_text += f"--- 来源 {i+1} ---\n"
                    sources_text += f"{result['content'][:300]}...\n\n"
                
                self.sources_display.setText(sources_text)
        except Exception as e:
            self.sources_display.setText(f"获取来源失败: {str(e)}")
    
    @pyqtSlot(str)
    def _on_answer_ready(self, answer: str):
        """回答就绪"""
        self._append_assistant_message(answer)
        self._enable_input()
    
    @pyqtSlot(str)
    def _on_error(self, error: str):
        """发生错误"""
        self._append_system_message(f"抱歉，处理失败: {error}")
        self._enable_input()
    
    def _enable_input(self):
        """启用输入"""
        self.question_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.question_input.setFocus()
    
    def clear_chat(self):
        """清空聊天记录"""
        self.chat_display.clear()
        self.sources_display.clear()
        self._append_system_message("你好！我是 Python Wiki 智能助手。有什么关于代码库的问题吗？")
